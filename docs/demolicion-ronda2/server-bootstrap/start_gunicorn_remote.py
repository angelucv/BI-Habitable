#!/usr/bin/env python3
from __future__ import annotations
import io
from pathlib import Path
import paramiko, puttykeys

phrase = Path(r"F:\servidor\frase-clave.txt").read_text().strip().splitlines()[0]
ppk = Path(r"F:\servidor\cph_private_key.ppk").read_text(encoding='utf-8', errors='replace')
pkey = paramiko.Ed25519Key.from_private_key(io.StringIO(puttykeys.ppkraw_to_openssh(ppk, passphrase=phrase)))
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('190.169.110.9', username='cph', pkey=pkey, timeout=30)

script = """
cd /home/cph/apps/fase2-rojo
source .venv/bin/activate
which gunicorn
gunicorn --version
./run/start-gunicorn.sh &
sleep 4
pgrep -af gunicorn
ss -tlnp | grep 8000
python3 -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health/').read())"
cat logs/gunicorn-error.log 2>/dev/null | tail -20
"""
_, o, e = c.exec_command(script, timeout=90)
print(o.read().decode('utf-8', errors='replace'))
err = e.read().decode('utf-8', errors='replace')
if err: print('ERR', err)
c.close()
