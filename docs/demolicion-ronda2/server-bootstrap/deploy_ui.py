#!/usr/bin/env python3
"""Despliega mejoras UI: Jazzmin + WhiteNoise + collectstatic."""
from __future__ import annotations

import io
from pathlib import Path

import paramiko
import puttykeys

ROOT = Path(__file__).resolve().parent.parent / "fase2-rojo"
REMOTE = "/home/cph/apps/fase2-rojo"
PHRASE = Path(r"F:\servidor\frase-clave.txt").read_text().strip().splitlines()[0]
PPK = Path(r"F:\servidor\cph_private_key.ppk").read_text(encoding="utf-8", errors="replace")

UPLOADS = [
    (ROOT / "config" / "settings.py", f"{REMOTE}/config/settings.py"),
    (ROOT / "config" / "jazzmin_settings.py", f"{REMOTE}/config/jazzmin_settings.py"),
    (ROOT / "config" / "urls.py", f"{REMOTE}/config/urls.py"),
    (ROOT / "requirements.txt", f"{REMOTE}/requirements.txt"),
    (ROOT / "inspecciones" / "admin.py", f"{REMOTE}/inspecciones/admin.py"),
    (
        ROOT / "inspecciones" / "static" / "css" / "cpeh_admin.css",
        f"{REMOTE}/inspecciones/static/css/cpeh_admin.css",
    ),
]


def connect() -> paramiko.SSHClient:
    pkey = paramiko.Ed25519Key.from_private_key(
        io.StringIO(puttykeys.ppkraw_to_openssh(PPK, passphrase=PHRASE))
    )
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("190.169.110.9", username="cph", pkey=pkey, timeout=30)
    return client


def upload(sftp: paramiko.SFTPClient, local: Path, remote: str) -> None:
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


def main() -> int:
    client = connect()
    sftp = client.open_sftp()
    for local, remote in UPLOADS:
        upload(sftp, local, remote)
    sftp.close()

    cmd = f"""
cd {REMOTE} && source .venv/bin/activate
pip install -q whitenoise django-jazzmin
pip install -q -r requirements.txt
python manage.py check
python manage.py collectstatic --noinput
pkill -f 'gunicorn config.wsgi' 2>/dev/null || true
sleep 2
nohup ./run/start-gunicorn.sh >> logs/nohup.out 2>&1 &
sleep 4
python3 -c "import urllib.request; h=urllib.request.urlopen('http://127.0.0.1/admin/login/'); b=h.read().decode(); print('static' in b.lower() or 'jazzmin' in b.lower() or 'admin/css' in b.lower()); print('login len', len(b))"
"""
    _, stdout, stderr = client.exec_command(cmd, timeout=300)
    print(stdout.read().decode("utf-8", errors="replace"))
    err = stderr.read().decode("utf-8", errors="replace")
    if err.strip():
        print("STDERR:", err[-4000:])
    client.close()
    print("\nListo — recarga http://190.169.110.9/admin/ (Ctrl+F5)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
