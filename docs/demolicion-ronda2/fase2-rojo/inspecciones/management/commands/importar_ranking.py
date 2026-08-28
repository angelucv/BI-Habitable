# -*- coding: utf-8 -*-
"""Importa casos ROJO masivamente desde Excel Ranking Habitable."""
from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from inspecciones.import_ranking import HOJAS_VALIDAS, importar_desde_excel


class Command(BaseCommand):
    help = "Importa o actualiza casos ROJO desde Excel Ranking (precarga secc. 1–2)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--excel",
            type=str,
            default="",
            help="Ruta al Excel cruce-informes v2 (Ranking_ROJO_*)",
        )
        parser.add_argument(
            "--hoja",
            type=str,
            default="Ranking_ROJO_LaGuaira",
            choices=HOJAS_VALIDAS,
            help="Hoja a importar",
        )
        parser.add_argument("--limit", type=int, default=None, help="Máximo de filas a procesar")
        parser.add_argument("--min-score", type=int, default=None, help="Score mínimo (0–100)")
        parser.add_argument(
            "--banda",
            action="append",
            default=[],
            help="Filtrar banda (ej. Muy alta). Repetir para varias.",
        )
        parser.add_argument("--solo-gps", action="store_true", help="Solo filas con lat/lng")
        parser.add_argument("--dry-run", action="store_true", help="Simular sin escribir BD")
        parser.add_argument(
            "--todas-hojas",
            action="store_true",
            help="Importar las tres hojas Ranking (La Guaira, nacional, Top200)",
        )
        parser.add_argument(
            "--sobrescribir-visitados",
            action="store_true",
            help="Actualizar también casos ya en visita/revisión",
        )

    def handle(self, *args, **options):
        excel = options["excel"]
        if not excel:
            candidatos = [
                Path(__file__).resolve().parents[4] / "cruce-informes-demolicion-habitable-2026-08-20-v2.xlsx",
                Path("/home/cph/data/cruce-informes-demolicion-habitable-2026-08-20-v2.xlsx"),
            ]
            for c in candidatos:
                if c.is_file():
                    excel = str(c)
                    break
        path = Path(excel)
        if not path.is_file():
            raise CommandError(f"Excel no encontrado: {excel or '(sin --excel)'}")

        bandas = set(options["banda"]) if options["banda"] else None
        hojas = list(HOJAS_VALIDAS) if options["todas_hojas"] else [options["hoja"]]
        totales = {"leidas": 0, "creadas": 0, "actualizadas": 0, "omitidas": 0, "errores": 0}

        for hoja in hojas:
            stats = importar_desde_excel(
                path,
                hoja=hoja,
                limit=options["limit"],
                min_score=options["min_score"],
                bandas=bandas,
                solo_con_gps=options["solo_gps"],
                dry_run=options["dry_run"],
                preservar_visitados=not options["sobrescribir_visitados"],
            )
            for k in totales:
                totales[k] += stats[k]
            self.stdout.write(f"  {hoja}: +{stats['creadas']} creadas, +{stats['actualizadas']} act.")

        modo = "SIMULACIÓN" if options["dry_run"] else "IMPORTADO"
        self.stdout.write(
            self.style.SUCCESS(
                f"{modo} — leídas={totales['leidas']} creadas={totales['creadas']} "
                f"actualizadas={totales['actualizadas']} omitidas={totales['omitidas']} "
                f"errores={totales['errores']}"
            )
        )
