#!/usr/bin/env python3
"""Despliega bootstrap-user.sh en el servidor vía SSH."""
from __future__ import annotations

import io
import sys
from pathlib import Path

import paramiko
import puttykeys

ROOT = Path(__file__).resolve().parent
PPK = Path(r"F:\servidor\cph_private_key.ppk")
PHRASE_FILE = Path(r"F:\servidor\frase-clave.txt")


def ssh_passphrase() -> str:
    return PHRASE_FILE.read_text(encoding="utf-8").strip().splitlines()[0]
HOST = "190.169.110.9"
USER = "cph"
REMOTE_BOOT = "/home/cph/apps/fase2-rojo/bootstrap"


def connect() -> paramiko.SSHClient:
    phrase = ssh_passphrase()
    ppk = PPK.read_text(encoding="utf-8", errors="replace")
    openssh = puttykeys.ppkraw_to_openssh(ppk, passphrase=phrase)
    pkey = paramiko.Ed25519Key.from_private_key(io.StringIO(openssh))
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, pkey=pkey, timeout=30)
    return client


def upload_scripts(client: paramiko.SSHClient) -> None:
    sftp = client.open_sftp()
    for part in ["/home/cph/apps", "/home/cph/apps/fase2-rojo", REMOTE_BOOT]:
        try:
            sftp.mkdir(part)
        except OSError:
            pass
    for name in ("bootstrap-user.sh", "bootstrap-sudo.sh"):
        data = (ROOT / name).read_bytes().replace(b"\r\n", b"\n")
        with sftp.open(f"{REMOTE_BOOT}/{name}", "wb") as f:
            f.write(data)
    sftp.close()


def run(client: paramiko.SSHClient, cmd: str, timeout: int = 900) -> tuple[int, str, str]:
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return stdout.channel.recv_exit_status(), out, err


def patch_bootstrap_for_virtualenv() -> None:
    text = (ROOT / "bootstrap-user.sh").read_text(encoding="utf-8")
    old = """if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi"""
    new = """if [[ ! -d .venv ]]; then
  python3 -m pip install --user --upgrade pip virtualenv -q
  python3 -m virtualenv .venv
fi"""
    if old in text and new not in text:
        (ROOT / "bootstrap-user.sh").write_text(text.replace(old, new), encoding="utf-8", newline="\n")


def main() -> int:
    patch_bootstrap_for_virtualenv()
    client = connect()
    upload_scripts(client)
    print("Scripts subidos.")

    code, out, err = run(
        client,
        f"chmod +x {REMOTE_BOOT}/*.sh && bash {REMOTE_BOOT}/bootstrap-user.sh",
    )
    print(out)
    if err.strip():
        print("STDERR:", err[-5000:])
    print("bootstrap-user exit", code)

    if code == 0:
        start_cmd = (
            "cd ~/apps/fase2-rojo && "
            "if ! pgrep -f 'gunicorn config.wsgi' >/dev/null 2>&1; then "
            "nohup ./run/start-gunicorn.sh > logs/nohup.out 2>&1 & sleep 3; fi; "
            "pgrep -af gunicorn | head -3; "
            "python3 -c 'import urllib.request; r=urllib.request.urlopen(\"http://127.0.0.1:8000/api/health/\"); print(r.read().decode())'"
        )
        code2, out2, err2 = run(client, start_cmd, timeout=60)
        print("--- servicio ---")
        print(out2.strip())
        if err2.strip():
            print("start err:", err2[-1000:])

    client.close()
    return code


if __name__ == "__main__":
    sys.exit(main())
