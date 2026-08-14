"""Filtros globales en cascada (estado → municipio) + uso limpio."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import streamlit as st

from clean_catalog import USO_GRUPOS
from process_habitable import ETIQUETAS, etiqueta_display


@dataclass(frozen=True)
class FiltrosGlobales:
    estados: tuple[str, ...]
    municipios: tuple[str, ...]
    usos: tuple[str, ...]
    anio_min: int | None
    anio_max: int | None
    solo_geo_valida: bool
    solo_semaforo: tuple[str, ...]


def _anio_series(df: pd.DataFrame) -> pd.Series:
    if "anio_construccion_n" in df.columns:
        return pd.to_numeric(df["anio_construccion_n"], errors="coerce")
    if "anio_construccion" in df.columns:
        return pd.to_numeric(df["anio_construccion"], errors="coerce")
    return pd.Series(np.nan, index=df.index)


def render_filtros_globales(df: pd.DataFrame) -> FiltrosGlobales:
    """Selectores en cascada; Uso alimentado solo por supercategorías."""
    st.sidebar.markdown("### Filtros del corte")

    estados_opts = sorted(
        x
        for x in df["estado_n"].dropna().astype(str).unique().tolist()
        if x and x not in {"(SIN ESTADO)", "(sin estado)"}
    )
    estados = st.sidebar.multiselect("Estado", estados_opts, default=[], key="fg_estado")

    df_m = df if not estados else df.loc[df["estado_n"].isin(estados)]
    mun_opts = sorted(
        x
        for x in df_m["municipio_n"].dropna().astype(str).unique().tolist()
        if x and x not in {"", "SIN EVALUAR", "Sin Evaluar", "CARACAS"}
    )
    municipios = st.sidebar.multiselect("Municipio", mun_opts, default=[], key="fg_mun")

    # Solo catálogo limpio (orden canónico + residuales presentes)
    presentes = set(df["uso_n"].dropna().astype(str).unique().tolist()) if "uso_n" in df.columns else set()
    uso_opts = [u for u in USO_GRUPOS if u in presentes] + sorted(presentes - set(USO_GRUPOS))
    usos = st.sidebar.multiselect("Uso de la edificación", uso_opts, default=[], key="fg_uso")

    anios = _anio_series(df).dropna()
    anio_min = anio_max = None
    if not anios.empty:
        lo, hi = int(anios.min()), int(anios.max())
        lo, hi = max(1900, lo), min(2030, hi)
        if lo < hi:
            rango = st.sidebar.slider(
                "Año de construcción",
                min_value=lo,
                max_value=hi,
                value=(lo, hi),
                key="fg_anio",
            )
            anio_min, anio_max = int(rango[0]), int(rango[1])

    sem = st.sidebar.multiselect(
        "Semáforo / acceso",
        list(ETIQUETAS),
        default=[],
        format_func=etiqueta_display,
        key="fg_sem",
        help="Verde/Amarillo/Rojo = etiquetas ANIH V.8. Pérdida total = extensión Habitable (colapso extremo).",
    )
    solo_geo = st.sidebar.checkbox(
        "Solo GPS válido (Venezuela)",
        value=True,
        key="fg_geo",
        help="Excluye nulos y coordenadas fuera del polígono operativo de VE.",
    )

    return FiltrosGlobales(
        estados=tuple(estados),
        municipios=tuple(municipios),
        usos=tuple(usos),
        anio_min=anio_min,
        anio_max=anio_max,
        solo_geo_valida=solo_geo,
        solo_semaforo=tuple(sem),
    )


def aplicar_filtros(df: pd.DataFrame, f: FiltrosGlobales) -> pd.DataFrame:
    out = df
    if f.estados:
        out = out.loc[out["estado_n"].isin(f.estados)]
    if f.municipios:
        out = out.loc[out["municipio_n"].isin(f.municipios)]
    if f.usos:
        out = out.loc[out["uso_n"].isin(f.usos)]
    if f.solo_semaforo:
        out = out.loc[out["etiqueta_n"].isin(f.solo_semaforo)]
    if f.solo_geo_valida:
        col = "geo_valida" if "geo_valida" in out.columns else "con_gps"
        if col in out.columns:
            out = out.loc[out[col]]
    if f.anio_min is not None and f.anio_max is not None:
        an = _anio_series(out)
        mask = an.isna() | ((an >= f.anio_min) & (an <= f.anio_max))
        out = out.loc[mask]
    return out
