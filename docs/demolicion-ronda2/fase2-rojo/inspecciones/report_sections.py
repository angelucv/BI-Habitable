"""Secciones del informe PDF (mismos títulos numerados que el admin)."""
from __future__ import annotations

from django.db import models

from inspecciones.models import CasoRojo
from inspecciones.section_labels import CASE_FIELDSETS


def _format_value(field: models.Field, value) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(field, models.DateField):
        return value.strftime("%d/%m/%Y")
    if isinstance(field, models.DateTimeField):
        return value.strftime("%d/%m/%Y %H:%M")
    return str(value)


def build_report_sections(caso: CasoRojo) -> list[dict]:
    sections: list[dict] = []
    for title, opts in CASE_FIELDSETS:
        if title.startswith("12 —"):
            continue
        rows = []
        for fname in opts["fields"]:
            field = CasoRojo._meta.get_field(fname)
            rows.append(
                {
                    "label": str(field.verbose_name),
                    "value": _format_value(field, getattr(caso, fname)),
                }
            )
        sections.append({"title": title, "rows": rows})
    return sections
