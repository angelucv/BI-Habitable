"""Navegación: Inicio · Análisis dimensional · Carga."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NavItem:
    id: str
    label: str
    blurb: str = ""


@dataclass(frozen=True)
class NavSection:
    id: str
    label: str
    blurb: str
    items: tuple[NavItem, ...]


HOME_ID = "home"

NAV_SECTIONS: tuple[NavSection, ...] = (
    NavSection(
        id="analisis_dimensional",
        label="Análisis dimensional",
        blurb="Año, pisos, uso, material y flujo ANIH.",
        items=(
            NavItem(
                "dim_anio",
                "Año de construcción",
                "Quinquenios vs pérdida total, uso y ubicación.",
            ),
            NavItem(
                "dim_pisos",
                "Número de pisos",
                "Bandas de altura (resonancia) vs pérdida total · OR vs baja.",
            ),
            NavItem(
                "dim_uso",
                "Uso agrupado",
                "Chi² / Cramer / OR vs Casa.",
            ),
            NavItem(
                "dim_material",
                "Material agrupado",
                "Chi² / Cramer / OR vs Concreto.",
            ),
            NavItem(
                "dim_elementos",
                "Flujo de decisión",
                "Embudo ANIH: salidas tempranas y pasos de daño.",
            ),
        ),
    ),
    NavSection(
        id="pdna",
        label="PDNA",
        blurb="Matriz tipología × semáforo y costos estimados (vivienda + contenidos).",
        items=(
            NavItem(
                "pdna_matriz",
                "Matriz y costos",
                "Afectación por tipología · daño vivienda y contenidos · parámetros editables.",
            ),
            NavItem(
                "pdna_guia",
                "Guía del modelo",
                "Explicación didáctica: qué calcula el modelo y qué parámetros calibrar.",
            ),
        ),
    ),
    NavSection(
        id="explorar",
        label="Explorar / cruces",
        blurb="Cruces libres con Perspective: el usuario arma tablas y gráficos.",
        items=(
            NavItem(
                "explorar_perspective",
                "Perspective (cruces libres)",
                "Año, pisos, uso agrupado y material agrupado · pivotes y gráficos.",
            ),
        ),
    ),
    NavSection(
        id="depuracion",
        label="Depuración de datos",
        blurb="Auditoría interna: multiplicidad en el mismo lugar y conflictos de semáforo.",
        items=(
            NavItem(
                "dep_auditoria",
                "Auditoría de multiplicidad",
                "Mismo GPS, nombre o dirección; conflictos de etiqueta.",
            ),
        ),
    ),
    NavSection(
        id="carga",
        label="Cargar información",
        blurb="Subir y procesar el CSV Habitable.",
        items=(
            NavItem("carga_datos", "Cargar CSV", "Ingesta del corte de inspecciones."),
        ),
    ),
)


def resolve_nav(item_id: str) -> tuple[NavSection | None, NavItem | None]:
    if item_id == HOME_ID:
        return None, None
    for sec in NAV_SECTIONS:
        for it in sec.items:
            if it.id == item_id:
                return sec, it
    return None, None
