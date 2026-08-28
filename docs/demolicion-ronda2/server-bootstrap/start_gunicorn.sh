#!/usr/bin/env bash
set -euo pipefail
cd ~/apps/fase2-rojo
source .venv/bin/activate
pkill -f 'gunicorn config.wsgi' 2>/dev/null || true
sleep 2
mkdir -p logs
# Apache proxy apunta a 127.0.0.1:8000
grep -q '127.0.0.1:8000' gunicorn.conf.py || sed -i 's/0.0.0.0:8000/127.0.0.1:8000/' gunicorn.conf.py
nohup ./run/start-gunicorn.sh >> logs/nohup.out 2>&1 &
sleep 4
echo "=== GUNICORN ==="
pgrep -af gunicorn || echo "NO GUNICORN"
ss -tlnp | grep 8000 || true
echo "=== HEALTH ==="
python3 -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health/').read().decode())"
echo "=== ADMIN LOGIN ==="
python3 /tmp/test_admin_login.py
