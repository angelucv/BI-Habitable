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
cmd = r"""
cd /home/cph/apps/fase2-rojo && source .venv/bin/activate
python << 'PY'
import os, django, re
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.test import Client
from django.contrib.auth.models import User
from django.urls import reverse
print('reverse guia:', reverse('guia_usuario_pdf'))
u = User.objects.filter(is_superuser=True).first()
client = Client(HTTP_HOST='190.169.110.9')
client.force_login(u)
r = client.get('/admin/')
html = r.content.decode('utf-8', errors='replace')
print('status', r.status_code, 'len', len(html))
for pat in ['NoReverseMatch', 'TemplateSyntaxError', 'Exception Value', 'errorlist', 'undefined', 'BORRADOR', 'guia/usuario.pdf']:
    print(pat, '->', pat in html or pat.lower() in html.lower())
# snippet around guia banner
idx = html.find('Guía de usuario')
if idx >= 0:
    print('--- snippet ---')
    print(html[idx-200:idx+600])
# check for django debug page
if 'Server Error' in html or 'Traceback' in html:
    print('DEBUG PAGE DETECTED')
    print(html[:2000])
PY
"""
_, o, e = c.exec_command(cmd, timeout=90)
print(o.read().decode("utf-8", errors="replace"))
if e.read().decode().strip():
    print("ERR", e.read())
c.close()
