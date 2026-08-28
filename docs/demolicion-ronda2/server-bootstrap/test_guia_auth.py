#!/usr/bin/env python3
import io
from pathlib import Path
import paramiko, puttykeys

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
python << 'PY'
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.test import Client
from django.contrib.auth.models import User
u = User.objects.filter(is_superuser=True).first()
client = Client(HTTP_HOST='190.169.110.9')
client.force_login(u)
for path in ['/admin/', '/guia/usuario.pdf']:
    r = client.get(path)
    print(path, r.status_code, r.get('Content-Type', '')[:40], len(r.content))
    if r.status_code >= 400:
        print(r.content[:500])
PY
"""
_, o, e = c.exec_command(cmd, timeout=120)
print(o.read().decode())
c.close()
