#!/usr/bin/env python3
"""Lee settings.py del servidor."""
import io
from pathlib import Path
import paramiko, puttykeys

phrase = Path(r"F:\servidor\frase-clave.txt").read_text().strip().splitlines()[0]
ppk = Path(r"F:\servidor\cph_private_key.ppk").read_text(encoding="utf-8", errors="replace")
pkey = paramiko.Ed25519Key.from_private_key(io.StringIO(puttykeys.ppkraw_to_openssh(ppk, passphrase=phrase)))
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("190.169.110.9", username="cph", pkey=pkey, timeout=30)
_, o, _ = c.exec_command("cat ~/apps/fase2-rojo/config/settings.py; echo '---URLS---'; cat ~/apps/fase2-rojo/config/urls.py")
print(o.read().decode("utf-8", errors="replace")[:8000])
c.close()
