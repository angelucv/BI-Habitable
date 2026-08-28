# -*- coding: utf-8 -*-
"""Genera el PDF de la guía de usuario en disco."""
from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand

from inspecciones.guia_pdf import render_guia_usuario_pdf


class Command(BaseCommand):
    help = "Genera PDF de la guía didáctica de usuario Fase II ROJO"

    def add_arguments(self, parser):
        parser.add_argument(
            "--salida",
            type=str,
            default="",
            help="Ruta del PDF de salida",
        )
        parser.add_argument(
            "--aprobada",
            action="store_true",
            help="Generar versión sin marca de agua (aprobada)",
        )

    def handle(self, *args, **options):
        borrador = not options["aprobada"]
        pdf = render_guia_usuario_pdf(borrador=borrador)
        if options["salida"]:
            out = Path(options["salida"])
        else:
            nombre = "guia-usuario-fase2-rojo-borrador.pdf" if borrador else "guia-usuario-fase2-rojo.pdf"
            out = Path(__file__).resolve().parents[4] / nombre
        out.write_bytes(pdf)
        self.stdout.write(self.style.SUCCESS(f"OK — {out} ({len(pdf):,} bytes)"))
