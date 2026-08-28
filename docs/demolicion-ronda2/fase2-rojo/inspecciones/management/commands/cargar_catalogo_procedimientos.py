# -*- coding: utf-8 -*-
"""Carga catálogo inicial de procedimientos VIG / COL / MAM."""
from __future__ import annotations

from django.core.management.base import BaseCommand

from inspecciones.catalogo_procedimientos import PROCEDIMIENTOS_INICIALES
from inspecciones.models import Procedimiento


class Command(BaseCommand):
    help = "Carga o actualiza el catálogo de procedimientos de reparación"

    def handle(self, *args, **options):
        creados = actualizados = 0
        for item in PROCEDIMIENTOS_INICIALES:
            _, created = Procedimiento.objects.update_or_create(
                codigo=item["codigo"],
                defaults={
                    "categoria": item["categoria"],
                    "titulo": item["titulo"],
                    "descripcion": item["descripcion"],
                    "activo": True,
                },
            )
            if created:
                creados += 1
            else:
                actualizados += 1
        self.stdout.write(
            self.style.SUCCESS(f"Catálogo: {creados} creados, {actualizados} actualizados.")
        )
