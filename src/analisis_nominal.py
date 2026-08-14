"""Motor estadístico para dimensiones nominales (uso / material agrupados)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from confirmacion_asociacion import odds_ratio_wald
from export_utils import fmt_es_int
from stats_asociacion import cramers_v_bias_corrected

MIN_N_CATEGORIA = 80  # omitir categorías con muestra muy chica en OR/barras


def tabla_riesgo_por_categoria(
    df: pd.DataFrame,
    *,
    col_cat: str,
    orden_pref: tuple[str, ...] | None = None,
    min_n: int = MIN_N_CATEGORIA,
) -> pd.DataFrame:
    """
    Una fila por categoría: n, críticos (Rojo+pérdida total), %.
    Orden descendente por % riesgo (para el gráfico).
    """
    if col_cat not in df.columns or df.empty:
        return pd.DataFrame()
    sub = df.loc[df["etiqueta_n"].isin(["VERDE", "AMARILLO", "ROJO", "NEGRO"])].copy()
    if sub.empty:
        return pd.DataFrame()
    sub["_crit"] = sub["etiqueta_n"].isin(["ROJO", "NEGRO"])
    g = (
        sub.groupby(col_cat, dropna=False)
        .agg(n=("etiqueta_n", "size"), criticos=("_crit", "sum"))
        .reset_index()
        .rename(columns={col_cat: "Categoria"})
    )
    g["Categoria"] = g["Categoria"].astype(str)
    g = g.loc[g["n"] >= min_n].copy()
    if g.empty:
        return g
    g["pct_riesgo"] = (100.0 * g["criticos"] / g["n"].clip(lower=1)).round(1)
    if orden_pref:
        # Mantener preferencia solo para OR; el gráfico reordena por %
        pass
    return g.sort_values("pct_riesgo", ascending=False).reset_index(drop=True)


def asociacion_nominal(
    df: pd.DataFrame,
    *,
    col_cat: str,
) -> tuple[float, float, float, int]:
    """V de Cramer, χ², p y n sobre categoría × (crítico sí/no)."""
    if col_cat not in df.columns or df.empty:
        return 0.0, 0.0, 1.0, 0
    sub = df.loc[df["etiqueta_n"].isin(["VERDE", "AMARILLO", "ROJO", "NEGRO"])].copy()
    if sub.empty:
        return 0.0, 0.0, 1.0, 0
    sub["_crit"] = np.where(sub["etiqueta_n"].isin(["ROJO", "NEGRO"]), "Crítico", "No crítico")
    ct = pd.crosstab(sub[col_cat].astype(str), sub["_crit"])
    if ct.shape[0] < 2 or ct.shape[1] < 2:
        return 0.0, 0.0, 1.0, int(len(sub))
    v, chi2, p = cramers_v_bias_corrected(ct)
    return v, chi2, p, int(len(sub))


def tabla_or_vs_base(
    tab: pd.DataFrame,
    *,
    categoria_base: str,
) -> pd.DataFrame:
    """OR de crítico vs una categoría base explícita (no la primera fila)."""
    if tab.empty or "Categoria" not in tab.columns:
        return pd.DataFrame()
    base_rows = tab.loc[tab["Categoria"] == categoria_base]
    if base_rows.empty:
        # Si la base no aparece (filtro), usar la de menor % como ancla débil
        base_rows = tab.sort_values("pct_riesgo").head(1)
        categoria_base = str(base_rows.iloc[0]["Categoria"])
    ref = base_rows.iloc[0]
    c = float(ref["criticos"])
    d = float(ref["n"] - ref["criticos"])
    rows: list[dict[str, Any]] = []
    for _, r in tab.iterrows():
        cat = str(r["Categoria"])
        n = float(r["n"])
        crit = float(r["criticos"])
        a, b = crit, n - crit
        if cat == categoria_base:
            rows.append(
                {
                    "Categoria": cat,
                    "n": int(n),
                    "criticos": int(crit),
                    "pct_riesgo": float(r["pct_riesgo"]),
                    "OR vs base": 1.0,
                    "IC95 lo": 1.0,
                    "IC95 hi": 1.0,
                    "nota": "Referencia",
                }
            )
            continue
        or_, lo, hi = odds_ratio_wald(a, b, c, d)
        rows.append(
            {
                "Categoria": cat,
                "n": int(n),
                "criticos": int(crit),
                "pct_riesgo": float(r["pct_riesgo"]),
                "OR vs base": round(or_, 2),
                "IC95 lo": round(lo, 2),
                "IC95 hi": round(hi, 2),
                "nota": "Mayor que base" if or_ > 1 else ("Menor que base" if or_ < 1 else "Similar"),
            }
        )
    return pd.DataFrame(rows)


def _factor_label(v: float) -> str:
    """Etiqueta corta para KPI (sigue siendo técnica en la tarjeta)."""
    return "Determinante" if v >= 0.15 else "Secundario"


def _influencia_negocio(v: float) -> str:
    """Traducción de fuerza de asociación a lenguaje de negocio."""
    if v >= 0.25:
        return "fuerte"
    if v >= 0.15:
        return "moderada a fuerte"
    if v >= 0.08:
        return "moderada"
    return "limitada"


def _uno_de_cada(pct: float) -> int:
    """Convierte % en lectura «1 de cada X»."""
    if pct <= 0:
        return 0
    return max(1, int(round(100.0 / pct)))


def _frase_multiplicador(or_val: float) -> str:
    """
    Traduce OR a lenguaje de negocio.
    Ej.: 2.04 → «el doble»; 0.55 → «cerca de la mitad del riesgo».
    """
    x = float(or_val)
    if x >= 2.8:
        return f"casi el triple ({x:.1f} veces)"
    if x >= 1.85:
        return f"el doble ({x:.1f} veces)"
    if x >= 1.4:
        return f"cerca de una vez y media ({x:.1f} veces)"
    if x > 1.05:
        return f"aproximadamente {x:.1f} veces"
    if x >= 0.95:
        return "un riesgo similar"
    if x >= 0.55:
        return f"cerca de la mitad del riesgo (factor {x:.2f})"
    if x > 0:
        return f"un riesgo claramente menor (factor {x:.2f})"
    return "un riesgo no comparable"


def _or_de_categoria(or_tab: pd.DataFrame, categoria: str, *, categoria_base: str) -> float | None:
    if or_tab.empty:
        return None
    if categoria == categoria_base:
        return 1.0
    match = or_tab.loc[or_tab["Categoria"] == categoria]
    if match.empty:
        return None
    return float(match.iloc[0]["OR vs base"])


def sintesis_ejecutiva_nominal(
    *,
    titulo: str,
    eje_nombre: str,
    tab: pd.DataFrame,
    or_tab: pd.DataFrame,
    v: float,
    categoria_base: str,
) -> str:
    """
    Resumen ejecutivo en lenguaje de negocio (sin jerga en el cuerpo).
    Maneja el caso base == peor (Escenario B).
    """
    _ = titulo  # título fijo de negocio abajo
    if tab.empty:
        return (
            "### 📝 Resumen del Perfil de Riesgo\n\n"
            "Sin categorías con muestra suficiente en este corte."
        )

    peor = tab.iloc[0]
    mejor = tab.iloc[-1]
    segundo = tab.iloc[1] if len(tab) > 1 else peor
    cat_peor = str(peor["Categoria"])
    cat_mejor = str(mejor["Categoria"])
    cat_segunda = str(segundo["Categoria"])
    pct_peor = float(peor["pct_riesgo"])
    pct_mejor = float(mejor["pct_riesgo"])
    uno_x = _uno_de_cada(pct_peor)
    influencia = _influencia_negocio(v)

    if cat_peor != categoria_base:
        # Escenario A: la base es un ancla «más segura» (o distinta del pico)
        or_peor = _or_de_categoria(or_tab, cat_peor, categoria_base=categoria_base)
        if or_peor is None:
            or_peor = 1.0
            sub = or_tab.loc[or_tab["Categoria"] != categoria_base] if not or_tab.empty else or_tab
            if not sub.empty:
                or_peor = float(sub.sort_values("OR vs base", ascending=False).iloc[0]["OR vs base"])
        frase_or = _frase_multiplicador(or_peor)
        bloque_relativo = (
            f"*   🎯 **Impacto de la Tipología:** Utilizando las estructuras de "
            f"**{categoria_base}** como punto de referencia seguro, los datos confirman "
            f"que construir / operar con tipología **{cat_peor}** multiplica el riesgo "
            f"de colapso o daño severo por **{frase_or}**."
        )
    else:
        # Escenario B: la propia base es el perfil más crítico
        or_seg = _or_de_categoria(or_tab, cat_segunda, categoria_base=categoria_base)
        if or_seg is None:
            or_seg = 1.0
        frase_seg = _frase_multiplicador(or_seg)
        bloque_relativo = (
            f"*   🎯 **Impacto de la Tipología:** La categoría de referencia "
            f"(**{categoria_base}**) resultó ser el perfil más crítico de todo el portafolio. "
            f"En contraste, el resto de las estructuras, como **{cat_segunda}**, demostraron "
            f"ser considerablemente más seguras, presentando un nivel de riesgo "
            f"significativamente menor ({frase_seg})."
        )

    return (
        "### 📝 Resumen del Perfil de Riesgo\n\n"
        f"🚨 **Alerta Principal:** El {eje_nombre} tiene una influencia **{influencia}** "
        f"en la probabilidad de daño total. El foco de vulnerabilidad se concentra "
        f"claramente en **{cat_peor}**, donde aproximadamente **1 de cada {uno_x}** "
        f"inspecciones ({pct_peor:.1f}%) culmina en pérdida total o riesgo alto.\n\n"
        f"{bloque_relativo}\n"
        f"*   📊 **Comportamiento del Portafolio:** Mientras que **{cat_peor}** lidera "
        f"las estadísticas de daño, el mejor desempeño estructural se observó en la "
        f"categoría de **{cat_mejor}**, logrando contener la tasa de falla en apenas "
        f"un **{pct_mejor:.1f}%**.\n\n"
        f"**⚠️ Decisión Operativa:**\n"
        f"Para la mitigación de riesgos y el despliegue de recursos, el sistema sugiere "
        f"perfilar a las edificaciones catalogadas como **{cat_peor}** con prioridad "
        f"de inspección roja."
    )


def opts_barras_riesgo_horizontal(tab: pd.DataFrame, *, titulo_eje: str = "% Rojo + pérdida total") -> dict[str, Any] | None:
    """Barras horizontales: % riesgo desc.; etiqueta con % y N."""
    from charts_habitable import _base_opts

    if tab is None or tab.empty:
        return None
    # ECharts category axis: first item at bottom → ascending so peor queda arriba
    t = tab.sort_values("pct_riesgo", ascending=True)
    cats = t["Categoria"].astype(str).tolist()
    pcts = [float(x) for x in t["pct_riesgo"].tolist()]
    ns = [int(x) for x in t["n"].tolist()]

    data = []
    for p, n in zip(pcts, ns, strict=True):
        if p >= 25:
            color = "#7F1D1D"
        elif p >= 15:
            color = "#DC2626"
        elif p >= 10:
            color = "#F97316"
        else:
            color = "#FDBA74"
        data.append(
            {
                "value": p,
                "itemStyle": {"color": color},
                "label": {
                    "show": True,
                    "position": "right",
                    "formatter": f"{p:.0f}% · n={fmt_es_int(n)}",
                    "fontSize": 11,
                    "fontWeight": 700,
                    "color": "#0F172A",
                },
            }
        )

    return _base_opts(
        tooltip={
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
        },
        grid={"left": 8, "right": 110, "top": 24, "bottom": 24, "containLabel": True},
        xAxis={
            "type": "value",
            "name": titulo_eje,
            "max": max(40, int(max(pcts) + 8) if pcts else 40),
            "axisLabel": {"formatter": "{value}%"},
            "splitLine": {"lineStyle": {"color": "#E2E8F0"}},
        },
        yAxis={
            "type": "category",
            "data": cats,
            "axisLabel": {"fontSize": 12, "fontWeight": 600, "color": "#0F172A"},
        },
        series=[
            {
                "type": "bar",
                "data": data,
                "barMaxWidth": 28,
                "label": {"show": True},
            }
        ],
    )
