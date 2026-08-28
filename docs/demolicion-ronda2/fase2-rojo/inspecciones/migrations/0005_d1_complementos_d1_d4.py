"""D1–D4: fusiona monitoreo+estudios en D1 con complementos explícitos."""
from django.db import migrations, models


REMAP_D_V2 = {
    "D1 — Inhabitabilidad + monitoreo": "D1 — Complementos requeridos",
    "D2 — Estudios complementarios": "D1 — Complementos requeridos",
    "D3 — Reparar / reconstruir": "D2 — Reparar / reconstruir",
    "D4 — Demoler": "D3 — Demoler",
    "D5 — Escombros / ya colapsado": "D4 — Escombros / ya colapsado",
}

REMAP_M = {
    "N/A (no es D3)": "N/A (no es D2)",
}


def forwards(apps, schema_editor):
    CasoRojo = apps.get_model("inspecciones", "CasoRojo")
    for old, new in REMAP_D_V2.items():
        for caso in CasoRojo.objects.filter(decision_D=old):
            caso.decision_D = new
            if new == "D1 — Complementos requeridos":
                if not caso.complementos_D:
                    caso.complementos_D = "REI"
                if not caso.complemento_detalle:
                    caso.complemento_detalle = (
                        "Complemento pendiente de detalle (caso migrado desde escala anterior)."
                    )
            caso.save(update_fields=["decision_D", "complementos_D", "complemento_detalle"])
    for old, new in REMAP_M.items():
        CasoRojo.objects.filter(magnitud_M=old).update(magnitud_M=new)


def backwards(apps, schema_editor):
    CasoRojo = apps.get_model("inspecciones", "CasoRojo")
    rev = {v: k for k, v in REMAP_D_V2.items()}
    for new, old in rev.items():
        CasoRojo.objects.filter(decision_D=new).update(decision_D=old)


class Migration(migrations.Migration):

    dependencies = [
        ("inspecciones", "0004_decision_d_escala_gravedad"),
    ]

    operations = [
        migrations.AddField(
            model_name="casorojo",
            name="complementos_D",
            field=models.CharField(
                blank=True,
                help_text="Si D1: códigos separados por coma (GEO, ENS, MOD, MON, INV, REI, ALE, OTR).",
                max_length=128,
                verbose_name="Complementos requeridos (D1)",
            ),
        ),
        migrations.AddField(
            model_name="casorojo",
            name="complemento_plazo",
            field=models.DateField(
                blank=True,
                null=True,
                verbose_name="Plazo / fecha objetivo complemento (D1)",
            ),
        ),
        migrations.AddField(
            model_name="casorojo",
            name="complemento_detalle",
            field=models.TextField(
                blank=True,
                verbose_name="Detalle del complemento — qué falta y entregable (D1)",
            ),
        ),
        migrations.RunPython(forwards, backwards),
    ]
