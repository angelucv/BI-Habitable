#!/usr/bin/env bash
# Instalación Fase II ROJO — requiere sudo (ejecutar en MobaXterm: bash bootstrap-sudo.sh)
set -euo pipefail

APP_DIR="${HOME}/apps/fase2-rojo"
DB_NAME="${DB_NAME:-fase2_rojo}"
DB_USER="${DB_USER:-fase2_app}"

if [[ "${EUID}" -ne 0 ]]; then
  SUDO="sudo"
else
  SUDO=""
fi

echo ">> Paquetes del sistema..."
export DEBIAN_FRONTEND=noninteractive
${SUDO} apt-get update -qq
${SUDO} apt-get install -y -qq \
  postgresql postgresql-contrib \
  python3-venv python3-pip python3-dev libpq-dev \
  libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libcairo2 \
  libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info \
  apache2

echo ">> PostgreSQL..."
if [[ -z "${DB_PASSWORD:-}" ]]; then
  DB_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | head -c 24)
  echo "Generada DB_PASSWORD (guardar en .env): ${DB_PASSWORD}"
fi

${SUDO} -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 \
  || ${SUDO} -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';"
${SUDO} -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 \
  || ${SUDO} -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"
${SUDO} -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"

if [[ -f "${APP_DIR}/.env" ]]; then
  grep -q '^DATABASE_ENGINE=' "${APP_DIR}/.env" \
    && sed -i 's/^DATABASE_ENGINE=.*/DATABASE_ENGINE=postgres/' "${APP_DIR}/.env" \
    || echo "DATABASE_ENGINE=postgres" >> "${APP_DIR}/.env"
  grep -q '^DB_PASSWORD=' "${APP_DIR}/.env" \
    && sed -i "s/^DB_PASSWORD=.*/DB_PASSWORD=${DB_PASSWORD}/" "${APP_DIR}/.env" \
    || echo "DB_PASSWORD=${DB_PASSWORD}" >> "${APP_DIR}/.env"
fi

echo ">> Apache proxy..."
${SUDO} a2enmod proxy proxy_http headers 2>/dev/null || true

cat << EOF | ${SUDO} tee /etc/apache2/sites-available/fase2-rojo.conf > /dev/null
<VirtualHost *:80>
    ServerName 190.169.110.9
    ProxyPreserveHost On
    RequestHeader set X-Forwarded-Proto "http"
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/
    ErrorLog \${APACHE_LOG_DIR}/fase2-rojo-error.log
    CustomLog \${APACHE_LOG_DIR}/fase2-rojo-access.log combined
</VirtualHost>
EOF

${SUDO} a2dissite 000-default.conf 2>/dev/null || true
${SUDO} a2ensite fase2-rojo.conf
${SUDO} systemctl reload apache2

echo ">> Servicio systemd gunicorn (usuario cph)..."
cat << EOF | ${SUDO} tee /etc/systemd/system/fase2-rojo.service > /dev/null
[Unit]
Description=CPEH Fase II ROJO - Gunicorn
After=network.target postgresql.service

[Service]
User=cph
Group=cph
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/.venv/bin/gunicorn config.wsgi:application -c ${APP_DIR}/gunicorn.conf.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

${SUDO} systemctl daemon-reload
${SUDO} systemctl enable fase2-rojo.service
${SUDO} systemctl restart fase2-rojo.service

if [[ -d "${APP_DIR}" ]]; then
  # shellcheck disable=SC1091
  source "${APP_DIR}/.venv/bin/activate"
  cd "${APP_DIR}"
  python manage.py migrate --noinput
fi

echo "============================================"
echo "OK bootstrap-sudo"
echo "App:  http://190.169.110.9/api/health/"
echo "Admin: http://190.169.110.9/admin/ (crear superuser aparte)"
echo "Estado: sudo systemctl status fase2-rojo"
echo "============================================"
