#!/usr/bin/env python3
"""Despliega tablero asignación + fix servicio Gunicorn."""
from __future__ import annotations

import io
from pathlib import Path

import paramiko
import puttykeys

BASE = Path(__file__).resolve().parent.parent
FASE2 = BASE / "fase2-rojo"
REMOTE = "/home/cph/apps/fase2-rojo"
PHRASE = Path(r"F:\servidor\frase-clave.txt").read_text().strip().splitlines()[0]
PPK = Path(r"F:\servidor\cph_private_key.ppk").read_text(encoding="utf-8", errors="replace")

UPLOAD = [
    FASE2 / "inspecciones" / "asignacion.py",
    FASE2 / "inspecciones" / "asignacion_views.py",
    FASE2 / "inspecciones" / "admin.py",
    FASE2 / "inspecciones" / "admin_dashboard.py",
    FASE2 / "inspecciones" / "excel_plantilla.py",
    FASE2 / "inspecciones" / "choices.py",
    FASE2 / "inspecciones" / "workflow.py",
    FASE2 / "inspecciones" / "import_informes_pdf.py",
    FASE2 / "inspecciones" / "models.py",
    FASE2 / "inspecciones" / "section_labels.py",
    FASE2 / "inspecciones" / "migrations" / "0005_d1_complementos_d1_d4.py",
    FASE2 / "inspecciones" / "export_views.py",
    FASE2 / "templates" / "includes" / "cpeh_guia_decisiones_d.html",
    FASE2 / "templates" / "includes" / "cpeh_guia_informe.html",
    FASE2 / "templates" / "includes" / "cpeh_guia_desarrolladores.html",
    FASE2 / "config" / "urls.py",
    FASE2 / "config" / "jazzmin_settings.py",
    FASE2 / "templates" / "inspecciones" / "tablero_asignacion.html",
    FASE2 / "templates" / "inspecciones" / "mapa_casos.html",
    FASE2 / "templates" / "includes" / "cpeh_guia_fase.html",
    FASE2 / "templates" / "includes" / "cpeh_guia_tutorial_sistema.html",
    FASE2 / "templates" / "includes" / "cpeh_guia_flujo_core.html",
    FASE2 / "templates" / "includes" / "cpeh_guia_roles_asignacion.html",
    FASE2 / "templates" / "admin" / "base_site.html",
    FASE2 / "templates" / "admin" / "index.html",
    FASE2 / "templates" / "admin" / "login.html",
    FASE2 / "templates" / "admin" / "inspecciones" / "casorojo" / "change_form.html",
    FASE2 / "templates" / "registration" / "logged_out.html",
    FASE2 / "inspecciones" / "static" / "css" / "cpeh_admin.css",
    FASE2 / "run" / "ensure-running.sh",
    FASE2 / "run" / "restart-gunicorn.sh",
]


def connect() -> paramiko.SSHClient:
    pkey = paramiko.Ed25519Key.from_private_key(
        io.StringIO(puttykeys.ppkraw_to_openssh(PPK, passphrase=PHRASE))
    )
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("190.169.110.9", username="cph", pkey=pkey, timeout=60)
    return client


def upload_file(sftp: paramiko.SFTPClient, local: Path, remote: str) -> None:
    data = local.read_bytes().replace(b"\r\n", b"\n")
    parts = remote.split("/")
    for i in range(2, len(parts)):
        d = "/".join(parts[:i])
        try:
            sftp.mkdir(d)
        except OSError:
            pass
    with sftp.open(remote, "wb") as f:
        f.write(data)
    print("OK", remote)


def main() -> int:
    client = connect()
    sftp = client.open_sftp()
    for local in UPLOAD:
        remote = f"{REMOTE}/{local.relative_to(FASE2).as_posix()}"
        upload_file(sftp, local, remote)
    sftp.close()

    cmd = f"""
set -e
cd {REMOTE}
source .venv/bin/activate
chmod +x run/ensure-running.sh run/restart-gunicorn.sh
python manage.py migrate --noinput
bash run/restart-gunicorn.sh
python manage.py collectstatic --noinput
python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health/').read().decode())"
python -c "
import os,django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
django.setup()
from django.test import RequestFactory
from django.contrib.auth.models import User
from inspecciones.asignacion_views import tablero_asignacion
from inspecciones.asignacion import kpis_asignacion
user = User.objects.filter(is_superuser=True).first()
rf = RequestFactory()
req = rf.get('/asignacion/')
req.user = user
resp = tablero_asignacion(req)
print('asignacion status:', resp.status_code)
print('kpis:', kpis_asignacion())
from inspecciones.models import CasoRojo
from inspecciones.excel_plantilla import generar_excel_informe, generar_excel_lote, EXPORT_COLUMNS
c = CasoRojo.objects.first()
if c:
    inf = generar_excel_informe(c)
    lot = generar_excel_lote([c])
    print('excel cols', len(EXPORT_COLUMNS), 'informe', len(inf), 'lote', len(lot))
else:
    print('excel: sin casos en BD')
"
"""
    _, stdout, stderr = client.exec_command(cmd, timeout=120)
    print(stdout.read().decode("utf-8", errors="replace"))
    err = stderr.read().decode("utf-8", errors="replace")
    if err.strip():
        print("STDERR:", err[-2000:])
    client.close()
    print("\nDesplegado — http://190.169.110.9/asignacion/ · http://190.169.110.9/admin/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
