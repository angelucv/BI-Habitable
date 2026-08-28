#!/usr/bin/env python3
"""Genera localmente el PDF de la guía de usuario (borrador para revisión)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "fase2-rojo"
OUT = Path(__file__).resolve().parent / "Guia-usuario-Fase-II-ROJO-BORRADOR.pdf"

sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("SECRET_KEY", "generar-guia-local")
os.environ.setdefault("DEBUG", "1")

import django

django.setup()

from inspecciones.guia_pdf import render_guia_usuario_pdf  # noqa: E402

if __name__ == "__main__":
    pdf = render_guia_usuario_pdf(borrador=True)
    OUT.write_bytes(pdf)
    print(f"OK — {OUT} ({len(pdf):,} bytes)")
