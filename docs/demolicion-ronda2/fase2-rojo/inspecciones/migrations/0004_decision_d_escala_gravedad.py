"""Remapea D1–D5 y M a escala ascendente de gravedad."""
from django.db import migrations


REMAP_D = {
    "D1 — Demoler": "D4 — Demoler",
    "D2 — Reparar / reconstruir": "D3 — Reparar / reconstruir",
    "D3 — Estudios complementarios": "D2 — Estudios complementarios",
    "D4 — Escombros / ya colapsado": "D5 — Escombros / ya colapsado",
    "D5 — Inhabitabilidad + monitoreo": "D1 — Inhabitabilidad + monitoreo",
}

REMAP_M = {
    "N/A (no es D2)": "N/A (no es D3)",
    "M1 — Reparación pequeña / local": "M1 — Reparación local (menor intervención)",
}


def forwards(apps, schema_editor):
    CasoRojo = apps.get_model("inspecciones", "CasoRojo")
    for old, new in REMAP_D.items():
        CasoRojo.objects.filter(decision_D=old).update(decision_D=new)
    for old, new in REMAP_M.items():
        CasoRojo.objects.filter(magnitud_M=old).update(magnitud_M=new)


def backwards(apps, schema_editor):
    CasoRojo = apps.get_model("inspecciones", "CasoRojo")
    rev_d = {v: k for k, v in REMAP_D.items()}
    rev_m = {v: k for k, v in REMAP_M.items()}
    for new, old in rev_d.items():
        CasoRojo.objects.filter(decision_D=new).update(decision_D=old)
    for new, old in rev_m.items():
        CasoRojo.objects.filter(magnitud_M=new).update(magnitud_M=old)


class Migration(migrations.Migration):

    dependencies = [
        ("inspecciones", "0003_informe_pdf_adjunto"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
