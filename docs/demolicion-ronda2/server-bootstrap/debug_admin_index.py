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
c.connect("190.169.110.9", username="cph", pkey=pkey, timeout=60)
cmd = """
cd /home/cph/apps/fase2-rojo && source .venv/bin/activate
python -c "
import os, django, traceback
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.test import Client
from django.contrib.auth.models import User
client = Client(HTTP_HOST='190.169.110.9')
u = User.objects.filter(is_superuser=True).first()
client.force_login(u)
try:
    r = client.get('/admin/')
    print('status', r.status_code)
    if r.status_code >= 400:
        print(r.content[:3000].decode('utf-8', errors='replace'))
except Exception:
    traceback.print_exc()
"
tail -30 logs/nohup.out 2>/dev/null || true
"""
_, o, e = c.exec_command(cmd, timeout=90)
print(o.read().decode("utf-8", errors="replace"))
err = e.read().decode("utf-8", errors="replace")
if err.strip():
    print("ERR:", err)
c.close()
