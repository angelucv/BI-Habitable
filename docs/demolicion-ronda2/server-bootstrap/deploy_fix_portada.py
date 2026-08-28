#!/usr/bin/env python3
"""Corrige layout portada admin + estilos guía PDF."""
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
    "templates/admin/login.html",
    "templates/registration/logged_out.html",
    "templates/includes/cpeh_nombre_institucional.html",
    "config/jazzmin_settings.py",
    "inspecciones/static/css/cpeh_admin.css",
]


def connect() -> paramiko.SSHClient:
    pkey = paramiko.Ed25519Key.from_private_key(
        io.StringIO(puttykeys.ppkraw_to_openssh(PPK, passphrase=PHRASE))
    )
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("190.169.110.9", username="cph", pkey=pkey, timeout=60)
    return client


def main() -> int:
    client = connect()
    sftp = client.open_sftp()
    for rel in FILES:
        local = FASE2 / rel.replace("/", "\\") if "\\" in rel else FASE2 / rel
        remote = f"{REMOTE}/{rel}"
        data = local.read_bytes().replace(b"\r\n", b"\n")
        with sftp.open(remote, "wb") as f:
            f.write(data)
        print("OK", remote)
    sftp.close()
    _, o, _ = client.exec_command(
        f"cd {REMOTE} && bash run/ensure-running.sh && "
        "source .venv/bin/activate && python manage.py collectstatic --noinput 2>/dev/null | tail -1",
        timeout=90,
    )
    print(o.read().decode())
    client.close()
    print("Portada corregida — http://190.169.110.9/admin/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
