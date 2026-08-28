"""Generación PDF — Guía de usuario Fase II ROJO."""
from __future__ import annotations

from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML


def render_guia_usuario_pdf(*, request=None, borrador: bool = True) -> bytes:
    """Renderiza la guía didáctica a bytes PDF."""
    ctx = {
        "generado": timezone.localtime(timezone.now()),
        "borrador": borrador,
        "version_guia": "1.0-borrador" if borrador else "1.0",
    }
    if request is not None:
        html = render_to_string("inspecciones/guia_usuario_pdf.html", ctx, request=request)
        base_url = request.build_absolute_uri("/")
    else:
        html = render_to_string("inspecciones/guia_usuario_pdf.html", ctx)
        base_url = "http://127.0.0.1/"
    return HTML(string=html, base_url=base_url).write_pdf()
