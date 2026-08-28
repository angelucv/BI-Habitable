#!/usr/bin/env python3
import io
from pathlib import Path
import paramiko, puttykeys

phrase = Path(r"F:\servidor\frase-clave.txt").read_text().strip().splitlines()[0]
ppk = Path(r"F:\servidor\cph_private_key.ppk").read_text(encoding="utf-8", errors="replace")
pkey = paramiko.Ed25519Key.from_private_key(io.StringIO(puttykeys.ppkraw_to_openssh(ppk, passphrase=phrase)))
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("190.169.110.9", username="cph", pkey=pkey, timeout=30)

_, o, e = c.exec_command(
    "cd ~/apps/fase2-rojo && source .venv/bin/activate && "
    "pgrep -af gunicorn; "
    "python3 docs/demolicion-ronda2/server-bootstrap/test_login_http.py 2>&1 || "
    "python3 -c \""
    "import re,urllib.request,urllib.parse,http.cookiejar;"
    "cj=http.cookiejar.CookieJar();op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj));"
    "html=op.open('http://127.0.0.1/admin/login/').read().decode();"
    "t=re.search(r'csrfmiddlewaretoken\\\" value=\\\"([^\\\"]+)',html).group(1);"
    "d=urllib.parse.urlencode({'csrfmiddlewaretoken':t,'username':'cph','password':'CphAdmin2026','next':'/admin/'}).encode();"
    "r=op.open(urllib.request.Request('http://127.0.0.1/admin/login/',data=d,headers={'Referer':'http://127.0.0.1/admin/login/'}));"
    "b=r.read().decode();print('URL',r.geturl());print('OK' if 'Site administration' in b or 'Log out' in b else 'FAIL');"
    "print('apache test:', end=' ');"
    "html2=op.open('http://127.0.0.1/admin/login/').read().decode()[:50]"
    "\"",
    timeout=60,
)
print(o.read().decode("utf-8", errors="replace"))
print(e.read().decode("utf-8", errors="replace"))
c.close()
