# Generated manually — informes PDF adjuntos
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("inspecciones", "0002_roles_catalogo_mapa"),
    ]

    operations = [
        migrations.CreateModel(
            name="InformePdfAdjunto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "archivo",
                    models.FileField(
                        help_text="Informe técnico original en PDF (cualquier formato / plantilla).",
                        upload_to="informes/%Y/%m/",
                        verbose_name="Archivo PDF",
                    ),
                ),
                ("titulo", models.CharField(blank=True, max_length=255, verbose_name="Título / referencia")),
                ("nombre_archivo_origen", models.CharField(blank=True, max_length=255, verbose_name="Nombre archivo origen")),
                ("tipo_informe", models.CharField(blank=True, max_length=128, verbose_name="Tipo de informe")),
                ("codigo_documento", models.CharField(blank=True, max_length=64, verbose_name="Código documento")),
                ("notas", models.TextField(blank=True, verbose_name="Notas")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "caso",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="informes_pdf",
                        to="inspecciones.casorojo",
                        verbose_name="Caso ROJO",
                    ),
                ),
                (
                    "subido_por",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="informes_pdf_subidos",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Informe PDF adjunto",
                "verbose_name_plural": "Informes PDF adjuntos",
                "ordering": ["-created_at"],
            },
        ),
    ]
