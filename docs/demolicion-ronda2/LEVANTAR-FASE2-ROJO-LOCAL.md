# Levantar Fase II ROJO en equipo local

Guía rápida para **laptop** u otro equipo tras sync Drive + `git pull`.

## Qué es

App **Django** de seguimiento de casos ROJO (2.ª ronda demolición / verificación). Código en `docs/demolicion-ronda2/fase2-rojo/`.

| Entorno | URL |
|---------|-----|
| **Producción** | http://190.169.110.9/admin/ |
| Streamlit BI Habitable | https://bi-habitable.onrender.com |
| Repo | https://github.com/angelucv/BI-Habitable (`main`) |

## 1. Sync desde Drive (laptop)

1. Esperar icono Google Drive sin pendientes.
2. `robocopy` **espejo → local** (no usar carpeta `C-Users-Angel-Projects`):
   - `MisProyectos-Espejo\instrucciones-cursor` → `Projects\instrucciones-cursor`
   - `MisProyectos-Espejo\D-CPEH` → `Projects\clients\comision-presidencial-habitabilidad`
3. Leer aviso **`AVISO-PC-A-LAPTOP-HABITABLE-FASE2-ROJO-2026-08-28.md`** en `instrucciones-cursor`.

## 2. Git

```powershell
cd Projects\clients\comision-presidencial-habitabilidad\bi-habitable
git pull origin main
```

Verificar que `main` incluye el commit del sprint Fase II (post `6398488`: guía PDF, portada, login).

## 3. Dependencias (desarrollo local)

**Recomendado:** Linux o WSL (WeasyPrint para PDF es más simple que Windows nativo).

```bash
cd docs/demolicion-ronda2/fase2-rojo
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Copiar `.env.example` → `.env` y configurar `DATABASE_URL` o variables PostgreSQL locales.

```bash
python manage.py migrate
python manage.py crear_roles_ejemplo   # usuarios demo si aplica
python manage.py runserver 0.0.0.0:8000
```

Admin local: http://127.0.0.1:8000/admin/

## 4. Cargar datos (opcional en local)

Requiere Excel ranking y carpeta PDF del cruce (en `docs/demolicion-ronda2/`):

```bash
python manage.py importar_ranking --todas-hojas --solo-gps
python manage.py cargar_informes_demolicion --reemplazar-pdf --sobrescribir-campos
python manage.py cargar_franco_mar   # ejemplo vaciado
```

## 5. Guía PDF usuario

- Ruta en sistema: `/guia/usuario.pdf` (requiere login staff).
- Generar borrador: `python manage.py generar_guia_usuario_pdf`
- Borrador local: `docs/demolicion-ronda2/Guia-usuario-Fase-II-ROJO-BORRADOR.pdf`
- Aprobación gerencial: `GUIA_USUARIO_PDF_APROBADA=1` en `.env` del servidor.

## 6. Documentación clave

| Documento | Contenido |
|-----------|-----------|
| `MANUAL-EJECUTIVO-SISTEMA-FASE2-ROJO.md` | Manual técnico-operativo |
| `README-entregables-demolicion-ronda2.md` | Paquete Word/Excel 2.ª ronda |
| `server-bootstrap/README.md` | Deploy en 190.169.110.9 |
| `templates/includes/cpeh_guia_desarrolladores.html` | Guía dev en admin (§10) |

## 7. Deploy a producción

Desde PC con SSH al servidor:

```powershell
python docs/demolicion-ronda2/server-bootstrap/deploy_sprint_operativo.py
# o scripts puntuales: deploy_guia_pdf.py, deploy_fix_portada.py
```

Credenciales servidor: `server-bootstrap/CREDENCIALES-ADMIN-SERVIDOR-FASE2.md` (no versionado).

## Notas

- **No confundir** con Habitable 1×10 (`habitable.onrender.com`) ni CPEH web (`cpeh-web.onrender.com`).
- En prod hay ~9k casos tras ranking nacional; 29 PDFs del cruce enriquecidos; 7 sin `hab_id`.
- systemd en servidor pendiente de `sudo`; Gunicorn vía `run/ensure-running.sh`.
