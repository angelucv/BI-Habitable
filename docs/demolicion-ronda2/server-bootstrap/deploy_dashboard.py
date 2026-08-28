#!/usr/bin/env python3
"""Despliega logo + dashboard portada admin."""
from __future__ import annotations

import io
from pathlib import Path

import paramiko
import puttykeys

ROOT = Path(__file__).resolve().parent.parent / "fase2-rojo"
REMOTE = "/home/cph/apps/fase2-rojo"
PHRASE = Path(r"F:\servidor\frase-clave.txt").read_text().strip().splitlines()[0]
PPK = Path(r"F:\servidor\cph_private_key.ppk").read_text(encoding="utf-8", errors="replace")

FILES = [
    ROOT / "static/img/logo-cpeh.svg",
    ROOT / "static/img/logo-cpeh-redes.svg",
    ROOT / "static/img/logo-cpeh-sidebar.svg",
    ROOT / "templates/includes/cpeh_nombre_institucional.html",
    ROOT / "templates/includes/cpeh_guia_fase.html",
    ROOT / "templates/includes/cpeh_guia_informe.html",
    ROOT / "templates/includes/cpeh_guia_desarrolladores.html",
    ROOT / "templates/includes/cpeh_footer_bandera.html",
    ROOT / "templates/admin/base_site.html",
    ROOT / "templates/admin/index.html",
    ROOT / "templates/admin/login.html",
    ROOT / "templates/registration/logged_out.html",
    ROOT / "templates/admin/inspecciones/casorojo/change_form.html",
    ROOT / "templates/inspecciones/caso_rojo_informe_pdf.html",
    ROOT / "inspecciones/views.py",
    ROOT / "inspecciones/section_labels.py",
    ROOT / "inspecciones/report_sections.py",
    ROOT / "inspecciones/admin.py",
    ROOT / "inspecciones/admin_dashboard.py",
    ROOT / "inspecciones/apps.py",
    ROOT / "inspecciones/static/css/cpeh_admin.css",
    ROOT / "config/jazzmin_settings.py",
    ROOT / "config/settings.py",
]


def connect() -> paramiko.SSHClient:
    pkey = paramiko.Ed25519Key.from_private_key(
        io.StringIO(puttykeys.ppkraw_to_openssh(PPK, passphrase=PHRASE))
    )
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("190.169.110.9", username="cph", pkey=pkey, timeout=30)
    return client


def upload(sftp: paramiko.SFTPClient, local: Path) -> None:
    rel = local.relative_to(ROOT).as_posix()
    remote = f"{REMOTE}/{rel}"
    data = local.read_bytes().replace(b"\r\n", b"\n")
    parts = remote.split("/")
    for i in range(3, len(parts)):
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
    for f in FILES:
        upload(sftp, f)
    sftp.close()

    cmd = f"""
cd {REMOTE} && source .venv/bin/activate
pip install -q weasyprint
python manage.py check
python manage.py collectstatic --noinput
pkill -f 'gunicorn config.wsgi' 2>/dev/null || true
sleep 2
~/apps/fase2-rojo/run/ensure-running.sh
"""
    _, stdout, stderr = client.exec_command(cmd, timeout=180)
    print(stdout.read().decode("utf-8", errors="replace"))
    err = stderr.read().decode("utf-8", errors="replace")
    if err.strip():
        print("STDERR:", err[-3000:])
    client.close()
    print("Dashboard desplegado — Ctrl+F5 en /admin/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
