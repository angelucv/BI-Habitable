# -*- coding: utf-8 -*-
"""Carga inicial de informes PDF desde carpeta (ensayo demolición)."""
from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from inspecciones.import_informes_pdf import importar_carpeta_informes


class Command(BaseCommand):
    help = "Vincula PDFs de informes de demolición a casos ROJO (formato libre + cruce CSV)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--carpeta",
            type=str,
            default="",
            help="Carpeta con PDFs (ej. D:\\Edificios Demolicion)",
        )
        parser.add_argument(
            "--csv",
            type=str,
            default="",
            help="CSV cruce informes × Habitable (hab_id por archivo)",
        )
        parser.add_argument("--dry-run", action="store_true", help="Simular sin escribir")
        parser.add_argument(
            "--sobrescribir-campos",
            action="store_true",
            help="Sobrescribir campos visita 2 ya completados",
        )
        parser.add_argument(
            "--reemplazar-pdf",
            action="store_true",
            help="Reemplazar PDF si ya existe mismo nombre en el caso",
        )

    def handle(self, *args, **options):
        carpeta = options["carpeta"]
        if not carpeta:
            candidatos = [
                Path(r"D:\Edificios Demolicion"),
                Path("/home/cph/data/informes-demolicion"),
                Path(__file__).resolve().parents[4] / "informes-demolicion",
            ]
            for c in candidatos:
                if c.is_dir():
                    carpeta = str(c)
                    break

        csv_path = options["csv"]
        if not csv_path:
            candidatos_csv = [
                Path(__file__).resolve().parents[4] / "cruce-informes-demolicion-habitable-2026-08-20.csv",
                Path("/home/cph/data/cruce-informes-demolicion-habitable-2026-08-20.csv"),
            ]
            for c in candidatos_csv:
                if c.is_file():
                    csv_path = str(c)
                    break

        folder = Path(carpeta)
        if not folder.is_dir():
            raise CommandError(f"Carpeta no encontrada: {carpeta or '(sin --carpeta)'}")

        csv_file = Path(csv_path) if csv_path else None
        stats = importar_carpeta_informes(
            folder,
            csv_file,
            dry_run=options["dry_run"],
            sobrescribir_campos=options["sobrescribir_campos"],
            reemplazar_pdf=options["reemplazar_pdf"],
        )
        modo = "SIMULACIÓN" if options["dry_run"] else "CARGADO"
        self.stdout.write(
            self.style.SUCCESS(
                f"{modo} — PDFs={stats['pdfs_en_carpeta']} vinculados={stats['vinculados']} "
                f"enriquecidos={stats['casos_enriquecidos']} sin_caso={stats['sin_caso']} "
                f"sin_cruce={stats['sin_cruce']} dup={stats['omitidos_dup']} err={stats['errores']}"
            )
        )
