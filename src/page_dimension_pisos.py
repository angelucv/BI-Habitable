"""Dimensión: número de pisos vs daño / semáforo (misma lógica que año)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import streamlit as st
from streamlit_echarts import st_echarts

from charts_habitable import ETIQUETA_COLORS, _base_opts, etiqueta_label
from clean_catalog import MATERIAL_GRUPOS, USO_GRUPOS, clasificar_material
from confirmacion_asociacion import (
    lectura_didactica_cramer,
    lectura_didactica_or,
    tabla_or_vs_referencia,
)
from export_utils import fmt_es_int
from process_habitable import ETIQUETAS
from stats_asociacion import (
    BANDA_ALTURA_ALTA,
    BANDA_ALTURA_BAJA,
    BANDAS_ALTURA,
    banda_altura,
    cramers_v_bias_corrected,
)
from ui_theme import render_kpi_strip, render_section

ORDEN_Q = BANDAS_ALTURA

MIN_N_CELDA = 30  # celda gris si n menor
MIN_CELDAS_FILA = 2  # con 4 bandas de altura, exigir cobertura mínima
MIN_N_FILA = 400  # volumen mínimo de la fila (uso/estado)
MIN_N_ESTADO_FILTRO = 200  # mismo umbral operativo que tortas
MIN_N_MUN_FILTRO = 80


def _pisos(df: pd.DataFrame) -> pd.Series:
    if "num_pisos" in df.columns:
        return pd.to_numeric(df["num_pisos"], errors="coerce")
    return pd.Series(np.nan, index=df.index)


def _prep(df: pd.DataFrame) -> pd.DataFrame:
    out = df.loc[df["etiqueta_n"].isin(ETIQUETAS)].copy()
    # Eje interno "quinquenio" = banda de altura (resonancia), no piso a piso.
    out["quinquenio"] = [banda_altura(x) for x in _pisos(out)]
    src_mat = out["material_n"] if "material_n" in out.columns else out.get("material")
    if src_mat is not None:
        out["material_grupo"] = [clasificar_material(x) for x in src_mat]
    else:
        out["material_grupo"] = "Otro / sin dato"
    return out


def _labs_presentes(df: pd.DataFrame, *, excluir_sin_anio: bool = False) -> list[str]:
    presentes = set(df["quinquenio"].unique())
    labs = [b for b in ORDEN_Q if b in presentes]
    if excluir_sin_anio:
        labs = [b for b in labs if b != "Sin dato"]
    return labs


def _opts_apilado_semaforo(
    df: pd.DataFrame,
    *,
    modo: str = "conteo",
    excluir_sin_anio: bool = True,
) -> dict[str, Any] | None:
    """Barras apiladas por quinquenio × semáforo. modo: conteo | pct."""
    labs = _labs_presentes(df, excluir_sin_anio=excluir_sin_anio)
    if not labs:
        return None
    ct = pd.crosstab(df["quinquenio"], df["etiqueta_n"])
    for e in ETIQUETAS:
        if e not in ct.columns:
            ct[e] = 0
    ct = ct.reindex(index=labs, columns=list(ETIQUETAS), fill_value=0)
    if modo == "pct":
        tot = ct.sum(axis=1).clip(lower=1)
        vals = (ct.div(tot, axis=0) * 100.0).round(1)
        y_axis: dict[str, Any] = {
            "type": "value",
            "max": 100,
            "axisLabel": {"formatter": "{value}%"},
        }
        tip = {"trigger": "axis", "axisPointer": {"type": "shadow"}}
    else:
        vals = ct
        y_axis = {"type": "value"}
        tip = {"trigger": "axis", "axisPointer": {"type": "shadow"}}

    series = [
        {
            "name": etiqueta_label(e),
            "type": "bar",
            "stack": "sem",
            "emphasis": {"focus": "series"},
            "itemStyle": {"color": ETIQUETA_COLORS[e]},
            "data": [float(vals.loc[b, e]) if modo == "pct" else int(vals.loc[b, e]) for b in labs],
        }
        for e in ETIQUETAS
    ]
    # Total + % del total debajo de cada barra (solo conteos)
    dense = len(labs) >= 10
    if modo == "conteo":
        totales = [int(ct.loc[b].sum()) for b in labs]
        n_tot = max(sum(totales), 1)
        series.append(
            {
                "name": "_total",
                "type": "bar",
                "data": [
                    {
                        "value": t,
                        "label": {
                            "show": True,
                            "position": "bottom",
                            "distance": 4,
                            "formatter": f"{fmt_es_int(t)}\n{100.0 * t / n_tot:.1f}%",
                            "fontWeight": 700,
                            "fontSize": 8 if dense else 10,
                            "lineHeight": 11 if dense else 13,
                            "color": "#0F172A",
                            "align": "center",
                        },
                    }
                    for t in totales
                ],
                "barGap": "-100%",
                "itemStyle": {"color": "rgba(0,0,0,0)"},
                "emphasis": {"disabled": True},
                "tooltip": {"show": False},
                "silent": True,
                "z": 20,
                "label": {"show": True},
                "barMaxWidth": 18 if dense else 36,
            }
        )
        top_grid = 52
        bottom_grid = 130 if dense else 122
    else:
        top_grid = 52
        bottom_grid = 80 if dense else 72

    for s in series:
        if s.get("name") != "_total" and s.get("type") == "bar":
            s["barMaxWidth"] = 18 if dense else 36

    return _base_opts(
        tooltip=tip,
        legend={
            "top": 0,
            "left": "center",
            "orient": "horizontal",
            "data": [etiqueta_label(e) for e in ETIQUETAS],
        },
        grid={"left": 48, "right": 24, "top": top_grid, "bottom": bottom_grid},
        xAxis={
            "type": "category",
            "data": labs,
            "axisLabel": {
                "rotate": 50 if dense else 40,
                "fontSize": 9 if dense else 10,
                "fontWeight": 600,
                "margin": 36 if modo == "conteo" else 8,
            },
        },
        yAxis=y_axis,
        series=series,
    )


def _opts_pct_etiqueta_h(df: pd.DataFrame, etiqueta: str, *, color: str) -> dict[str, Any] | None:
    """Barras horizontales: % de una etiqueta por quinquenio."""
    rows = []
    for b in _labs_presentes(df, excluir_sin_anio=True):
        sub = df.loc[df["quinquenio"] == b]
        if sub.empty:
            continue
        n = len(sub)
        pct = round(100.0 * float((sub["etiqueta_n"] == etiqueta).mean()), 1)
        rows.append({"banda": b, "pct": pct, "n": n})
    if not rows:
        return None
    ymax = max(10.0, max(r["pct"] for r in rows) * 1.15)
    return _base_opts(
        tooltip={"trigger": "axis"},
        legend={"show": False},
        grid={"left": 16, "right": 48, "top": 28, "bottom": 24, "containLabel": True},
        xAxis={"type": "value", "max": round(ymax, 1), "axisLabel": {"formatter": "{value}%"}},
        yAxis={"type": "category", "data": [r["banda"] for r in rows], "inverse": True},
        series=[
            {
                "type": "bar",
                "data": [
                    {
                        "value": r["pct"],
                        "itemStyle": {"color": color, "borderRadius": [0, 6, 6, 0]},
                    }
                    for r in rows
                ],
                "label": {"show": True, "position": "right", "formatter": "{c}%", "fontWeight": 700},
                "barMaxWidth": 22,
            }
        ],
    )


def _opts_pct_etiqueta(df: pd.DataFrame, etiqueta: str, *, color: str) -> dict[str, Any] | None:
    """% de una etiqueta por banda de altura (sin tendencia lineal)."""
    labs = _labs_presentes(df, excluir_sin_anio=True)
    if not labs:
        return None
    rows = []
    for b in labs:
        sub = df.loc[df["quinquenio"] == b]
        n = len(sub)
        if n == 0:
            continue
        pct = round(100.0 * float((sub["etiqueta_n"] == etiqueta).mean()), 1)
        rows.append({"banda": b, "pct": pct, "n": n})
    if not rows:
        return None
    pico = max(rows, key=lambda r: r["pct"])["banda"]
    ys = np.array([r["pct"] for r in rows], dtype=float)
    ymax = max(10.0, float(ys.max()) * 1.25)
    return _base_opts(
        tooltip={"trigger": "axis"},
        legend={"show": False},
        grid={"left": 48, "right": 24, "top": 36, "bottom": 88},
        xAxis={
            "type": "category",
            "data": [r["banda"] for r in rows],
            "axisLabel": {
                "rotate": 18,
                "fontSize": 11,
                "fontWeight": 600,
                "interval": 0,
            },
        },
        yAxis={
            "type": "value",
            "max": round(ymax, 1),
            "axisLabel": {"formatter": "{value}%"},
            "name": "%",
        },
        series=[
            {
                "name": "% pérdida total",
                "type": "bar",
                "data": [
                    {
                        "value": r["pct"],
                        "itemStyle": {
                            "color": "#7F1D1D" if r["banda"] == pico else color,
                            "borderRadius": [4, 4, 0, 0],
                            "opacity": 0.45 if r["n"] < 30 else 0.95,
                            "borderColor": "#FCD116" if r["banda"] == pico else "transparent",
                            "borderWidth": 2 if r["banda"] == pico else 0,
                        },
                    }
                    for r in rows
                ],
                "label": {
                    "show": True,
                    "position": "top",
                    "formatter": "{c}%",
                    "fontSize": 12,
                    "fontWeight": 700,
                },
                "barMaxWidth": 56,
            }
        ],
    )


def texto_sintesis_resonancia(tab: pd.DataFrame, or_tab: pd.DataFrame) -> str:
    """Síntesis ejecutiva: daño por bandas de altura (efecto de resonancia)."""
    if tab.empty:
        return "Sin bandas suficientes para evaluar el efecto de altura."
    peor = tab.sort_values("% NEGRO", ascending=False).iloc[0]
    banda_peor = str(peor["Banda"])
    pct_peor = float(peor["% NEGRO"])

    alta = tab.loc[tab["Banda"] == BANDA_ALTURA_ALTA]
    if alta.empty:
        banda_alta = BANDA_ALTURA_ALTA
        pct_alta = 0.0
    else:
        banda_alta = BANDA_ALTURA_ALTA
        pct_alta = float(alta.iloc[0]["% NEGRO"])

    or_max = 1.0
    if not or_tab.empty:
        match = or_tab.loc[or_tab["Banda"] == banda_peor]
        if not match.empty and str(match.iloc[0].get("nota", "")) != "Referencia":
            or_max = float(match.iloc[0]["OR vs ref."])
        else:
            sub = or_tab.loc[or_tab["nota"] != "Referencia"]
            if not sub.empty:
                or_max = float(sub.sort_values("OR vs ref.", ascending=False).iloc[0]["OR vs ref."])

    return (
        "### 📝 Evaluación de Riesgo por Altura (Efecto de Resonancia)\n\n"
        "🚨 **Alerta Principal:** El nivel de daño no aumenta de forma lineal con la altura "
        "de la edificación, sino que se concentra en franjas específicas. "
        f"La banda de altura más crítica detectada es **{banda_peor}**, "
        f"presentando un **{pct_peor:.1f}%** de pérdida total.\n\n"
        f"*   **🎯 Riesgo Relativo:** Al comparar el desempeño del portafolio contra las "
        f"estructuras más rígidas (**{BANDA_ALTURA_BAJA}**), los edificios ubicados en la "
        f"franja de **{banda_peor}** tienen **{or_max:.2f} veces más probabilidades** "
        f"de sufrir pérdida total.\n"
        f"*   **📊 Comportamiento de Estructuras Flexibles:** Las edificaciones más altas "
        f"({banda_alta}) muestran un riesgo del **{pct_alta:.1f}%**, confirmando que el daño "
        f"se concentra en alturas intermedias debido a posibles efectos de resonancia con el suelo.\n\n"
        f"**⚠️ Recomendación Operativa:**\n"
        f"Abandone el análisis piso a piso. Utilice la franja de **{banda_peor}** como un "
        f"perfil de alto riesgo (Bandera Roja) para cruzarlo inmediatamente con la tipología "
        f"estructural y la microzonificación de los municipios más afectados."
    )


def _tabla_asociacion(df: pd.DataFrame, col_a: str, col_b: str) -> tuple[float, float, float, int]:
    ct = pd.crosstab(df[col_a], df[col_b])
    v, chi2, p = cramers_v_bias_corrected(ct)
    return v, chi2, p, int(ct.values.sum())


def _estados_frecuentes(df: pd.DataFrame, *, minimo: int = MIN_N_ESTADO_FILTRO) -> list[str]:
    ban = {"", "NAN", "nan", "(SIN ESTADO)", "(sin estado)", "SIN EVALUAR", "Sin Evaluar"}
    s = df["estado_n"].dropna().astype(str)
    s = s.loc[~s.isin(ban)]
    vc = s.value_counts()
    return vc.loc[vc >= minimo].index.tolist()


def _municipios_frecuentes(
    df: pd.DataFrame,
    *,
    estados: list[str] | None = None,
    minimo: int = MIN_N_MUN_FILTRO,
    top: int = 25,
) -> list[str]:
    ban = {"", "SIN EVALUAR", "Sin Evaluar", "CARACAS", "NAN", "nan"}
    sub = df
    if estados:
        sub = sub.loc[sub["estado_n"].isin(estados)]
    s = sub["municipio_n"].dropna().astype(str)
    s = s.loc[~s.isin(ban)]
    vc = s.value_counts()
    return vc.loc[vc >= minimo].head(top).index.tolist()


def _usos_frecuentes(df: pd.DataFrame) -> list[str]:
    if "uso_n" not in df.columns:
        return []
    presentes = set(df["uso_n"].dropna().astype(str).unique())
    orden = [u for u in USO_GRUPOS if u in presentes]
    extra = sorted(presentes - set(USO_GRUPOS))
    return orden + extra


def _materiales_grupo(df: pd.DataFrame) -> list[str]:
    if "material_grupo" not in df.columns:
        return []
    presentes = set(df["material_grupo"].dropna().astype(str).unique())
    return [g for g in MATERIAL_GRUPOS if g in presentes]


def _tabla_pct_negro(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for b in _labs_presentes(df, excluir_sin_anio=True):
        sub = df.loc[df["quinquenio"] == b]
        n = len(sub)
        n_neg = int((sub["etiqueta_n"] == "NEGRO").sum())
        rows.append(
            {
                "Banda": b,
                "Inspecciones": n,
                "NEGRO": n_neg,
                "% NEGRO": round(100.0 * n_neg / max(n, 1), 1),
            }
        )
    return pd.DataFrame(rows)


def _nivel_v(v: float) -> str:
    if v < 0.05:
        return "muy débil"
    if v < 0.15:
        return "débil"
    if v < 0.25:
        return "moderada"
    return "notable"


def _texto_lectura_negro(
    *,
    v: float,
    p: float,
    n: int,
    n_neg: int,
    tab: pd.DataFrame,
    filtros_txt: str,
    nombre_eje: str = "la banda",
) -> str:
    nivel = _nivel_v(v)
    pct_neg = 100.0 * n_neg / max(n, 1)
    if tab.empty or len(tab) < 2:
        tendencia = f"No hay suficientes bandas ({nombre_eje}) para describir una tendencia."
        pico_txt = ""
    else:
        mitad = max(1, len(tab) // 3)
        viejo = float(tab.head(mitad)["% NEGRO"].mean())
        reciente = float(tab.tail(mitad)["% NEGRO"].mean())
        idx = tab["% NEGRO"].idxmax()
        pico = tab.loc[idx]
        banda_pico = str(pico["Banda"]) if "Banda" in tab.columns else str(pico.iloc[0])
        if reciente > viejo + 0.5:
            tendencia = (
                f"En este corte, el % con pérdida total promedio de bandas posteriores "
                f"({reciente:.1f} %) supera al de las iniciales ({viejo:.1f} %)."
            )
        elif viejo > reciente + 0.5:
            tendencia = (
                f"En este corte, el % con pérdida total promedio es mayor en bandas iniciales "
                f"({viejo:.1f} %) que en las posteriores ({reciente:.1f} %)."
            )
        else:
            tendencia = (
                f"En este corte, el % con pérdida total se mantiene parecido entre bandas iniciales "
                f"({viejo:.1f} %) y posteriores ({reciente:.1f} %)."
            )
        pico_txt = (
            f" El máximo del corte está en **{banda_pico}** "
            f"({float(pico['% NEGRO']):.1f} %, n={fmt_es_int(int(pico['Inspecciones']))})."
        )

    p_txt = (
        "La p es muy pequeña: con este volumen de datos la relación no parece casualidad."
        if p < 0.01
        else "La p no es concluyente; conviene no forzar conclusiones."
    )

    return (
        f"**Corte analizado:** {filtros_txt}\n\n"
        f"**Cómo leerlo**\n\n"
        f"1. El gráfico de la izquierda muestra la *proporción* de **pérdida total** por {nombre_eje} "
        f"en este corte ({fmt_es_int(n)} insp.; {fmt_es_int(n_neg)} pérdida total, {pct_neg:.1f} %).\n\n"
        f"2. La **V de Cramer** (0–1) mide qué tan ligada está {nombre_eje} con la *pérdida total*. "
        f"Aquí V ≈ **{v:.2f}** → asociación **{nivel}** "
        f"(el factor ayuda a matizar, no a explicar casi todos los casos).\n\n"
        f"3. {p_txt} No implica causalidad.\n\n"
        f"**Lectura de este filtro:** {tendencia}{pico_txt}"
    )


def _titulo_prueba(num: int, pregunta: str, herramienta: str) -> None:
    """Cabecera didáctica: pregunta primero, nombre técnico debajo."""
    st.markdown(f"**{num} · {pregunta}**")
    st.caption(f"Herramienta: {herramienta}")


def _bloque_or_vs_baja(
    tab: pd.DataFrame,
    *,
    num_or: int = 2,
) -> pd.DataFrame:
    """Odds Ratio de cada banda vs Baja (1 a 3 pisos). Sin Cochran–Armitage."""
    if tab.empty or "Banda" not in tab.columns:
        return pd.DataFrame()
    # Forzar referencia = banda baja (primera en ORDEN_Q)
    orden = [b for b in ORDEN_Q if b != "Sin dato" and b in set(tab["Banda"])]
    if BANDA_ALTURA_BAJA not in orden:
        st.warning(f"No hay inspecciones en **{BANDA_ALTURA_BAJA}** para usarla como base del OR.")
        return pd.DataFrame()
    tab_ord = tab.set_index("Banda").reindex(orden).dropna(subset=["Inspecciones"]).reset_index()
    # Poner Baja primero
    tab_ord = pd.concat(
        [
            tab_ord.loc[tab_ord["Banda"] == BANDA_ALTURA_BAJA],
            tab_ord.loc[tab_ord["Banda"] != BANDA_ALTURA_BAJA],
        ],
        ignore_index=True,
    )
    or_tab = tabla_or_vs_referencia(tab_ord, col_banda="Banda")
    if len(or_tab) > 1:
        top = or_tab.iloc[1:].sort_values("OR vs ref.", ascending=False).iloc[0]
        _titulo_prueba(
            num_or,
            f"¿Qué franja se separa más de «{BANDA_ALTURA_BAJA}»?",
            "Razón de momios (Odds Ratio) vs banda rígida de referencia",
        )
        st.metric("OR máximo vs baja", f"{top['OR vs ref.']:.2f}")
        st.caption(
            f"Banda de mayor contraste: **{top['Banda']}** · "
            f"IC95 {top['IC95 lo']:.2f}–{top['IC95 hi']:.2f}"
        )
        st.info(lectura_didactica_or(or_tab))
    with st.expander(f"Tabla OR por banda (vs {BANDA_ALTURA_BAJA})", expanded=False):
        st.dataframe(or_tab, use_container_width=True, hide_index=True)
    return or_tab


def _aplicar_filtros_dimension(
    work: pd.DataFrame,
    *,
    key_prefix: str,
    titulo: str = "Filtros de este análisis",
    con_territorio: bool = True,
) -> tuple[pd.DataFrame, str]:
    """Filtros opcionales de territorio + uso / material. Retorna (df_filtrado, texto_corte)."""
    st.markdown(f"##### {titulo}")
    estados: list[str] = []
    municipios: list[str] = []
    usos: list[str] = []
    materiales: list[str] = []

    if con_territorio:
        est_opts = _estados_frecuentes(work)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            estados = st.multiselect(
                "Estado (más frecuentes)",
                est_opts,
                default=[],
                key=f"{key_prefix}_estado",
                help=f"Estados con ≥{MIN_N_ESTADO_FILTRO} inspecciones (criterio similar a las tortas).",
            )
        df_m = work if not estados else work.loc[work["estado_n"].isin(estados)]
        with c2:
            mun_opts = _municipios_frecuentes(df_m, estados=estados or None)
            municipios = st.multiselect(
                "Municipio (más frecuentes)",
                mun_opts,
                default=[],
                key=f"{key_prefix}_mun",
                help=f"Municipios con ≥{MIN_N_MUN_FILTRO} insp. en el corte de estado.",
            )
        with c3:
            usos = st.multiselect(
                "Uso agrupado",
                _usos_frecuentes(work),
                default=[],
                key=f"{key_prefix}_uso",
            )
        with c4:
            materiales = st.multiselect(
                "Material (agrupado)",
                _materiales_grupo(work),
                default=[],
                key=f"{key_prefix}_mat",
                help="Familias estructurales: concreto, mixto, mampostería, acero, túnel, tradicional…",
            )
    else:
        c1, c2 = st.columns(2)
        with c1:
            usos = st.multiselect(
                "Uso agrupado",
                _usos_frecuentes(work),
                default=[],
                key=f"{key_prefix}_uso",
            )
        with c2:
            materiales = st.multiselect(
                "Material (agrupado)",
                _materiales_grupo(work),
                default=[],
                key=f"{key_prefix}_mat",
                help="Familias estructurales: concreto, mixto, mampostería, acero, túnel, tradicional…",
            )

    dff = work
    partes: list[str] = []
    if estados:
        dff = dff.loc[dff["estado_n"].isin(estados)]
        partes.append("estado: " + ", ".join(estados))
    if municipios:
        dff = dff.loc[dff["municipio_n"].isin(municipios)]
        partes.append("municipio: " + ", ".join(municipios))
    if usos and "uso_n" in dff.columns:
        dff = dff.loc[dff["uso_n"].isin(usos)]
        partes.append("uso: " + ", ".join(usos))
    if materiales and "material_grupo" in dff.columns:
        dff = dff.loc[dff["material_grupo"].isin(materiales)]
        partes.append("material: " + ", ".join(materiales))
    if partes:
        filtros_txt = "; ".join(partes)
    elif con_territorio:
        filtros_txt = "todo el país (sin filtro territorial/uso/material)"
    else:
        filtros_txt = "todos los estados (sin filtro de uso/material)"
    st.caption(f"Corte activo: **{fmt_es_int(len(dff))}** de **{fmt_es_int(len(work))}** · {filtros_txt}")
    return dff, filtros_txt


def _render_tab_panorama(work: pd.DataFrame) -> None:
    dff, _filtros_txt = _aplicar_filtros_dimension(work, key_prefix="dim_pis_pan")
    if dff.empty:
        st.warning("El filtro no deja filas. Amplíe la selección.")
        return

    st.markdown("##### Volumen por banda de altura · barras apiladas por semáforo")
    st.caption(
        "Cuatro franjas de rigidez/flexibilidad: Baja (1–3), Media-Baja (4–8), "
        "Media-Alta (9–12) y Alta (13+). Debajo de cada barra: total y % del corte."
    )
    opts = _opts_apilado_semaforo(dff, modo="conteo", excluir_sin_anio=True)
    if opts:
        st_echarts(opts, height="400px", key="dim-p-panorama")

    st.markdown("##### % pérdida total por banda de altura")
    opts_neg = _opts_pct_etiqueta(dff, "NEGRO", color="#1E293B")
    if opts_neg:
        st_echarts(opts_neg, height="320px", key="dim-p-pct-negro")

    with st.expander("Conteos banda de altura × semáforo", expanded=False):
        ct = pd.crosstab(dff["quinquenio"], dff["etiqueta_n"])
        for e in ETIQUETAS:
            if e not in ct.columns:
                ct[e] = 0
        ct = ct.reindex(
            index=[b for b in ORDEN_Q if b in ct.index],
            columns=list(ETIQUETAS),
            fill_value=0,
        )
        ct["Total"] = ct.sum(axis=1)
        ct["% NEGRO"] = (100.0 * ct.get("NEGRO", 0) / ct["Total"].clip(lower=1)).round(1)
        st.dataframe(ct, use_container_width=True)


def _render_tab_anio_vs_dano(work: pd.DataFrame) -> None:
    dff, filtros_txt = _aplicar_filtros_dimension(work, key_prefix="dim_pis_avd")
    if dff.empty:
        st.warning("El filtro no deja filas. Amplíe la selección.")
        return

    st.markdown("##### Composición del semáforo por banda de altura (100 %)")
    st.caption(
        "Contexto de mezcla V/A/R/N. El análisis estricto de asociación usa solo la **pérdida total**. "
        "La vulnerabilidad por altura no es lineal: se evalúa por franjas (resonancia)."
    )
    opts = _opts_apilado_semaforo(dff, modo="pct", excluir_sin_anio=True)
    if opts:
        st_echarts(opts, height="380px", key="dim-p-pct")

    sub = dff.loc[dff["quinquenio"] != "Sin dato"].copy()
    if len(sub) < 30:
        st.warning("Muestra insuficiente sin «Sin dato» en este corte.")
        return
    sub["es_negro"] = np.where(sub["etiqueta_n"] == "NEGRO", "NEGRO", "No NEGRO")
    if sub["es_negro"].nunique() < 2 or sub["quinquenio"].nunique() < 2:
        st.warning("En este corte no hay contraste suficiente (falta pérdida total o una sola banda).")
        return

    st.markdown("##### % pérdida total por banda de altura")
    st.caption(
        "Cuatro bandas. La barra resaltada (borde amarillo) concentra el **pico** de pérdida total. "
        "No se ajusta tendencia lineal: el fenómeno es unimodal (resonancia), no monótono."
    )
    opts_neg = _opts_pct_etiqueta(sub, "NEGRO", color="#1E293B")
    if opts_neg:
        st_echarts(opts_neg, height="360px", key="dim-p-negro-v")

    tab = _tabla_pct_negro(sub)
    v, chi2, p, n_ct = _tabla_asociacion(sub, "quinquenio", "es_negro")
    n_neg = int((sub["etiqueta_n"] == "NEGRO").sum())

    st.markdown("##### Pruebas estadísticas (nominales por banda)")
    c1, c2 = st.columns(2)
    with c1:
        _titulo_prueba(
            1,
            "¿Qué tan ligada está la banda de altura con la pérdida total?",
            "V de Cramer (asociación categórica · sin asumir linealidad)",
        )
        st.metric("Fuerza del vínculo (0–1)", f"{v:.3f}")
        st.caption(
            f"χ² = {chi2:.1f} · p = {p:.4g} · n = {fmt_es_int(n_ct)} · "
            "banda de altura × pérdida total sí/no"
        )
        st.info(lectura_didactica_cramer(v=v, p=p, n_neg=n_neg, n=len(sub)))
    with c2:
        or_tab = _bloque_or_vs_baja(tab, num_or=2)

    st.markdown("##### Síntesis ejecutiva")
    st.markdown(texto_sintesis_resonancia(tab, or_tab))

    st.markdown("##### Tabla % pérdida total por banda de altura")
    if not tab.empty:
        st.dataframe(tab, use_container_width=True, hide_index=True)

    with st.expander("¿Por qué no Cochran–Armitage aquí?", expanded=False):
        st.markdown(
            "La prueba de tendencia lineal asume que el riesgo **sube o baja de forma monótona** "
            "con el orden de las categorías. En altura sísmica el daño suele concentrarse en "
            "**franjas intermedias** (posible resonancia con el suelo), no en una recta. "
            f"Por eso se usan **4 bandas** y **Odds Ratio vs {BANDA_ALTURA_BAJA}**."
        )
        st.caption(f"Corte: {filtros_txt}")


def _hex_to_rgb(hx: str) -> tuple[float, float, float]:
    h = hx.lstrip("#")
    return int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0


def _rel_luminance(hx: str) -> float:
    def _lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = _hex_to_rgb(hx)
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def _text_on_bg(hx: str) -> str:
    """#FFFFFF o #000000 según luminosidad relativa del fondo."""
    return "#FFFFFF" if _rel_luminance(hx) < 0.45 else "#000000"


_HEAT_PALETTE = ("#FEF3C7", "#FDBA74", "#F97316", "#DC2626", "#7F1D1D")
_HEAT_EMPTY = "#F0F0F0"


def _heat_color(t: float) -> str:
    """t ∈ [0, 100] → color en la paleta de riesgo."""
    x = max(0.0, min(100.0, float(t))) / 100.0
    n = len(_HEAT_PALETTE) - 1
    pos = x * n
    i = int(pos)
    if i >= n:
        return _HEAT_PALETTE[-1]
    frac = pos - i
    r1, g1, b1 = _hex_to_rgb(_HEAT_PALETTE[i])
    r2, g2, b2 = _hex_to_rgb(_HEAT_PALETTE[i + 1])
    r = int(round((r1 + (r2 - r1) * frac) * 255))
    g = int(round((g1 + (g2 - g1) * frac) * 255))
    b = int(round((b1 + (b2 - b1) * frac) * 255))
    return f"#{r:02X}{g:02X}{b:02X}"


def _celda_insuficiente(*, j: int, i: int, tip: str) -> dict[str, Any]:
    return {
        "value": [j, i, None],
        "itemStyle": {
            "color": _HEAT_EMPTY,
            "borderColor": "#E5E7EB",
            "borderWidth": 1,
        },
        "label": {
            "show": True,
            "formatter": "—",
            "color": "#64748B",
            "fontSize": 11,
            "fontWeight": 600,
        },
        "tooltip": {"formatter": tip},
        "name": tip,
    }


def _celda_pct(
    *,
    j: int,
    i: int,
    pct: float,
    n: int,
    color_v: float,
    row: str,
    col: str,
) -> dict[str, Any]:
    bg = _heat_color(color_v)
    fg = _text_on_bg(bg)
    tip = (
        f"{row} · {col}<br/>"
        f"De cada 100 inspecciones, <b>{pct:.0f}</b> quedaron en "
        f"rojo o pérdida total ({pct:.1f}%)<br/>"
        f"n = {fmt_es_int(n)}"
    )
    return {
        "value": [j, i, color_v],
        "itemStyle": {"color": bg, "borderColor": "#FFFFFF", "borderWidth": 0.5},
        "label": {
            "show": True,
            "formatter": "{pct|" + f"{pct:.0f}%" + "}",
            "rich": {
                "pct": {
                    "color": fg,
                    "fontSize": 10,
                    "fontWeight": "bold",
                }
            },
        },
        "tooltip": {"formatter": tip},
        "name": tip.replace("<br/>", " · ").replace("<b>", "").replace("</b>", ""),
    }


def _matriz_pct(
    df: pd.DataFrame,
    *,
    row_col: str,
    row_labs: list[str],
    col_labs: list[str],
) -> tuple[list[str], list[str], dict[tuple[str, str], tuple[float, int, bool]]]:
    raw: dict[tuple[str, str], tuple[float, int, bool]] = {}
    keep_rows: list[str] = []
    for row in row_labs:
        n_fila = int((df[row_col] == row).sum())
        if n_fila < MIN_N_FILA:
            continue
        valid = 0
        for col in col_labs:
            cel = df.loc[(df[row_col] == row) & (df["quinquenio"] == col)]
            n = len(cel)
            if n <= 0:
                raw[(row, col)] = (0.0, 0, False)
                continue
            pct = round(100.0 * float(cel["etiqueta_n"].isin(["ROJO", "NEGRO"]).mean()), 1)
            fiable = n >= MIN_N_CELDA
            raw[(row, col)] = (pct, n, fiable)
            if fiable:
                valid += 1
        if valid >= MIN_CELDAS_FILA:
            keep_rows.append(row)
    kept = {k: v for k, v in raw.items() if k[0] in keep_rows}
    return keep_rows, col_labs, kept


def _ordenar_filas_por_riesgo(
    rows: list[str],
    cols: list[str],
    cell: dict[tuple[str, str], tuple[float, int, bool]],
) -> list[str]:
    """Mayor → menor según riesgo promedio ponderado por n (celdas fiables)."""

    def _avg(r: str) -> float:
        num = 0.0
        den = 0
        for c in cols:
            if (r, c) not in cell:
                continue
            pct, n, fiable = cell[(r, c)]
            if not fiable or n <= 0:
                continue
            num += pct * n
            den += n
        return (num / den) if den else -1.0

    return sorted(rows, key=_avg, reverse=True)


def _heatmap_pct_adv(
    df: pd.DataFrame,
    *,
    row_col: str,
    row_labs: list[str],
    col_labs: list[str],
    left_grid: int = 140,
    color_mode: str = "global",
) -> dict[str, Any] | None:
    rows, cols, cell = _matriz_pct(df, row_col=row_col, row_labs=row_labs, col_labs=col_labs)
    if not rows:
        return None
    rows = _ordenar_filas_por_riesgo(rows, cols, cell)

    row_rng: dict[str, tuple[float, float]] = {}
    for r in rows:
        vals = [cell[(r, c)][0] for c in cols if (r, c) in cell and cell[(r, c)][2]]
        if vals:
            row_rng[r] = (min(vals), max(vals))

    globales = [cell[k][0] for k, v in cell.items() if v[2]]
    g_lo = min(globales) if globales else 0.0
    g_hi = max(globales) if globales else 1.0
    g_span = g_hi - g_lo

    por_fila = color_mode == "fila"
    tip_insuf = "Muestra insuficiente en este periodo"
    data: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        lo_r, hi_r = row_rng.get(row, (0.0, 1.0))
        span_r = hi_r - lo_r
        for j, col in enumerate(cols):
            if (row, col) not in cell or not cell[(row, col)][2]:
                data.append(_celda_insuficiente(j=j, i=i, tip=tip_insuf))
                continue
            pct, n, _fiable = cell[(row, col)]
            if por_fila:
                color_v = 50.0 if span_r < 0.5 else round(100.0 * (pct - lo_r) / span_r, 1)
            else:
                color_v = 50.0 if g_span < 0.5 else round(100.0 * (pct - g_lo) / g_span, 1)
            data.append(
                _celda_pct(j=j, i=i, pct=pct, n=n, color_v=color_v, row=row, col=col)
            )

    vm_text = (
        ["Alto en la fila", "Bajo en la fila"]
        if por_fila
        else ["Alto global", "Bajo global"]
    )
    return _base_opts(
        tooltip={"position": "top", "trigger": "item"},
        grid={"left": left_grid, "right": 40, "top": 36, "bottom": 88},
        xAxis={
            "type": "category",
            "data": cols,
            "axisLabel": {"rotate": 40, "fontSize": 9, "fontWeight": 600},
            "splitArea": {"show": False},
        },
        yAxis={
            "type": "category",
            "data": [str(r)[:28] for r in rows],
            "splitArea": {"show": False},
            "inverse": True,
        },
        visualMap={
            "show": True,
            "min": 0,
            "max": 100,
            "calculable": False,
            "orient": "horizontal",
            "left": "center",
            "bottom": 0,
            "text": vm_text,
            "inRange": {"color": list(_HEAT_PALETTE)},
            "seriesIndex": -1,
        },
        series=[
            {
                "type": "heatmap",
                "data": data,
                "label": {"show": True},
                "itemStyle": {"borderColor": "#FFFFFF", "borderWidth": 0.5},
                "emphasis": {"itemStyle": {"shadowBlur": 8, "shadowColor": "rgba(0,0,0,0.25)"}},
            }
        ],
    )


def _opts_heatmap_q_uso(
    df: pd.DataFrame,
    *,
    color_mode: str = "global",
) -> dict[str, Any] | None:
    if "uso_n" not in df.columns:
        return None
    candidatos = df["uso_n"].value_counts().head(12).index.tolist()
    sub = df.loc[df["uso_n"].isin(candidatos)].copy()
    if sub.empty:
        return None
    bandas = _labs_presentes(sub, excluir_sin_anio=True)
    return _heatmap_pct_adv(
        sub,
        row_col="uso_n",
        row_labs=candidatos,
        col_labs=bandas,
        left_grid=150,
        color_mode=color_mode,
    )


def _estados_con_cobertura(df: pd.DataFrame, *, max_estados: int = 8) -> list[str]:
    """Solo estados con volumen y varias bandas de pisos fiables."""
    ban = {
        "",
        "NAN",
        "nan",
        "(SIN ESTADO)",
        "(sin estado)",
        "SIN EVALUAR",
        "Sin Evaluar",
    }
    s = df["estado_n"].dropna().astype(str)
    s = s.loc[~s.isin(ban)]
    bandas = _labs_presentes(df, excluir_sin_anio=True)
    scored: list[tuple[int, int, str]] = []
    for est, n_tot in s.value_counts().items():
        if int(n_tot) < MIN_N_FILA:
            continue
        valid = 0
        for b in bandas:
            n = int(((df["estado_n"].astype(str) == est) & (df["quinquenio"] == b)).sum())
            if n >= MIN_N_CELDA:
                valid += 1
        if valid >= MIN_CELDAS_FILA:
            scored.append((int(n_tot), valid, str(est)))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [est for _, _, est in scored[:max_estados]]


def _opts_heatmap_q_estado(
    df: pd.DataFrame,
    *,
    color_mode: str = "global",
) -> dict[str, Any] | None:
    top_est = _estados_con_cobertura(df, max_estados=8)
    if not top_est:
        return None
    sub = df.loc[df["estado_n"].isin(top_est)].copy()
    bandas = _labs_presentes(sub, excluir_sin_anio=True)
    return _heatmap_pct_adv(
        sub,
        row_col="estado_n",
        row_labs=top_est,
        col_labs=bandas,
        left_grid=140,
        color_mode=color_mode,
    )


def _render_tab_anio_uso(work: pd.DataFrame) -> None:
    dff, _ = _aplicar_filtros_dimension(work, key_prefix="dim_pis_uso")
    if dff.empty:
        st.warning("El filtro no deja filas. Amplíe la selección.")
        return

    t1, t2 = st.columns([0.82, 0.18])
    with t1:
        st.markdown("##### % Rojo + pérdida total · banda de altura × uso agrupado")
        st.caption(
            "Cada casilla: de cada 100 inspecciones, cuántas quedaron en rojo o pérdida total."
        )
    with t2:
        with st.popover("ℹ️ Criterios"):
            st.markdown(
                f"- Solo usos con **≥{MIN_N_FILA}** inspecciones\n"
                f"- Al menos **{MIN_CELDAS_FILA}** bandas con **n≥{MIN_N_CELDA}**\n"
                f"- Celdas grises: muestra insuficiente en ese periodo\n"
                f"- Filas ordenadas de mayor a menor riesgo promedio\n"
                f"- Escala **Global**: rojo máximo = celda más alta de toda la tabla\n"
                f"- Escala **Por fila**: rojo máximo = máximo de cada uso"
            )

    modo_lbl = st.radio(
        "Escala de color",
        ["Global", "Por fila"],
        horizontal=True,
        index=0,
        key="dim_pis_uso_heat_scale_v2",
        help=(
            "Global (recomendado): compara todas las celdas. "
            "Por fila: compara bandas dentro de cada uso."
        ),
    )
    color_mode = "global" if modo_lbl == "Global" else "fila"

    heat = _opts_heatmap_q_uso(dff, color_mode=color_mode)
    if heat:
        st_echarts(heat, height="440px", key=f"dim-p-uso-{color_mode}")
    else:
        st.info("Sin usos con cobertura suficiente en este corte.")


def _render_tab_anio_ubicacion(work: pd.DataFrame) -> None:
    """Matriz pisos × estado; filtros solo uso y material (la ubicación es el eje del gráfico)."""
    dff, _ = _aplicar_filtros_dimension(
        work,
        key_prefix="dim_pis_ubi",
        titulo="Filtros de este análisis (sin territorio)",
        con_territorio=False,
    )
    if dff.empty:
        st.warning("El filtro no deja filas. Amplíe la selección.")
        return

    t1, t2 = st.columns([0.82, 0.18])
    with t1:
        st.markdown("##### % Rojo + pérdida total · banda de altura × estado")
        st.caption(
            "Cada casilla: de cada 100 inspecciones, cuántas quedaron en rojo o pérdida total."
        )
    with t2:
        with st.popover("ℹ️ Criterios"):
            st.markdown(
                f"- Solo estados con **≥{MIN_N_FILA}** inspecciones\n"
                f"- Al menos **{MIN_CELDAS_FILA}** bandas con **n≥{MIN_N_CELDA}**\n"
                f"- Celdas grises: muestra insuficiente en ese periodo\n"
                f"- Estados ordenados de mayor a menor riesgo promedio\n"
                f"- Uso y material acotan el corte sin filtrar por territorio\n"
                f"- Escala **Global**: rojo máximo = celda más alta de toda la tabla\n"
                f"- Escala **Por fila**: rojo máximo = máximo de cada estado"
            )

    modo_lbl = st.radio(
        "Escala de color",
        ["Global", "Por fila"],
        horizontal=True,
        index=0,
        key="dim_pis_ubi_heat_scale_v2",
        help=(
            "Global (recomendado): compara todas las celdas. "
            "Por fila: compara bandas dentro de cada estado."
        ),
    )
    color_mode = "global" if modo_lbl == "Global" else "fila"

    heat = _opts_heatmap_q_estado(dff, color_mode=color_mode)
    if heat:
        st_echarts(heat, height="440px", key=f"dim-p-est-{color_mode}")
    else:
        st.info("Sin estados con cobertura suficiente.")
    with st.expander("Detalle tabular por estado y banda de altura", expanded=False):
        ests = _estados_con_cobertura(dff)
        g = (
            dff.loc[dff["estado_n"].isin(ests)]
            .assign(adv=lambda d: d["etiqueta_n"].isin(["ROJO", "NEGRO"]))
            .groupby(["estado_n", "quinquenio"], dropna=False)
            .agg(n=("etiqueta_n", "size"), adv=("adv", "sum"))
            .reset_index()
        )
        g["% Rojo+pérdida total"] = (100.0 * g["adv"] / g["n"].clip(lower=1)).round(1)
        g["fiable"] = g["n"] >= MIN_N_CELDA
        st.dataframe(
            g.sort_values(["estado_n", "quinquenio"]),
            use_container_width=True,
            hide_index=True,
        )


def render_dimension_pisos(df: pd.DataFrame) -> None:
    """Subpestañas: bandas de altura (resonancia) vs daño."""
    render_section(
        "Dimensión · Número de pisos",
        "¿La altura se asocia con mayor daño? "
        "Análisis por **bandas de altura** (rigidez/flexibilidad), no piso a piso: "
        "el daño sísmico suele concentrarse en franjas intermedias (resonancia), no en una recta. "
        "Variables secundarias: uso, material y ubicación.",
    )
    work = _prep(df)
    if work.empty:
        st.warning("Sin filas tras filtros.")
        return

    n = len(work)
    con_banda = int(work["quinquenio"].ne("Sin dato").sum())
    rn = int(work["etiqueta_n"].isin(["ROJO", "NEGRO"]).sum())
    render_kpi_strip(
        [
            {"label": "Inspecciones", "value": fmt_es_int(n)},
            {"label": "Con banda de altura", "value": fmt_es_int(con_banda)},
            {"label": "% Rojo + pérdida total", "value": f"{100.0 * rn / max(n, 1):.1f} %", "tone": "warning"},
        ]
    )

    s1, s2, s3, s4 = st.tabs(
        [
            "Panorama por banda de altura",
            "Altura vs daño (resonancia)",
            "Altura × uso",
            "Altura × ubicación",
        ]
    )

    with s1:
        _render_tab_panorama(work)

    with s2:
        _render_tab_anio_vs_dano(work)

    with s3:
        _render_tab_anio_uso(work)

    with s4:
        _render_tab_anio_ubicacion(work)
