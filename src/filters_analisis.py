"""Filtros de análisis (Elementos de la planilla)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import streamlit as st

from clean_catalog import USO_GRUPOS
from stats_asociacion import BANDAS_ANIO, banda_anio


@dataclass(frozen=True)
class FiltrosAnalisis:
    estados: tuple[str, ...]
    municipios: tuple[str, ...]
    usos: tuple[str, ...]
    bandas_anio: tuple[str, ...]


def _anios(df: pd.DataFrame) -> pd.Series:
    if "anio_construccion_n" in df.columns:
        return pd.to_numeric(df["anio_construccion_n"], errors="coerce")
    if "anio_construccion" in df.columns:
        return pd.to_numeric(df["anio_construccion"], errors="coerce")
    return pd.Series(np.nan, index=df.index)


def asegurar_banda_anio(df: pd.DataFrame) -> pd.DataFrame:
    """Siempre recalcula la escala por décadas (no reutiliza bandas viejas)."""
    out = df.copy()
    an = _anios(out)
    out["banda_anio"] = [banda_anio(x) for x in an]
    return out


def render_filtros_analisis(df: pd.DataFrame, *, titulo: str = "Filtros") -> FiltrosAnalisis:
    """Bloque de filtros (cascada estado → municipio)."""
    work = asegurar_banda_anio(df)
    st.markdown(f"##### {titulo}")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        est_opts = sorted(
            x
            for x in work["estado_n"].dropna().astype(str).unique().tolist()
            if x and x not in {"(SIN ESTADO)", "(sin estado)", "NAN"}
        )
        estados = st.multiselect("Estado", est_opts, default=[], key="fa_estado")

    df_m = work if not estados else work.loc[work["estado_n"].isin(estados)]
    with c2:
        mun_opts = sorted(
            x
            for x in df_m["municipio_n"].dropna().astype(str).unique().tolist()
            if x and x not in {"", "SIN EVALUAR", "Sin Evaluar", "CARACAS"}
        )
        municipios = st.multiselect("Municipio", mun_opts, default=[], key="fa_mun")

    with c3:
        presentes = set(work["uso_n"].dropna().astype(str).unique()) if "uso_n" in work.columns else set()
        uso_opts = [u for u in USO_GRUPOS if u in presentes] + sorted(presentes - set(USO_GRUPOS))
        usos = st.multiselect("Uso agrupado", uso_opts, default=[], key="fa_uso")

    with c4:
        bandas = st.multiselect(
            "Escala de años",
            list(BANDAS_ANIO),
            default=[],
            key="fa_banda",
            help="Décadas: 1950 o menos → 2021+",
        )

    return FiltrosAnalisis(
        estados=tuple(estados),
        municipios=tuple(municipios),
        usos=tuple(usos),
        bandas_anio=tuple(bandas),
    )


def aplicar_filtros_analisis(df: pd.DataFrame, f: FiltrosAnalisis) -> pd.DataFrame:
    out = asegurar_banda_anio(df)
    if f.estados:
        out = out.loc[out["estado_n"].isin(f.estados)]
    if f.municipios:
        out = out.loc[out["municipio_n"].isin(f.municipios)]
    if f.usos and "uso_n" in out.columns:
        out = out.loc[out["uso_n"].isin(f.usos)]
    if f.bandas_anio:
        out = out.loc[out["banda_anio"].isin(f.bandas_anio)]
    return out
