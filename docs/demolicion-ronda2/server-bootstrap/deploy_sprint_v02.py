#!/usr/bin/env python3
"""Despliegue Sprint v0.2: roles, import masivo, catálogo, mapa, infra."""
from __future__ import annotations

import io
from pathlib import Path

import paramiko
import puttykeys

BASE = Path(__file__).resolve().parent.parent
FASE2 = BASE / "fase2-rojo"
REMOTE = "/home/cph/apps/fase2-rojo"
REMOTE_DATA = "/home/cph/data"
EXCEL_LOCAL = BASE / "cruce-informes-demolicion-habitable-2026-08-20-v2.xlsx"
PHRASE = Path(r"F:\servidor\frase-clave.txt").read_text().strip().splitlines()[0]
PPK = Path(r"F:\servidor\cph_private_key.ppk").read_text(encoding="utf-8", errors="replace")

UPLOAD_PATHS = [
    FASE2 / "inspecciones",
    FASE2 / "config" / "urls.py",
    FASE2 / "config" / "jazzmin_settings.py",
    FASE2 / "gunicorn.conf.py",
    FASE2 / "run" / "ensure-running.sh",
    FASE2 / "run" / "fase2-rojo.service",
    FASE2 / "templates" / "inspecciones" / "mapa_casos.html",
    FASE2 / "templates" / "includes" / "cpeh_guia_fase.html",
    FASE2 / "templates" / "includes" / "cpeh_guia_desarrolladores.html",
]


def connect() -> paramiko.SSHClient:
    pkey = paramiko.Ed25519Key.from_private_key(
        io.StringIO(puttykeys.ppkraw_to_openssh(PPK, passphrase=PHRASE))
    )
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("190.169.110.9", username="cph", pkey=pkey, timeout=60)
    return client


def upload_file(sftp: paramiko.SFTPClient, local: Path, remote: str) -> None:
    if local.suffix.lower() in {".xlsx", ".xls", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf"}:
        data = local.read_bytes()
    else:
        data = local.read_bytes().replace(b"\r\n", b"\n")
    parts = remote.split("/")
    for i in range(2, len(parts)):
        d = "/".join(parts[:i])
        try:
            sftp.mkdir(d)
        except OSError:
            pass
    with sftp.open(remote, "wb") as f:
        f.write(data)
    print("OK", remote)


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


def main() -> int:
    client = connect()
    sftp = client.open_sftp()

    for item in UPLOAD_PATHS:
        if item.is_dir():
            upload_tree(sftp, item, f"{REMOTE}/{item.relative_to(FASE2).as_posix()}")
        elif item.is_file():
            upload_file(sftp, item, f"{REMOTE}/{item.relative_to(FASE2).as_posix()}")

    if EXCEL_LOCAL.is_file():
        try:
            sftp.mkdir(REMOTE_DATA)
        except OSError:
            pass
        upload_file(sftp, EXCEL_LOCAL, f"{REMOTE_DATA}/cruce-informes-demolicion-habitable-2026-08-20-v2.xlsx")

    sftp.close()

    cmd = f"""
set -e
cd {REMOTE}
source .venv/bin/activate
pip install -q openpyxl Pillow
python manage.py migrate --noinput
python manage.py cargar_catalogo_procedimientos
python manage.py crear_roles_ejemplo
python manage.py cargar_franco_mar
python manage.py importar_ranking --excel {REMOTE_DATA}/cruce-informes-demolicion-habitable-2026-08-20-v2.xlsx --hoja Ranking_ROJO_LaGuaira --solo-gps
python manage.py collectstatic --noinput
mkdir -p media/evidencias logs
chmod +x run/ensure-running.sh
~/apps/fase2-rojo/run/ensure-running.sh || true
python -c "
import os,django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
django.setup()
from inspecciones.models import CasoRojo, Procedimiento
from django.contrib.auth.models import User
print('Casos:', CasoRojo.objects.count())
print('Con GPS:', CasoRojo.objects.exclude(lat__isnull=True).count())
print('Procedimientos:', Procedimiento.objects.count())
print('Usuarios demo:', list(User.objects.filter(username__endswith='.demo').values_list('username', flat=True)))
"
curl -sf http://127.0.0.1:8000/api/health/
"""
    _, stdout, stderr = client.exec_command(cmd, timeout=600)
    print(stdout.read().decode("utf-8", errors="replace"))
    err = stderr.read().decode("utf-8", errors="replace")
    if err.strip():
        print("STDERR:", err[-4000:])
    client.close()
    print("\nSprint v0.2 desplegado — /admin/ · /mapa/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
