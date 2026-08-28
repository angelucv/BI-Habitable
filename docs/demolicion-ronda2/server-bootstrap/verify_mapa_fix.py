#!/usr/bin/env python3
"""Verifica que mapa_casos responde sin FieldError."""
from __future__ import annotations

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

script = r"""
cd /home/cph/apps/fase2-rojo
source .venv/bin/activate
python -c "
import os,django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
django.setup()
from django.test import RequestFactory
from django.contrib.auth.models import User
from inspecciones.views import mapa_casos, casos_geojson
rf = RequestFactory()
user = User.objects.filter(is_staff=True).first()
req = rf.get('/mapa/')
req.user = user
resp = mapa_casos(req)
print('mapa status:', resp.status_code)
req2 = rf.get('/api/casos/geojson/')
req2.user = user
resp2 = casos_geojson(req2)
import json
data = json.loads(resp2.content)
print('geojson features:', len(data.get('features', [])))
"
"""
_, o, e = c.exec_command(script, timeout=60)
print(o.read().decode("utf-8", errors="replace"))
err = e.read().decode("utf-8", errors="replace")
if err.strip():
    print("ERR:", err[-2000:])
c.close()
