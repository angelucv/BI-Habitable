#!/usr/bin/env python3
from __future__ import annotations
import io
from pathlib import Path
import paramiko, puttykeys

PWD = "cph%0000"
phrase = Path(r"F:\servidor\frase-clave.txt").read_text().strip().splitlines()[0]
ppk = Path(r"F:\servidor\cph_private_key.ppk").read_text(encoding="utf-8", errors="replace")
pkey = paramiko.Ed25519Key.from_private_key(io.StringIO(puttykeys.ppkraw_to_openssh(ppk, passphrase=phrase)))
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("190.169.110.9", username="cph", pkey=pkey, timeout=30)

remote_py = f"""
import os, django
os.chdir('/home/cph/apps/fase2-rojo')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.contrib.auth import get_user_model, authenticate
U = get_user_model()
for name in ('cph', 'admin'):
    u, created = U.objects.get_or_create(username=name, defaults={{'email': ''}})
    u.is_superuser = u.is_staff = u.is_active = True
    u.set_password({PWD!r})
    u.save()
    ok = authenticate(username=name, password={PWD!r})
    print(name, 'updated', 'auth OK' if ok else 'auth FAIL')
"""

script = f"cd ~/apps/fase2-rojo && source .venv/bin/activate && python3 << 'EOF'\n{remote_py}\nEOF"
_, o, e = c.exec_command(script, timeout=60)
print(o.read().decode("utf-8", errors="replace"))
if e.read().decode().strip():
    print("ERR")
c.close()
