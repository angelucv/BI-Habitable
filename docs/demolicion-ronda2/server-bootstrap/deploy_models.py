#!/usr/bin/env python3
"""Sube app inspecciones al servidor y aplica migraciones."""
from __future__ import annotations

import io
from pathlib import Path

import paramiko
import puttykeys

ROOT = Path(__file__).resolve().parent.parent / "fase2-rojo" / "inspecciones"
REMOTE_APP = "/home/cph/apps/fase2-rojo/inspecciones"
PHRASE = Path(r"F:\servidor\frase-clave.txt").read_text().strip().splitlines()[0]
PPK = Path(r"F:\servidor\cph_private_key.ppk").read_text(encoding="utf-8", errors="replace")


def connect() -> paramiko.SSHClient:
    pkey = paramiko.Ed25519Key.from_private_key(
        io.StringIO(puttykeys.ppkraw_to_openssh(PPK, passphrase=PHRASE))
    )
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("190.169.110.9", username="cph", pkey=pkey, timeout=30)
    return client


def upload_tree(sftp: paramiko.SFTPClient, local: Path, remote: str) -> None:
    for path in local.rglob("*"):
        rel = path.relative_to(local).as_posix()
        remote_path = f"{remote}/{rel}" if rel != "." else remote
        if path.is_dir():
            try:
                sftp.mkdir(remote_path)
            except OSError:
                pass
        else:
            data = path.read_bytes()
            if path.suffix == ".py" or path.name.endswith(".sh"):
                data = data.replace(b"\r\n", b"\n")
            remote_dir = remote_path.rsplit("/", 1)[0]
            parts = remote_dir.split("/")
            acc = ""
            for part in parts:
                if not part:
                    acc = "/"
                    continue
                acc = f"{acc}{part}/" if acc.endswith("/") else f"{acc}/{part}"
                try:
                    sftp.mkdir(acc.rstrip("/"))
                except OSError:
                    pass
            with sftp.open(remote_path, "wb") as f:
                f.write(data)
            print("  ", remote_path)


def main() -> int:
    print("Subiendo inspecciones desde", ROOT)
    client = connect()
    sftp = client.open_sftp()
    upload_tree(sftp, ROOT, REMOTE_APP)
    sftp.close()

    cmd = """
cd ~/apps/fase2-rojo && source .venv/bin/activate
python manage.py makemigrations inspecciones --noinput
python manage.py migrate --noinput
python manage.py cargar_franco_mar
python manage.py check
pkill -f 'gunicorn config.wsgi' 2>/dev/null || true
sleep 2
nohup ./run/start-gunicorn.sh >> logs/nohup.out 2>&1 &
sleep 3
python3 -c "from django.contrib.auth import get_user_model; import os,django; os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings'); django.setup(); from inspecciones.models import CasoRojo; print('Casos:', CasoRojo.objects.count())"
"""
    _, stdout, stderr = client.exec_command(cmd, timeout=180)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    print(out)
    if err.strip():
        print("STDERR:", err[-3000:])
    client.close()
    print("Deploy OK — Admin: Casos ROJO Fase II")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
