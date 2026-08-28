#!/usr/bin/env python3
import io, re, urllib.parse, urllib.request, http.cookiejar
from pathlib import Path
import paramiko, puttykeys

phrase = Path(r"F:\servidor\frase-clave.txt").read_text().strip().splitlines()[0]
ppk = Path(r"F:\servidor\cph_private_key.ppk").read_text(encoding="utf-8", errors="replace")
pkey = paramiko.Ed25519Key.from_private_key(io.StringIO(puttykeys.ppkraw_to_openssh(ppk, passphrase=phrase)))
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("190.169.110.9", username="cph", pkey=pkey, timeout=30)

remote_script = r'''
import re, urllib.request, urllib.parse, http.cookiejar

def login(base, user, pwd):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    login_url = base + "/admin/login/"
    html = op.open(login_url).read().decode()
    token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html).group(1)
    data = urllib.parse.urlencode({
        "csrfmiddlewaretoken": token,
        "username": user,
        "password": pwd,
        "next": "/admin/",
    }).encode()
    req = urllib.request.Request(login_url, data=data, headers={"Referer": login_url}, method="POST")
    resp = op.open(req)
    body = resp.read().decode()
    ok = "Site administration" in body or "Log out" in body or resp.geturl().rstrip("/").endswith("/admin")
    return ok, resp.geturl(), ("FAIL" if "Please enter the correct" in body else "ok")

for base in ["http://127.0.0.1:8000", "http://127.0.0.1"]:
    try:
        ok, url, note = login(base, "cph", "CphAdmin2026")
        print(base, "=>", "LOGIN OK" if ok else "LOGIN FAIL", url, note)
    except Exception as ex:
        print(base, "=> ERROR", ex)
'''

sftp = c.open_sftp()
with sftp.open("/tmp/test_admin_login.py", "w") as f:
    f.write(remote_script)
sftp.close()

cmd = (
    "pgrep -af gunicorn | head -2; "
    "python3 /tmp/test_admin_login.py"
)
_, o, e = c.exec_command(cmd, timeout=60)
print(o.read().decode())
print(e.read().decode())
c.close()
