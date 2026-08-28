#!/usr/bin/env python3
"""Despliega guía PDF didáctica y genera borrador en servidor (WeasyPrint)."""
from __future__ import annotations

import io
from pathlib import Path

import paramiko
import puttykeys

BASE = Path(__file__).resolve().parent.parent
FASE2 = BASE / "fase2-rojo"
REMOTE = "/home/cph/apps/fase2-rojo"
OUT_LOCAL = BASE / "Guia-usuario-Fase-II-ROJO-BORRADOR.pdf"
PHRASE = Path(r"F:\servidor\frase-clave.txt").read_text().strip().splitlines()[0]
PPK = Path(r"F:\servidor\cph_private_key.ppk").read_text(encoding="utf-8", errors="replace")

UPLOAD = [
    FASE2 / "inspecciones" / "guia_pdf.py",
    FASE2 / "inspecciones" / "views.py",
    FASE2 / "inspecciones" / "admin_dashboard.py",
    FASE2 / "config" / "urls.py",
    FASE2 / "config" / "settings.py",
    FASE2 / "templates" / "inspecciones" / "guia_usuario_pdf.html",
    FASE2 / "templates" / "includes" / "cpeh_guia_tutorial_sistema.html",
    FASE2 / "inspecciones" / "management" / "commands" / "generar_guia_usuario_pdf.py",
    FASE2 / "manage.py",
]


def connect() -> paramiko.SSHClient:
    pkey = paramiko.Ed25519Key.from_private_key(
        io.StringIO(puttykeys.ppkraw_to_openssh(PPK, passphrase=PHRASE))
    )
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("190.169.110.9", username="cph", pkey=pkey, timeout=120)
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
        if local.is_file():
            upload_file(sftp, local, f"{REMOTE}/{local.relative_to(FASE2).as_posix()}")

    remote_pdf = f"{REMOTE}/media/docs/guia-usuario-fase2-rojo-borrador.pdf"
    cmd = f"""
set -e
cd {REMOTE}
source .venv/bin/activate
mkdir -p media/docs
python manage.py generar_guia_usuario_pdf --salida {remote_pdf}
bash run/ensure-running.sh
python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/guia/usuario.pdf', timeout=10); print('guia pdf http', r.status, len(r.read()), 'bytes')"
"""
    _, stdout, stderr = client.exec_command(cmd, timeout=180)
    print(stdout.read().decode("utf-8", errors="replace"))
    err = stderr.read().decode("utf-8", errors="replace")
    if err.strip():
        print("STDERR:", err[-3000:])

    with sftp.open(remote_pdf, "rb") as rf:
        OUT_LOCAL.write_bytes(rf.read())
    print(f"Descargado → {OUT_LOCAL} ({OUT_LOCAL.stat().st_size:,} bytes)")
    sftp.close()
    client.close()
    print("Preview web: http://190.169.110.9/guia/usuario.pdf")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
