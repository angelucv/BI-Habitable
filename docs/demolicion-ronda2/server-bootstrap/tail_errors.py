#!/usr/bin/env python3
import io
from pathlib import Path
import paramiko, puttykeys

phrase = Path(r"F:\servidor\frase-clave.txt").read_text().strip().splitlines()[0]
ppk = Path(r"F:\servidor\cph_private_key.ppk").read_text(encoding="utf-8", errors="replace")
pkey = paramiko.Ed25519Key.from_private_key(io.StringIO(puttykeys.ppkraw_to_openssh(ppk, passphrase=phrase)))
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("190.169.110.9", username="cph", pkey=pkey, timeout=60)
_, o, _ = c.exec_command("grep -i 'error\\|traceback\\|500' /home/cph/apps/fase2-rojo/logs/nohup.out 2>/dev/null | tail -20", timeout=30)
print(o.read().decode())
c.close()
