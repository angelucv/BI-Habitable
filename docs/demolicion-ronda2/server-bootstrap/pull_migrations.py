#!/usr/bin/env python3
"""Descarga migraciones generadas en servidor al repo local."""
from __future__ import annotations
import io
from pathlib import Path
import paramiko, puttykeys

LOCAL = Path(__file__).resolve().parent.parent / "fase2-rojo" / "inspecciones" / "migrations"
LOCAL.mkdir(parents=True, exist_ok=True)
phrase = Path(r"F:\servidor\frase-clave.txt").read_text().strip().splitlines()[0]
ppk = Path(r"F:\servidor\cph_private_key.ppk").read_text(encoding="utf-8", errors="replace")
pkey = paramiko.Ed25519Key.from_private_key(io.StringIO(puttykeys.ppkraw_to_openssh(ppk, passphrase=phrase)))
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("190.169.110.9", username="cph", pkey=pkey, timeout=30)
sftp = c.open_sftp()
for name in ("__init__.py", "0001_initial.py"):
    remote = f"/home/cph/apps/fase2-rojo/inspecciones/migrations/{name}"
    try:
        with sftp.open(remote, "rb") as f:
            (LOCAL / name).write_bytes(f.read().replace(b"\r\n", b"\n"))
        print("OK", LOCAL / name)
    except FileNotFoundError:
        if name == "__init__.py":
            (LOCAL / name).write_text("", encoding="utf-8")
sftp.close()
c.close()
