# Generated manually — extensiones Fase II v0.2
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("inspecciones", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="casorojo",
            name="lat",
            field=models.DecimalField(
                blank=True, db_index=True, decimal_places=7, max_digits=10, null=True, verbose_name="Latitud"
            ),
        ),
        migrations.AddField(
            model_name="casorojo",
            name="lng",
            field=models.DecimalField(
                blank=True, db_index=True, decimal_places=7, max_digits=10, null=True, verbose_name="Longitud"
            ),
        ),
        migrations.AddField(
            model_name="casorojo",
            name="inspector_asignado",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="casos_inspeccion",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Inspector asignado",
            ),
        ),
        migrations.AddField(
            model_name="casorojo",
            name="revisor_asignado",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="casos_revision",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Revisor asignado",
            ),
        ),
        migrations.CreateModel(
            name="Procedimiento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo", models.CharField(max_length=16, unique=True, verbose_name="Código")),
                (
                    "categoria",
                    models.CharField(
                        choices=[("VIG", "Vigas"), ("COL", "Columnas"), ("MAM", "Mampostería"), ("OTRO", "Otro")],
                        max_length=8,
                    ),
                ),
                ("titulo", models.CharField(max_length=255)),
                ("descripcion", models.TextField(blank=True)),
                ("activo", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Procedimiento",
                "verbose_name_plural": "Catálogo de procedimientos",
                "ordering": ["categoria", "codigo"],
            },
        ),
        migrations.CreateModel(
            name="HistorialEstado",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("estado_anterior", models.CharField(blank=True, max_length=32)),
                ("estado_nuevo", models.CharField(max_length=32)),
                ("nota", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "caso",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="historial_estados",
                        to="inspecciones.casorojo",
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Historial de estado",
                "verbose_name_plural": "Historial de estados",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="EvidenciaFoto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("imagen", models.ImageField(upload_to="evidencias/%Y/%m/", verbose_name="Imagen")),
                ("descripcion", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "caso",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fotos",
                        to="inspecciones.casorojo",
                    ),
                ),
                (
                    "subido_por",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Foto de evidencia",
                "verbose_name_plural": "Fotos de evidencia",
                "ordering": ["-created_at"],
            },
        ),
    ]
