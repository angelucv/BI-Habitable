#!/usr/bin/env python3
import io, re
from pathlib import Path
import paramiko, puttykeys

phrase = Path(r"F:\servidor\frase-clave.txt").read_text().strip().splitlines()[0]
ppk = Path(r"F:\servidor\cph_private_key.ppk").read_text(encoding="utf-8", errors="replace")
pkey = paramiko.Ed25519Key.from_private_key(io.StringIO(puttykeys.ppkraw_to_openssh(ppk, passphrase=phrase)))
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("190.169.110.9", username="cph", pkey=pkey, timeout=30)
remote = """
python3 << 'PY'
import urllib.request
html = urllib.request.urlopen('http://127.0.0.1/admin/login/').read().decode()
print('jazzmin' in html.lower(), 'bootstrap' in html.lower(), 'admin/css' in html.lower())
for pat in ['jazzmin', 'bootstrap', '/static/']:
    if pat in html:
        print('found', pat)
print('title snippet:', html[html.find('<title'):html.find('</title>')+8][:120])
PY
pgrep -af gunicorn | head -2
"""
_, o, _ = c.exec_command(remote, timeout=30)
print(o.read().decode())
c.close()
