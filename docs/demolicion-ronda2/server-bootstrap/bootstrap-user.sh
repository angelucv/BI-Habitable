#!/usr/bin/env bash
# Instalación Fase II ROJO — sin sudo (usuario cph)
set -euo pipefail

APP_DIR="${HOME}/apps/fase2-rojo"
mkdir -p "${APP_DIR}"
cd "${APP_DIR}"

# Limpiar venv roto de intentos previos (python3-venv no instalado)
if [[ -d .venv && ! -f .venv/bin/activate ]]; then
  rm -rf .venv
fi

if ! python3 -m pip --version >/dev/null 2>&1; then
  echo ">> Instalando pip en usuario (sin sudo)..."
  python3 - << 'PYPIP'
import urllib.request
urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py", "/tmp/get-pip.py")
print("get-pip descargado")
PYPIP
  python3 /tmp/get-pip.py --user --break-system-packages
  export PATH="${HOME}/.local/bin:${PATH}"
fi

if [[ ! -d .venv ]]; then
  python3 -m pip install --user --upgrade pip virtualenv --break-system-packages -q
  export PATH="${HOME}/.local/bin:${PATH}"
  python3 -m virtualenv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip -q
pip install -q \
  django djangorestframework django-cors-headers psycopg2-binary \
  gunicorn pillow openpyxl python-dotenv weasyprint

if [[ ! -f manage.py ]]; then
  django-admin startproject config .
fi

if [[ ! -f inspecciones/apps.py ]]; then
  rm -rf inspecciones
  python manage.py startapp inspecciones
fi

cat > requirements.txt << 'EOF'
django>=5.0,<5.2
djangorestframework>=3.15.0
django-cors-headers>=4.3.0
psycopg2-binary>=2.9.9
gunicorn>=22.0.0
Pillow>=10.3.0
openpyxl>=3.1.0
python-dotenv>=1.0.1
weasyprint>=62.0
EOF

if [[ ! -f .env ]]; then
  SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
  cat > .env << EOF
DEBUG=1
SECRET_KEY=${SECRET_KEY}
ALLOWED_HOSTS=190.169.110.9,localhost,127.0.0.1
DATABASE_ENGINE=sqlite
DB_NAME=fase2_rojo
DB_USER=fase2_app
DB_PASSWORD=
DB_HOST=127.0.0.1
DB_PORT=5432
EOF
  chmod 600 .env
fi

python3 << 'PYEOF'
from pathlib import Path
import re

p = Path("config/settings.py")
text = p.read_text(encoding="utf-8")

if "load_dotenv" not in text:
    text = text.replace(
        "from pathlib import Path",
        "from pathlib import Path\nimport os\nfrom dotenv import load_dotenv\n\nload_dotenv(Path(__file__).resolve().parent.parent / \".env\")",
    )

if "'inspecciones'" not in text and '"inspecciones"' not in text:
    text = text.replace(
        "INSTALLED_APPS = [",
        "INSTALLED_APPS = [\n    \"inspecciones\",\n    \"rest_framework\",\n    \"corsheaders\",",
    )
    text = text.replace(
        "'django.middleware.security.SecurityMiddleware',",
        "'django.middleware.security.SecurityMiddleware',\n    'corsheaders.middleware.CorsMiddleware',",
    )
elif "'rest_framework'" not in text:
    text = text.replace(
        "INSTALLED_APPS = [",
        "INSTALLED_APPS = [\n    \"rest_framework\",\n    \"corsheaders\",",
    )

if "ALLOWED_HOSTS = []" in text:
    text = text.replace(
        "ALLOWED_HOSTS = []",
        "ALLOWED_HOSTS = os.environ.get(\"ALLOWED_HOSTS\", \"localhost\").split(\",\")",
    )

text = re.sub(
    r"SECRET_KEY = .*",
    "SECRET_KEY = os.environ.get(\"SECRET_KEY\", \"dev-insecure-change-me\")",
    text,
    count=1,
)

old_db = """DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}"""

new_db = """if os.environ.get("DATABASE_ENGINE", "sqlite") == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", "fase2_rojo"),
            "USER": os.environ.get("DB_USER", "fase2_app"),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
            "PORT": os.environ.get("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }"""

if old_db in text:
    text = text.replace(old_db, new_db)

p.write_text(text, encoding="utf-8")
print("settings.py patched")
PYEOF

python manage.py migrate --noinput
python manage.py check

mkdir -p run logs static media

cat > gunicorn.conf.py << 'EOF'
bind = "0.0.0.0:8000"
workers = 2
timeout = 120
accesslog = "logs/gunicorn-access.log"
errorlog = "logs/gunicorn-error.log"
capture_output = True
EOF

cat > run/start-gunicorn.sh << 'EOF'
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
mkdir -p logs
exec gunicorn config.wsgi:application -c gunicorn.conf.py
EOF
chmod +x run/start-gunicorn.sh

cat > run/start-dev.sh << 'EOF'
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
python manage.py runserver 0.0.0.0:8000
EOF
chmod +x run/start-dev.sh

cat > inspecciones/views.py << 'EOF'
from django.http import JsonResponse


def health(request):
    return JsonResponse(
        {
            "status": "ok",
            "proyecto": "CPEH Fase II — Seguimiento ROJO",
            "version": "0.1.0-bootstrap",
        }
    )
EOF

python3 << 'PYEOF'
from pathlib import Path

urls = Path("config/urls.py")
text = urls.read_text(encoding="utf-8")
if "health" not in text:
    text = text.replace(
        "from django.contrib import admin",
        "from django.contrib import admin\nfrom inspecciones.views import health",
    )
    text = text.replace(
        "urlpatterns = [",
        "urlpatterns = [\n    path(\"api/health/\", health),",
    )
    urls.write_text(text, encoding="utf-8")
PYEOF

python manage.py check

echo "============================================"
echo "OK bootstrap-user en ${APP_DIR}"
echo "Probar: cd ${APP_DIR} && ./run/start-dev.sh"
echo "Health: http://127.0.0.1:8000/api/health/"
echo "============================================"
