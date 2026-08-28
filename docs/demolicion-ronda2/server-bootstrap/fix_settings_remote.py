#!/usr/bin/env python3
"""Repara settings.py duplicado en servidor."""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import paramiko
import puttykeys

PPK = Path(r"F:\servidor\cph_private_key.ppk")
PHRASE_FILE = Path(r"F:\servidor\frase-clave.txt")


def main() -> int:
    phrase = PHRASE_FILE.read_text(encoding="utf-8").strip()
    ppk = PPK.read_text(encoding="utf-8", errors="replace")
    openssh = puttykeys.ppkraw_to_openssh(ppk, passphrase=phrase)
    pkey = paramiko.Ed25519Key.from_private_key(io.StringIO(openssh))
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("190.169.110.9", username="cph", pkey=pkey, timeout=30)

    fix = r'''
python3 << 'PY'
from pathlib import Path
import re
p = Path("/home/cph/apps/fase2-rojo/config/settings.py")
text = p.read_text(encoding="utf-8")
# quitar duplicados en INSTALLED_APPS
m = re.search(r"INSTALLED_APPS = \[(.*?)\n\]", text, re.S)
if m:
    block = m.group(0)
    items = re.findall(r"['\"]([^'\"]+)['\"]", block)
    seen = set()
    unique = []
    for i in items:
        if i not in seen:
            seen.add(i)
            unique.append(i)
    new_block = "INSTALLED_APPS = [\n" + "".join(f"    '{x}',\n" for x in unique) + "]"
    text = text[:m.start()] + new_block + text[m.end():]
    p.write_text(text, encoding="utf-8")
    print("fixed", unique)
PY
cd ~/apps/fase2-rojo && source .venv/bin/activate && python manage.py check
'''
    stdin, stdout, stderr = client.exec_command(fix, timeout=120)
    print(stdout.read().decode("utf-8", errors="replace"))
    err = stderr.read().decode("utf-8", errors="replace")
    if err.strip():
        print("ERR:", err)
    client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
