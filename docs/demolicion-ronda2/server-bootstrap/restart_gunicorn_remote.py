#!/usr/bin/env python3
"""Actualiza gunicorn bind y reinicia en servidor."""
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

script = """
cd /home/cph/apps/fase2-rojo
sed -i 's/127.0.0.1:8000/0.0.0.0:8000/' gunicorn.conf.py
pkill -f '/home/cph/apps/fase2-rojo/.venv/bin/gunicorn config.wsgi' || true
sleep 1
nohup ./run/start-gunicorn.sh > logs/nohup.out 2>&1 &
sleep 3
ss -tlnp | grep 8000
python3 -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health/').read().decode())"
"""
_, o, e = c.exec_command(script, timeout=60)
print(o.read().decode("utf-8", errors="replace"))
if e.read().decode().strip():
    print("ERR", e.read())
c.close()
