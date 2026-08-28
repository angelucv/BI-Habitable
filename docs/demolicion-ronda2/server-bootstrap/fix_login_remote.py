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

NEW_PWD = "CphAdmin2026"

remote = f'''
cd ~/apps/fase2-rojo && source .venv/bin/activate
echo "=== .env DB ==="
grep -E "^DATABASE|^DB_" .env | sed 's/DB_PASSWORD=.*/DB_PASSWORD=***/'
echo "=== GUNICORN ENV ==="
grep -E "^DATABASE|^DB_" /proc/$(pgrep -f "gunicorn config.wsgi" | head -1)/environ 2>/dev/null | tr "\\0" "\\n" | grep -E "^DATABASE|^DB_" | head -5 || echo "(no gunicorn pid)"
python3 << 'PYEOF'
import os
os.chdir("/home/cph/apps/fase2-rojo")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from django.conf import settings
from django.contrib.auth import get_user_model, authenticate
print("DB ENGINE:", settings.DATABASES["default"]["ENGINE"])
print("DB NAME:", settings.DATABASES["default"].get("NAME"))
U = get_user_model()
print("USERS:", U.objects.count())
for u in U.objects.all():
    print(" ", repr(u.username), "staff", u.is_staff, "super", u.is_superuser, "active", u.is_active)
for pwd in ["cph%0000", "cph%000", "CphAdmin2026"]:
    ok = authenticate(username="cph", password=pwd)
    print("auth cph +", repr(pwd), "=>", "OK" if ok else "FAIL")
u = U.objects.get(username="cph")
u.set_password("{NEW_PWD}")
u.is_staff = u.is_superuser = u.is_active = True
u.save()
print("RESET to CphAdmin2026 =>", "OK" if authenticate(username="cph", password="{NEW_PWD}") else "FAIL")
PYEOF
pkill -f "gunicorn config.wsgi" 2>/dev/null || true
sleep 2
nohup ./run/start-gunicorn.sh >> logs/nohup.out 2>&1 &
sleep 3
pgrep -af gunicorn | head -3
'''

_, o, e = c.exec_command(remote, timeout=120)
print(o.read().decode("utf-8", errors="replace"))
err = e.read().decode("utf-8", errors="replace")
if err.strip():
    print("STDERR:", err[:500])
c.close()
