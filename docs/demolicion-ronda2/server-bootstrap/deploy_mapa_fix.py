#!/usr/bin/env python3
"""Despliega corrección mapa GPS (parse gps_hab/gps_v2 sin depender de lat/lng en ORM)."""
from __future__ import annotations

import io
from pathlib import Path

import paramiko
import puttykeys

BASE = Path(__file__).resolve().parent.parent
FASE2 = BASE / "fase2-rojo"
REMOTE = "/home/cph/apps/fase2-rojo"
PHRASE = Path(r"F:\servidor\frase-clave.txt").read_text().strip().splitlines()[0]
PPK = Path(r"F:\servidor\cph_private_key.ppk").read_text(encoding="utf-8", errors="replace")

FILES = [
    FASE2 / "inspecciones" / "gps_utils.py",
    FASE2 / "inspecciones" / "views.py",
    FASE2 / "inspecciones" / "admin.py",
    FASE2 / "run" / "restart-gunicorn.sh",
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
    data = local.read_bytes().replace(b"\r\n", b"\n")
    with sftp.open(remote, "wb") as f:
        f.write(data)
    print("OK", remote)


def main() -> int:
    client = connect()
    sftp = client.open_sftp()
    for local in FILES:
        remote = f"{REMOTE}/{local.relative_to(FASE2).as_posix()}"
        upload_file(sftp, local, remote)
    sftp.close()

    cmd = f"""
set -e
cd {REMOTE}
source .venv/bin/activate
python manage.py migrate --noinput
chmod +x run/restart-gunicorn.sh
bash run/restart-gunicorn.sh
python -c "
import os,django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
django.setup()
from inspecciones.models import CasoRojo
from inspecciones.gps_utils import filtrar_casos_con_gps
total = CasoRojo.objects.count()
con_gps = len(filtrar_casos_con_gps(CasoRojo.objects.all().iterator()))
print('Casos:', total, 'Con GPS parseado:', con_gps)
"
python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health/').read().decode())"
"""
    _, stdout, stderr = client.exec_command(cmd, timeout=120)
    print(stdout.read().decode("utf-8", errors="replace"))
    err = stderr.read().decode("utf-8", errors="replace")
    if err.strip():
        print("STDERR:", err[-2000:])
    client.close()
    print("\nMapa fix desplegado — http://190.169.110.9/mapa/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
