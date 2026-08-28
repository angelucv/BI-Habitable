#!/usr/bin/env python3
import io
from pathlib import Path
import paramiko
import puttykeys

phrase = Path(r"F:\servidor\frase-clave.txt").read_text().strip().splitlines()[0]
ppk = Path(r"F:\servidor\cph_private_key.ppk").read_text(encoding="utf-8", errors="replace")
pkey = paramiko.Ed25519Key.from_private_key(
    io.StringIO(puttykeys.ppkraw_to_openssh(ppk, passphrase=phrase))
)
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("190.169.110.9", username="cph", pkey=pkey, timeout=30)
script = """
cd /home/cph/apps/fase2-rojo
bash run/restart-gunicorn.sh
sleep 3
python3 <<'PY'
import urllib.request
for url in [
    'http://127.0.0.1:8000/admin/',
    'http://127.0.0.1:8000/asignacion/',
    'http://127.0.0.1/api/health/',
    'http://127.0.0.1/admin/',
]:
    try:
        r = urllib.request.urlopen(url, timeout=8)
        print(url, r.status)
    except Exception as e:
        print(url, 'ERR', type(e).__name__, e)
PY
"""
_, o, e = c.exec_command(script, timeout=90)
print(o.read().decode("utf-8", errors="replace"))
err = e.read().decode("utf-8", errors="replace")
if err.strip():
    print("ERR:", err[-1500:])
c.close()
