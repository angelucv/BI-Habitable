#!/usr/bin/env python3
import io
from pathlib import Path
import paramiko
import puttykeys

phrase = Path(r"F:\servidor\frase-clave.txt").read_text().strip().splitlines()[0]
ppk = Path(r"F:\servidor\cph_private_key.ppk").read_text(encoding="utf-8", errors="replace")
pkey = paramiko.Ed25519Key.from_private_key(io.StringIO(puttykeys.ppkraw_to_openssh(ppk, passphrase=phrase)))
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("190.169.110.9", username="cph", pkey=pkey, timeout=30)
remote_script = r"""
cd ~/apps/fase2-rojo && source .venv/bin/activate
python manage.py shell <<'PY'
import django
from django.test import Client, RequestFactory
from django.contrib.auth import get_user_model
from inspecciones.models import CasoRojo
from inspecciones.views import caso_rojo_pdf
caso = CasoRojo.objects.first()
print("PK", caso.pk, "HAB", caso.hab_id)
factory = RequestFactory()
req = factory.get(f"/admin/inspecciones/casorojo/{caso.pk}/pdf/", HTTP_HOST="190.169.110.9")
User = get_user_model()
req.user = User.objects.filter(is_superuser=True).first()
r = caso_rojo_pdf(req, caso.pk)
print("STATUS", r.status_code, "TYPE", r.get("Content-Type", ""), "LEN", len(r.content))
PY
"""
_, out, err = c.exec_command(remote_script, timeout=120)
print(out.read().decode())
e = err.read().decode()
if e.strip():
    print("STDERR:", e[-4000:])
c.close()
