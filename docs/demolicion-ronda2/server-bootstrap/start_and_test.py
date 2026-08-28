#!/usr/bin/env python3
import io
from pathlib import Path
import paramiko, puttykeys

phrase = Path(r"F:\servidor\frase-clave.txt").read_text().strip().splitlines()[0]
ppk = Path(r"F:\servidor\cph_private_key.ppk").read_text(encoding="utf-8", errors="replace")
pkey = paramiko.Ed25519Key.from_private_key(io.StringIO(puttykeys.ppkraw_to_openssh(ppk, passphrase=phrase)))
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("190.169.110.9", username="cph", pkey=pkey, timeout=30)

cmd = """
cd ~/apps/fase2-rojo
source .venv/bin/activate
pkill -f 'gunicorn config.wsgi' 2>/dev/null || true
sleep 1
mkdir -p logs
nohup ./run/start-gunicorn.sh >> logs/nohup.out 2>&1 &
sleep 4
echo '=== PROCESOS ==='
pgrep -af gunicorn || echo 'NO GUNICORN'
ss -tlnp 2>/dev/null | grep 8000 || netstat -tlnp 2>/dev/null | grep 8000
echo '=== HEALTH ==='
python3 -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health/').read().decode())"
echo '=== LOGIN TEST ==='
python3 /tmp/test_admin_login.py
"""
_, o, e = c.exec_command(cmd, timeout=90)
print(o.read().decode("utf-8", errors="replace"))
err = e.read().decode("utf-8", errors="replace")
if err.strip():
    print("ERR:", err)
c.close()
