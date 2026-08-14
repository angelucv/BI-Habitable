"""Auditoría fuzzy: posibles duplicados y conflictos de semáforo."""

from __future__ import annotations

from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd
from rapidfuzz import fuzz


def _celda_geo(lat: float, lng: float, *, dec: int = 4) -> str | None:
    if lat != lat or lng != lng:
        return None
    return f"{round(float(lat), dec):.{dec}f}|{round(float(lng), dec):.{dec}f}"


def detectar_conflictos_semaforo(
    df: pd.DataFrame,
    *,
    umbral: float = 85.0,
    decimales_geo: int = 4,
    max_por_celda: int = 40,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Empareja edificaciones por vecindad GPS + similitud de nombre.

    Returns
    -------
    posibles_duplicados
        Pares con similitud ≥ umbral (misma celda geo).
    alerta_critica
        Subconjunto donde las etiquetas de semáforo discrepan.
    """
    cols_need = {"lat", "lng", "etiqueta_n"}
    if not cols_need.issubset(df.columns):
        vacio = pd.DataFrame()
        return vacio, vacio

    work = df.copy()
    if "nombre_edificacion" not in work.columns:
        work["nombre_edificacion"] = ""
    work["nombre_edificacion"] = work["nombre_edificacion"].fillna("").astype(str).str.strip()
    work = work.loc[work["nombre_edificacion"].str.len() >= 4].copy()
    work = work.loc[work["lat"].notna() & work["lng"].notna()].copy()
    if work.empty:
        vacio = pd.DataFrame()
        return vacio, vacio

    work["_celda"] = [
        _celda_geo(a, b, dec=decimales_geo) for a, b in zip(work["lat"], work["lng"], strict=False)
    ]
    work = work.loc[work["_celda"].notna()]

    if "id" not in work.columns:
        work["id"] = work.index.astype(str)
    if "inspector_nombre" not in work.columns:
        work["inspector_nombre"] = "Sin Evaluar"

    pares: list[dict[str, Any]] = []
    for celda, g in work.groupby("_celda", sort=False):
        if len(g) < 2:
            continue
        # Limitar explosión combinatoria en celdas densas
        g2 = g.head(max_por_celda)
        rows = list(g2.itertuples(index=False))
        # map column positions
        cols = list(g2.columns)
        i_id = cols.index("id")
        i_nom = cols.index("nombre_edificacion")
        i_et = cols.index("etiqueta_n")
        i_insp = cols.index("inspector_nombre")
        i_lat = cols.index("lat")
        i_lng = cols.index("lng")

        for a, b in combinations(range(len(rows)), 2):
            ra, rb = rows[a], rows[b]
            nom_a, nom_b = str(ra[i_nom]), str(rb[i_nom])
            sim = float(fuzz.token_set_ratio(nom_a, nom_b))
            if sim < umbral:
                continue
            et_a, et_b = str(ra[i_et]).upper(), str(rb[i_et]).upper()
            conflicto = et_a != et_b and et_a in {"VERDE", "AMARILLO", "ROJO", "NEGRO"} and et_b in {
                "VERDE",
                "AMARILLO",
                "ROJO",
                "NEGRO",
            }
            pares.append(
                {
                    "celda_geo": celda,
                    "similitud_pct": round(sim, 1),
                    "id_a": ra[i_id],
                    "id_b": rb[i_id],
                    "nombre_a": nom_a,
                    "nombre_b": nom_b,
                    "etiqueta_a": et_a,
                    "etiqueta_b": et_b,
                    "inspector_a": ra[i_insp],
                    "inspector_b": rb[i_insp],
                    "lat": ra[i_lat],
                    "lng": ra[i_lng],
                    "conflicto_semaforo": conflicto,
                    "posible_duplicado": True,
                }
            )

    dups = pd.DataFrame(pares)
    if dups.empty:
        return dups, dups.copy()
    alerta = dups.loc[dups["conflicto_semaforo"]].copy()
    return dups, alerta
