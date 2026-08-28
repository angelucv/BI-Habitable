# Bootstrap servidor — Fase II ROJO

Scripts para desplegar Django en `190.169.110.9` (usuario `cph`).

| Archivo | Uso |
|---------|-----|
| `bootstrap-user.sh` | Sin sudo: venv, Django, Gunicorn |
| `bootstrap-sudo.sh` | Con sudo: PostgreSQL, Apache, systemd |
| `CREDENCIALES-ADMIN-SERVIDOR-FASE2.md` | **Contraseña BD, SECRET_KEY, URLs** (solo admins repo) |
| `deploy_models.py` | Sube modelos inspecciones + migrate + Franco Mar |
| `deploy_ui.py` | Jazzmin + WhiteNoise + collectstatic (mejora visual) |

**Credenciales PostgreSQL:** ver `CREDENCIALES-ADMIN-SERVIDOR-FASE2.md`.
