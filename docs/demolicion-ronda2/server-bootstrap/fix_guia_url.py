#!/usr/bin/env python3
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
c.connect("190.169.110.9", username="cph", pkey=pkey, timeout=60)
cmd = """
cd /home/cph/apps/fase2-rojo
bash run/ensure-running.sh
curl -s -o /dev/null -w 'health:%{http_code}\\n' http://127.0.0.1:8000/api/health/
curl -s -o /dev/null -w 'guia:%{http_code}\\n' http://127.0.0.1:8000/guia/usuario.pdf
"""
_, o, e = c.exec_command(cmd, timeout=90)
print(o.read().decode("utf-8", errors="replace"))
err = e.read().decode("utf-8", errors="replace")
if err.strip():
    print("ERR:", err)
c.close()
