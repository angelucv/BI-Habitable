#!/usr/bin/env python3
"""Sprint operativo: código + ranking nacional + import PDF enriquecido + systemd."""
from __future__ import annotations

import io
from pathlib import Path

import paramiko
import puttykeys

BASE = Path(__file__).resolve().parent.parent
FASE2 = BASE / "fase2-rojo"
PDF_DIR = Path(r"D:\Edificios Demolicion")
CSV_LOCAL = BASE / "cruce-informes-demolicion-habitable-2026-08-20.csv"
EXCEL_LOCAL = BASE / "cruce-informes-demolicion-habitable-2026-08-20-v2.xlsx"
REMOTE = "/home/cph/apps/fase2-rojo"
REMOTE_DATA = "/home/cph/data"
REMOTE_PDF = f"{REMOTE_DATA}/informes-demolicion"
PHRASE = Path(r"F:\servidor\frase-clave.txt").read_text().strip().splitlines()[0]
PPK = Path(r"F:\servidor\cph_private_key.ppk").read_text(encoding="utf-8", errors="replace")

SKIP_DIRS = {"__pycache__", ".git", "staticfiles", "media"}


def connect() -> paramiko.SSHClient:
    pkey = paramiko.Ed25519Key.from_private_key(
        io.StringIO(puttykeys.ppkraw_to_openssh(PPK, passphrase=PHRASE))
    )
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("190.169.110.9", username="cph", pkey=pkey, timeout=120)
    return client


def upload_file(sftp: paramiko.SFTPClient, local: Path, remote: str) -> None:
    data = local.read_bytes()
    if local.suffix.lower() not in {".pdf", ".xlsx", ".xls"}:
        data = data.replace(b"\r\n", b"\n")
    parts = remote.split("/")
    for i in range(2, len(parts)):
        d = "/".join(parts[:i])
        try:
            sftp.mkdir(d)
        except OSError:
            pass
    with sftp.open(remote, "wb") as f:
        f.write(data)


def upload_tree(sftp: paramiko.SFTPClient, local: Path, remote: str) -> None:
    for path in local.rglob("*"):
        if any(p in SKIP_DIRS for p in path.parts):
            continue
        if path.name == "__pycache__" or path.suffix == ".pyc":
            continue
        rel = path.relative_to(local).as_posix()
        remote_path = f"{remote}/{rel}"
        if path.is_dir():
            try:
                sftp.mkdir(remote_path)
            except OSError:
                pass
        else:
            upload_file(sftp, path, remote_path)
            print("  ", remote_path)


def main() -> int:
    client = connect()
    sftp = client.open_sftp()

    print(">> Subiendo aplicación fase2-rojo…")
    for sub in ("config", "inspecciones", "templates", "run", "static"):
        local = FASE2 / sub
        if local.is_dir():
            upload_tree(sftp, local, f"{REMOTE}/{sub}")
    for extra in ("gunicorn.conf.py", "requirements.txt", "manage.py"):
        p = FASE2 / extra
        if p.is_file():
            upload_file(sftp, p, f"{REMOTE}/{extra}")

    for d in (REMOTE_DATA, REMOTE_PDF):
        try:
            sftp.mkdir(d)
        except OSError:
            pass

    if EXCEL_LOCAL.is_file():
        upload_file(sftp, EXCEL_LOCAL, f"{REMOTE_DATA}/cruce-informes-demolicion-habitable-2026-08-20-v2.xlsx")
        print("  Excel ranking v2")

    if CSV_LOCAL.is_file():
        upload_file(sftp, CSV_LOCAL, f"{REMOTE_PDF}/cruce-informes-demolicion-habitable-2026-08-20.csv")
        print("  CSV cruce PDF")

    if PDF_DIR.is_dir():
        pdfs = sorted(PDF_DIR.glob("*.pdf"))
        print(f">> Subiendo {len(pdfs)} PDFs…")
        for pdf in pdfs:
            upload_file(sftp, pdf, f"{REMOTE_PDF}/{pdf.name}")
    else:
        print(f"AVISO: sin carpeta local PDF ({PDF_DIR}); se usan PDFs ya en servidor")

    sftp.close()

    cmd = f"""
set -e
cd {REMOTE}
source .venv/bin/activate
chmod +x run/*.sh
python manage.py migrate --noinput

echo '=== Ranking nacional + La Guaira + Top200 ==='
python manage.py importar_ranking \\
  --excel {REMOTE_DATA}/cruce-informes-demolicion-habitable-2026-08-20-v2.xlsx \\
  --todas-hojas --solo-gps

echo '=== Import PDF enriquecido (36 cruce) ==='
python manage.py cargar_informes_demolicion \\
  --carpeta {REMOTE_PDF} \\
  --csv {REMOTE_PDF}/cruce-informes-demolicion-habitable-2026-08-20.csv \\
  --reemplazar-pdf --sobrescribir-campos

echo '=== systemd permanente ==='
if sudo -n true 2>/dev/null; then
  sudo cp run/fase2-rojo.service /etc/systemd/system/fase2-rojo.service
  sudo systemctl daemon-reload
  sudo systemctl enable fase2-rojo.service
  pkill -f '/home/cph/apps/fase2-rojo/.venv/bin/gunicorn' 2>/dev/null || true
  sleep 1
  sudo systemctl restart fase2-rojo.service
  sleep 2
  systemctl is-active fase2-rojo && echo 'systemd: activo' || bash run/restart-gunicorn.sh
else
  echo 'sudo sin password — fallback ensure-running'
  bash run/ensure-running.sh
fi

python manage.py collectstatic --noinput 2>/dev/null || true
python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health/').read().decode())"
python -c "
import os,django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
django.setup()
from inspecciones.models import CasoRojo, InformePdfAdjunto
from django.db.models import Count
n_pdf = InformePdfAdjunto.objects.count()
n_enr = CasoRojo.objects.exclude(nombre_conf='').count()
n_dec = CasoRojo.objects.exclude(decision_D='Pendiente').exclude(decision_D='').count()
n_nat = CasoRojo.objects.filter(puestos__icontains='nacional').count()
print('PDFs adjuntos:', n_pdf)
print('Casos con nombre visita2:', n_enr)
print('Casos con decision D:', n_dec)
print('Casos ranking nacional:', n_nat)
"
"""
    _, stdout, stderr = client.exec_command(cmd, timeout=1200)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    print(out)
    if err.strip():
        print("STDERR:", err[-5000:])
    client.close()
    print("\nSprint operativo completado — http://190.169.110.9/admin/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
