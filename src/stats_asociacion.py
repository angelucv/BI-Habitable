"""Asociación categórica: Chi-cuadrado y V de Cramer (corrección de sesgo)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency


def banda_anio(anio: Any) -> str:
    """Escala por décadas: ≤1950 … 2011-2020 · 2021+ · Sin año."""
    try:
        y = float(anio)
    except (TypeError, ValueError):
        return "Sin año"
    if y != y:
        return "Sin año"
    yi = int(y)
    if yi <= 1950:
        return "1950 o menos"
    if yi <= 1960:
        return "1951-1960"
    if yi <= 1970:
        return "1961-1970"
    if yi <= 1980:
        return "1971-1980"
    if yi <= 1990:
        return "1981-1990"
    if yi <= 2000:
        return "1991-2000"
    if yi <= 2010:
        return "2001-2010"
    if yi <= 2020:
        return "2011-2020"
    return "2021+"


BANDAS_ANIO = (
    "1950 o menos",
    "1951-1960",
    "1961-1970",
    "1971-1980",
    "1981-1990",
    "1991-2000",
    "2001-2010",
    "2011-2020",
    "2021+",
    "Sin año",
)


def quinquenio_anio(anio: Any) -> str:
    """Escala por quinquenios: 1950 o menos … 2016-2020 · 2021+ · Sin año."""
    try:
        y = float(anio)
    except (TypeError, ValueError):
        return "Sin año"
    if y != y:
        return "Sin año"
    yi = int(y)
    if yi <= 1950:
        return "1950 o menos"
    if yi <= 1955:
        return "1951-1955"
    if yi <= 1960:
        return "1956-1960"
    if yi <= 1965:
        return "1961-1965"
    if yi <= 1970:
        return "1966-1970"
    if yi <= 1975:
        return "1971-1975"
    if yi <= 1980:
        return "1976-1980"
    if yi <= 1985:
        return "1981-1985"
    if yi <= 1990:
        return "1986-1990"
    if yi <= 1995:
        return "1991-1995"
    if yi <= 2000:
        return "1996-2000"
    if yi <= 2005:
        return "2001-2005"
    if yi <= 2010:
        return "2006-2010"
    if yi <= 2015:
        return "2011-2015"
    if yi <= 2020:
        return "2016-2020"
    return "2021+"


QUINQUENIOS_ANIO = (
    "1950 o menos",
    "1951-1955",
    "1956-1960",
    "1961-1965",
    "1966-1970",
    "1971-1975",
    "1976-1980",
    "1981-1985",
    "1986-1990",
    "1991-1995",
    "1996-2000",
    "2001-2005",
    "2006-2010",
    "2011-2015",
    "2016-2020",
    "2021+",
    "Sin año",
)


# Pisos: uno a uno hasta este umbral; arriba se consolida la cola alta.
# p99 del mart ~20; por encima suele ser error (años de construcción, typos).
PISOS_HASTA_INDIVIDUAL = 20
# Por encima: probable error de captura (p. ej. 1985) → Sin dato
PISOS_MAX_PLAUSIBLE = 60


def banda_pisos(n_pisos: Any) -> str:
    """
    Altura casi sin agrupar: 1, 2, …, 20 pisos por separado;
    cola alta consolidada en «21 o más»; inválidos / >60 → Sin dato.
    """
    try:
        n = float(n_pisos)
    except (TypeError, ValueError):
        return "Sin dato"
    if n != n or n <= 0:
        return "Sin dato"
    ni = int(n)
    if ni > PISOS_MAX_PLAUSIBLE:
        return "Sin dato"
    if ni == 1:
        return "1 piso"
    if ni <= PISOS_HASTA_INDIVIDUAL:
        return f"{ni} pisos"
    return f"{PISOS_HASTA_INDIVIDUAL + 1} o más"


BANDAS_PISOS: tuple[str, ...] = (
    "1 piso",
    *[f"{i} pisos" for i in range(2, PISOS_HASTA_INDIVIDUAL + 1)],
    f"{PISOS_HASTA_INDIVIDUAL + 1} o más",
    "Sin dato",
)


# Bandas de altura por rigidez/flexibilidad (análisis de resonancia; no lineal)
BANDA_ALTURA_BAJA = "Baja (1 a 3 pisos)"
BANDA_ALTURA_MEDIA_BAJA = "Media-Baja (4 a 8 pisos)"
BANDA_ALTURA_MEDIA_ALTA = "Media-Alta (9 a 12 pisos)"
BANDA_ALTURA_ALTA = "Alta (13 o más pisos)"

BANDAS_ALTURA: tuple[str, ...] = (
    BANDA_ALTURA_BAJA,
    BANDA_ALTURA_MEDIA_BAJA,
    BANDA_ALTURA_MEDIA_ALTA,
    BANDA_ALTURA_ALTA,
    "Sin dato",
)


def banda_altura(n_pisos: Any) -> str:
    """
    Agrupa pisos en franjas de comportamiento dinámico típico
    (rígido → intermedio → flexible), no en escala lineal piso a piso.
    """
    try:
        n = float(n_pisos)
    except (TypeError, ValueError):
        return "Sin dato"
    if n != n or n <= 0:
        return "Sin dato"
    ni = int(n)
    if ni > PISOS_MAX_PLAUSIBLE:
        return "Sin dato"
    if ni <= 3:
        return BANDA_ALTURA_BAJA
    if ni <= 8:
        return BANDA_ALTURA_MEDIA_BAJA
    if ni <= 12:
        return BANDA_ALTURA_MEDIA_ALTA
    return BANDA_ALTURA_ALTA


def cramers_v_bias_corrected(table: pd.DataFrame) -> tuple[float, float, float]:
    """Retorna (V, chi2, p). Usa corrección de sesgo de Bergsma."""
    if table.size == 0 or table.values.sum() == 0:
        return 0.0, 0.0, 1.0
    chi2, p, _, _ = chi2_contingency(table.fillna(0).astype(int).values)
    n = float(table.values.sum())
    if n <= 0:
        return 0.0, float(chi2), float(p)
    r, k = table.shape
    phi2 = chi2 / n
    phi2_corr = max(0.0, phi2 - (k - 1) * (r - 1) / (n - 1))
    r_corr = r - (r - 1) ** 2 / (n - 1)
    k_corr = k - (k - 1) ** 2 / (n - 1)
    denom = min(r_corr - 1, k_corr - 1)
    if denom <= 0:
        return 0.0, float(chi2), float(p)
    v = float(np.sqrt(phi2_corr / denom))
    return v, float(chi2), float(p)


def preparar_categoricas(df: pd.DataFrame) -> pd.DataFrame:
    """Variables discretas para asociación con semáforo / tipología."""
    out = pd.DataFrame(index=df.index)
    out["etiqueta"] = df.get("etiqueta_n", pd.Series(index=df.index)).astype(str)
    out["material"] = (
        df.get("material_n", pd.Series(index=df.index))
        .replace({"": "Sin Evaluar", "Sin Evaluar": "Sin Evaluar"})
        .fillna("Sin Evaluar")
        .astype(str)
    )
    anio = df.get("anio_construccion_n", df.get("anio_construccion"))
    out["anio_banda"] = [banda_anio(x) for x in (anio if anio is not None else [np.nan] * len(df))]
    out["riesgo_externo"] = (
        df.get("riesgo_externo", pd.Series(False, index=df.index)).fillna(False).map(
            lambda x: "Sí" if bool(x) else "No"
        )
    )
    out["riesgo_severo"] = (
        df.get("riesgo_severo", pd.Series(False, index=df.index)).fillna(False).map(
            lambda x: "Sí" if bool(x) else "No"
        )
    )
    # Colapso estructural como proxy de falla severa
    if "ext_colapso_estructura" in df.columns:
        out["colapso_estructura"] = df["ext_colapso_estructura"].fillna("Sin Evaluar").astype(str)
    else:
        out["colapso_estructura"] = "Sin Evaluar"
    out["tipologia_pdna"] = df.get("tipologia_pdna", pd.Series(index=df.index)).fillna("Sin tipología").astype(str)
    # Solo semáforos canónicos en etiqueta para análisis
    out = out.loc[out["etiqueta"].isin(["VERDE", "AMARILLO", "ROJO", "NEGRO"])].copy()
    return out


def matriz_cramers_v(df_cat: pd.DataFrame, vars_: list[str] | None = None) -> pd.DataFrame:
    """Matriz simétrica de V de Cramer entre variables categóricas."""
    cols = vars_ or [
        "etiqueta",
        "material",
        "anio_banda",
        "riesgo_externo",
        "riesgo_severo",
        "colapso_estructura",
        "tipologia_pdna",
    ]
    cols = [c for c in cols if c in df_cat.columns]
    n = len(cols)
    mat = np.eye(n, dtype=float)
    for i in range(n):
        for j in range(i + 1, n):
            ct = pd.crosstab(df_cat[cols[i]], df_cat[cols[j]])
            v, _, _ = cramers_v_bias_corrected(ct)
            mat[i, j] = mat[j, i] = v
    return pd.DataFrame(mat, index=cols, columns=cols)


def detalle_asociacion_vs_etiqueta(df_cat: pd.DataFrame) -> pd.DataFrame:
    """Tabla V/chi2/p de cada variable vs etiqueta."""
    rows = []
    for col in df_cat.columns:
        if col == "etiqueta":
            continue
        ct = pd.crosstab(df_cat["etiqueta"], df_cat[col])
        v, chi2, p = cramers_v_bias_corrected(ct)
        rows.append(
            {
                "variable": col,
                "V_cramer": round(v, 4),
                "chi2": round(chi2, 2),
                "p_valor": round(p, 6),
                "n_celdas": int(ct.size),
            }
        )
    return pd.DataFrame(rows).sort_values("V_cramer", ascending=False)
