#!/usr/bin/env python3
"""Diagnóstico remoto fase2-rojo."""
from __future__ import annotations

import io
from pathlib import Path

import paramiko
import puttykeys

PPK = Path(r"F:\servidor\cph_private_key.ppk")
PHRASE_FILE = Path(r"F:\servidor\frase-clave.txt")

phrase = PHRASE_FILE.read_text(encoding="utf-8").strip()
ppk = PPK.read_text(encoding="utf-8", errors="replace")
openssh = puttykeys.ppkraw_to_openssh(ppk, passphrase=phrase)
pkey = paramiko.Ed25519Key.from_private_key(io.StringIO(openssh))
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("190.169.110.9", username="cph", pkey=pkey, timeout=30)

cmds = [
    "cat ~/apps/fase2-rojo/logs/nohup.out 2>/dev/null | tail -30",
    "cat ~/apps/fase2-rojo/logs/gunicorn-error.log 2>/dev/null | tail -30",
    "cd ~/apps/fase2-rojo && source .venv/bin/activate && gunicorn config.wsgi:application -c gunicorn.conf.py --check-config 2>&1",
    "cd ~/apps/fase2-rojo && source .venv/bin/activate && timeout 5 gunicorn config.wsgi:application -c gunicorn.conf.py 2>&1 || true",
]
for c in cmds:
    stdin, stdout, stderr = client.exec_command(f"bash -lc {c!r}", timeout=60)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    print("===", c[:50], "===")
    print(out or err)
client.close()
