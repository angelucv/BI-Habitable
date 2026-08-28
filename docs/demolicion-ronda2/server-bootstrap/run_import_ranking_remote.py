#!/usr/bin/env python3
"""Re-sube Excel binario y ejecuta import masivo."""
from __future__ import annotations

import io
from pathlib import Path

import paramiko
import puttykeys

EXCEL = Path(__file__).resolve().parent.parent / "cruce-informes-demolicion-habitable-2026-08-20-v2.xlsx"
PHRASE = Path(r"F:\servidor\frase-clave.txt").read_text().strip().splitlines()[0]
PPK = Path(r"F:\servidor\cph_private_key.ppk").read_text(encoding="utf-8", errors="replace")


def main() -> int:
    pkey = paramiko.Ed25519Key.from_private_key(
        io.StringIO(puttykeys.ppkraw_to_openssh(PPK, passphrase=PHRASE))
    )
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("190.169.110.9", username="cph", pkey=pkey, timeout=60)
    sftp = c.open_sftp()
    remote = "/home/cph/data/cruce-informes-demolicion-habitable-2026-08-20-v2.xlsx"
    with sftp.open(remote, "wb") as f:
        f.write(EXCEL.read_bytes())
    print(f"Excel OK: {EXCEL.stat().st_size} bytes")
    sftp.close()

    cmd = """
cd ~/apps/fase2-rojo && source .venv/bin/activate
python manage.py importar_ranking --excel /home/cph/data/cruce-informes-demolicion-habitable-2026-08-20-v2.xlsx --hoja Ranking_ROJO_LaGuaira --solo-gps
~/apps/fase2-rojo/run/ensure-running.sh
"""
    _, stdout, stderr = c.exec_command(cmd, timeout=600)
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err.strip():
        print("STDERR:", err[-3000:])
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
