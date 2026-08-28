#!/usr/bin/env bash
# Reinicia Gunicorn — prefiere systemd; fallback a script local
set -euo pipefail
cd "$(dirname "$0")/.."
APP_DIR="$(pwd)"

health_ok() {
  python3 -c "
import urllib.request
urllib.request.urlopen('http://127.0.0.1:8000/api/health/', timeout=3)
" 2>/dev/null
}

if systemctl is-active --quiet fase2-rojo 2>/dev/null; then
  if health_ok; then
    echo "systemd fase2-rojo activo y responde"
    exit 0
  fi
  echo "systemd activo pero health falló — reiniciando..."
  sudo systemctl restart fase2-rojo 2>/dev/null || bash run/restart-gunicorn.sh
  sleep 3
  health_ok && exit 0
fi

if pgrep -f '/home/cph/apps/fase2-rojo/.venv/bin/gunicorn' >/dev/null 2>&1; then
  if health_ok; then
    echo "Gunicorn nohup activo y responde"
    exit 0
  fi
  echo "Gunicorn activo pero health falló — reiniciando..."
fi

bash run/restart-gunicorn.sh
sleep 2
health_ok || { echo "ERROR: Gunicorn no responde en :8000"; exit 1; }
echo "Gunicorn OK"
