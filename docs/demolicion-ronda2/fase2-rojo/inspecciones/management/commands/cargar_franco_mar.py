# -*- coding: utf-8 -*-
"""Carga caso ejemplo Franco Mar (ID 171818) desde plantilla Excel."""
from __future__ import annotations

from datetime import date

from django.core.management.base import BaseCommand

from inspecciones import choices as ch
from inspecciones.models import CasoRojo


class Command(BaseCommand):
    help = "Carga o actualiza el caso ejemplo Franco Mar (hab_id 171818)"

    def handle(self, *args, **options):
        data = {
            "hab_id": 171818,
            "certificado": "73420200720261338",
            "nombre_hab": "Edif. Francomar",
            "etiqueta_f1": "ROJO",
            "fecha_f1": date(2026, 7, 20),
            "inspector_f1": "Maria Mercedes Nieves Duarte",
            "direccion_hab": "Calle Principal Boulevard Tanaguarenas. Caraballeda. La Guaira.",
            "muni_parr": "Vargas / Caraballeda",
            "pisos_f1": "12 / 1",
            "riesgos_f1": "Externo C / Severo A",
            "colapso_f1": "C",
            "piso_crit_f1": "Planta baja, piso 1, 2, 3, 4",
            "acciones_f1": "Acordonar",
            "obs_f1": "Edificio a punto de colapso, se recomienda Desalojar",
            "gps_hab": "10.6123543, -66.8318071",
            "lat": "10.6123543",
            "lng": "-66.8318071",
            "score": 51,
            "banda": "Media",
            "puestos": "La Guaira ~115 / Nacional ~264",
            "score_detalle": (
                "riesgo_externo+20; ext_colapso+15; acordonar+2; altura_10++6; "
                "piso_critico+3; sev_elementos+5"
            ),
            "prob_rel": "Media — verificar; puede ser ROJO por riesgo localizado",
            "val_edificio": ch.SiNoParcial.SI,
            "val_etiqueta": ch.SiNoInsuf.SI,
            "val_geometria": ch.SiNoParcial.PARCIAL,
            "val_ranking": ch.SiNoParcial.SI,
            "correcciones": "Sótanos 1→2; precisar GPS y dirección de control de la visita",
            "nombre_conf": "Edificio Franco Mar",
            "fecha_v2": date(2026, 8, 11),
            "gps_v2": "10.489497, -66.899001",
            "evaluadores_v2": "Ing. Luis Burgos; Ing. José García",
            "supervisor_v2": "Ing. Aura Quintero",
            "uso": "Vivienda edificio",
            "pisos_conf": "12",
            "sotanos_conf": "2",
            "sistema": ch.SistemaEstructural.PORTICOS,
            "ocupacion": ch.Ocupacion.DESALOJADO,
            "peligro_aledanos": ch.PeligroAledanos.SI,
            "piso_crit_v2": "Nivel 1 / PB transición",
            "pct_columnas": ch.PctColumnas.GT50,
            "inclinacion": ch.Inclinacion.SI_CUAL,
            "dano_vigas": ch.NivelABC.C,
            "riesgo_fachada": ch.NivelABC.C,
            "analisis_libre": (
                "Piso crítico en Nivel 1 con >50% columnas graves; pérdida de verticalidad; "
                "daño en vigas en varios niveles. Ranking Media (51) no refleja la gravedad "
                "vista en sitio. Reparación en sitio no viable con seguridad."
            ),
            "col_mec": "Compresión / aplastamiento núcleo",
            "col_nivel": ch.NivelABC.C,
            "col_evidencia": "Nivel 1 >50% columnas; grietas >10 cm; núcleo >50% perdido — FOTOS 4-7",
            "vig_mec": "Corte / tensión diagonal",
            "vig_nivel": ch.NivelABC.C,
            "vig_evidencia": "Grietas 45° hasta ~5 niveles — FOTO 8",
            "mur_mec": "Compresión por reducción entrepiso",
            "mur_nivel": ch.NivelABC.C,
            "mam_mec": "Compresión / fuera de plano en cerramientos",
            "mam_nivel": ch.NivelABC.C,
            "mam_diag": "Tabiquería comprimida e inclinada PB — FOTOS 2, 10",
            "escaleras": "Fisuras arranque losa escalera piso 1 — FOTO 9",
            "preexistentes": "No reportados como determinantes vs daño sísmico 24/06/2026",
            "proc_codigos": "Condición crítica COL — fuera de alcance; demolición estructural",
            "repar_viable": ch.SiNoInsuf.NO,
            "proc_notas": "No aplican VIG/COL/MAM de reparación; D3 demolición controlada",
            "estado_2da": ch.Estado2daRonda.REVISADO,
            "decision_D": ch.DecisionD.D3,
            "magnitud_M": ch.MagnitudM.NA,
            "prioridad": ch.PrioridadOperativa.INMEDIATA,
            "medidas": "Exclusión total; acordonar; no ingreso; monitoreo de vecinos",
            "justificacion": (
                "Se recomienda demolición controlada por falla masiva en piso crítico, "
                "pérdida de verticalidad y peligro a colindantes."
            ),
            "n_fotos": "Según informe detallado DGPS (registro fotográfico)",
            "firmas": "Elaboró: equipo visita 11/08 · Supervisión: Aura Quintero",
            "resumen_ejecutivo": (
                "Franco Mar (Caraballeda). Fase 1 ROJO 20/07/2026, score 51 (Media, ~puesto 115 "
                "La Guaira). Visita 11/08/2026: 12 pisos + 2 sótanos, piso crítico Nivel 1, "
                ">50% columnas graves, pérdida de verticalidad. Validación: ROJO confirmado; "
                "corrección sótanos y GPS. Decisión D3 demoler, prioridad inmediata."
            ),
        }
        obj, created = CasoRojo.objects.update_or_create(hab_id=171818, defaults=data)
        verb = "Creado" if created else "Actualizado"
        self.stdout.write(self.style.SUCCESS(f"{verb}: {obj}"))
