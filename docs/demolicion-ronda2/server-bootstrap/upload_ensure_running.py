#!/usr/bin/env python3
"""Sube ensure-running.sh y lo deja en el servidor."""
from __future__ import annotations
import io
from pathlib import Path
import paramiko, puttykeys

phrase = Path(r"F:\servidor\frase-clave.txt").read_text().strip().splitlines()[0]
ppk = Path(r"F:\servidor\cph_private_key.ppk").read_text(encoding="utf-8", errors="replace")
pkey = paramiko.Ed25519Key.from_private_key(io.StringIO(puttykeys.ppkraw_to_openssh(ppk, passphrase=phrase)))
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("190.169.110.9", username="cph", pkey=pkey, timeout=30)
data = (Path(__file__).resolve().parent.parent / "fase2-rojo" / "run" / "ensure-running.sh").read_bytes().replace(b"\r\n", b"\n")
sftp = c.open_sftp()
with sftp.open("/home/cph/apps/fase2-rojo/run/ensure-running.sh", "wb") as f:
    f.write(data)
sftp.close()
c.exec_command("chmod +x ~/apps/fase2-rojo/run/ensure-running.sh")
c.close()
print("OK ensure-running.sh en servidor")
