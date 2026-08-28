#!/usr/bin/env bash
# Reinicia Gunicorn sin matar la sesión SSH que invoca pkill -f con el mismo patrón.
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
mkdir -p logs media

mapfile -t PIDS < <(pgrep -f '/home/cph/apps/fase2-rojo/.venv/bin/gunicorn' || true)
for pid in "${PIDS[@]}"; do
  if [[ -r "/proc/$pid/cmdline" ]] && grep -q 'gunicorn' "/proc/$pid/cmdline" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
  fi
done
sleep 2
nohup gunicorn config.wsgi:application -c gunicorn.conf.py >> logs/nohup.out 2>&1 &
sleep 3
pgrep -af '/home/cph/apps/fase2-rojo/.venv/bin/gunicorn' | head -3 || true
