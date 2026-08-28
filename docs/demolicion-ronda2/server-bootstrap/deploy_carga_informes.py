#!/usr/bin/env python3
"""Sube PDFs de D:\\Edificios Demolicion y ejecuta carga inicial en servidor."""
from __future__ import annotations

import io
from pathlib import Path

import paramiko
import puttykeys

BASE = Path(__file__).resolve().parent.parent
FASE2 = BASE / "fase2-rojo"
PDF_DIR = Path(r"D:\Edificios Demolicion")
CSV_LOCAL = BASE / "cruce-informes-demolicion-habitable-2026-08-20.csv"
REMOTE = "/home/cph/apps/fase2-rojo"
REMOTE_PDF = "/home/cph/data/informes-demolicion"
PHRASE = Path(r"F:\servidor\frase-clave.txt").read_text().strip().splitlines()[0]
PPK = Path(r"F:\servidor\cph_private_key.ppk").read_text(encoding="utf-8", errors="replace")


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
    if not PDF_DIR.is_dir():
        raise SystemExit(f"No existe carpeta PDF: {PDF_DIR}")

    client = connect()
    sftp = client.open_sftp()

    print("Subiendo app inspecciones…")
    upload_tree(sftp, FASE2 / "inspecciones", f"{REMOTE}/inspecciones")
    for rel in (
        "config/urls.py",
        "templates/admin/inspecciones/casorojo/change_form.html",
    ):
        local = FASE2 / rel
        if local.is_file():
            upload_file(sftp, local, f"{REMOTE}/{rel.replace(chr(92), '/')}")

    try:
        sftp.mkdir(REMOTE_PDF)
    except OSError:
        pass

    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    print(f"Subiendo {len(pdfs)} PDFs…")
    for pdf in pdfs:
        upload_file(sftp, pdf, f"{REMOTE_PDF}/{pdf.name}")
        print("  pdf", pdf.name)

    if CSV_LOCAL.is_file():
        upload_file(sftp, CSV_LOCAL, f"{REMOTE_PDF}/cruce-informes-demolicion-habitable-2026-08-20.csv")

    sftp.close()

    cmd = f"""
set -e
cd {REMOTE}
source .venv/bin/activate
python manage.py migrate --noinput
echo '--- DRY RUN ---'
python manage.py cargar_informes_demolicion --carpeta {REMOTE_PDF} --csv {REMOTE_PDF}/cruce-informes-demolicion-habitable-2026-08-20.csv --dry-run
echo '--- CARGA REAL ---'
python manage.py cargar_informes_demolicion --carpeta {REMOTE_PDF} --csv {REMOTE_PDF}/cruce-informes-demolicion-habitable-2026-08-20.csv --reemplazar-pdf --sobrescribir-campos
mkdir -p media/informes
~/apps/fase2-rojo/run/ensure-running.sh || true
python -c "import os,django; os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings'); django.setup(); from inspecciones.models import InformePdfAdjunto, CasoRojo; print('PDFs adjuntos:', InformePdfAdjunto.objects.count()); print('Casos con PDF:', CasoRojo.objects.filter(informes_pdf__isnull=False).distinct().count())"
"""
    _, stdout, stderr = client.exec_command(cmd, timeout=900)
    print(stdout.read().decode("utf-8", errors="replace"))
    err = stderr.read().decode("utf-8", errors="replace")
    if err.strip():
        print("STDERR:", err[-4000:])
    client.close()
    print("Ensayo carga informes PDF completado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
