#!/usr/bin/env python3
from __future__ import annotations
import io
from pathlib import Path
import paramiko, puttykeys

phrase = Path(r"F:\servidor\frase-clave.txt").read_text().strip().splitlines()[0]
ppk = Path(r"F:\servidor\cph_private_key.ppk").read_text(encoding="utf-8", errors="replace")
pkey = paramiko.Ed25519Key.from_private_key(io.StringIO(puttykeys.ppkraw_to_openssh(ppk, passphrase=phrase)))
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("190.169.110.9", username="cph", pkey=pkey, timeout=30)

script = """
echo '=== SERVICIOS ==='
systemctl is-active fase2-rojo apache2 postgresql 2>/dev/null || true
echo '=== ENV (sin password) ==='
grep -E '^(DATABASE_ENGINE|DB_NAME|DB_USER|DB_HOST|DB_PORT)=' ~/apps/fase2-rojo/.env
grep -q '^DB_PASSWORD=' ~/apps/fase2-rojo/.env && echo 'DB_PASSWORD=*** configurada'
echo '=== HEALTH local apache ==='
python3 -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1/api/health/').read().decode())"
echo '=== STATUS gunicorn ==='
systemctl status fase2-rojo --no-pager -l | head -15
"""
_, o, e = c.exec_command(script, timeout=60)
print(o.read().decode("utf-8", errors="replace"))
err = e.read().decode("utf-8", errors="replace")
if err.strip():
    print("ERR:", err)
c.close()
