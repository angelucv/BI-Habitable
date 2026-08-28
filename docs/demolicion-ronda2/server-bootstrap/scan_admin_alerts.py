#!/usr/bin/env python3
import io, re
from pathlib import Path
import paramiko, puttykeys

phrase = Path(r"F:\servidor\frase-clave.txt").read_text().strip().splitlines()[0]
ppk = Path(r"F:\servidor\cph_private_key.ppk").read_text(encoding="utf-8", errors="replace")
pkey = paramiko.Ed25519Key.from_private_key(io.StringIO(puttykeys.ppkraw_to_openssh(ppk, passphrase=phrase)))
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("190.169.110.9", username="cph", pkey=pkey, timeout=60)
cmd = """
cd /home/cph/apps/fase2-rojo && source .venv/bin/activate
python << 'PY'
import os, django, re
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.test import Client
from django.contrib.auth.models import User
u = User.objects.filter(is_superuser=True).first()
client = Client(HTTP_HOST='190.169.110.9')
client.force_login(u)
html = client.get('/admin/').content.decode('utf-8', errors='replace')
for m in re.finditer(r'class="[^"]*alert[^"]*"[^>]*>.*?</div>', html, re.S):
    s = re.sub(r'<[^>]+>', ' ', m.group(0))
    s = ' '.join(s.split())[:200]
    print('ALERT:', s)
for pat in ['alert-danger', 'errornote', 'messagelist', 'tablers']:
    print(pat, html.count(pat))
PY
"""
_, o, e = c.exec_command(cmd, timeout=90)
print(o.read().decode())
c.close()
