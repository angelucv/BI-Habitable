#!/usr/bin/env python3
import io
from pathlib import Path
import paramiko, puttykeys

ROOT = Path(__file__).resolve().parent
phrase = Path(r"F:\servidor\frase-clave.txt").read_text().strip().splitlines()[0]
ppk = Path(r"F:\servidor\cph_private_key.ppk").read_text(encoding="utf-8", errors="replace")
pkey = paramiko.Ed25519Key.from_private_key(io.StringIO(puttykeys.ppkraw_to_openssh(ppk, passphrase=phrase)))
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("190.169.110.9", username="cph", pkey=pkey, timeout=30)

sftp = c.open_sftp()
for name in ("start_gunicorn.sh",):
    data = (ROOT / name).read_bytes().replace(b"\r\n", b"\n")
    with sftp.open(f"/tmp/{name}", "wb") as f:
        f.write(data)
sftp.close()

_, o, e = c.exec_command("chmod +x /tmp/start_gunicorn.sh && bash /tmp/start_gunicorn.sh", timeout=90)
out = o.read().decode("utf-8", errors="replace")
err = e.read().decode("utf-8", errors="replace")
print(out)
if err.strip():
    print("STDERR:", err)
c.close()
