"""Vista ejecutiva: semáforo/tortas + elementos ANIH + dimensiones."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from streamlit_echarts import JsCode, st_echarts

from anih_logic import (
    RESUMEN_METODO,
    enriquecer_riesgos_anih,
    metricas_flujo_inspeccion,
    resumen_elementos_abc,
    texto_sintesis_flujo,
)
from charts_habitable import ETIQUETA_COLORS, NAVY, STEEL, _base_opts
from export_utils import fmt_es_int
from filters_analisis import aplicar_filtros_analisis, render_filtros_analisis
from process_habitable import ETIQUETAS
from ui_theme import render_kpi_strip, render_section

CORTE_ESTADO = "CARABOBO"
MIN_INSPECCIONES_TORTA = 200
# Estados con torta propia (orden por volumen); el resto se agrega después de Aragua
ESTADOS_DETALLE_HASTA = "ARAGUA"


def _filtrar_estados_min(ct: pd.DataFrame, *, minimo: int = MIN_INSPECCIONES_TORTA) -> pd.DataFrame:
    """Solo estados con volumen suficiente para torta legible."""
    if ct.empty or "__t" not in ct.columns:
        return ct
    return ct.loc[ct["__t"] > minimo].copy()


def _partir_detalle_y_resto(ct: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Detalle hasta Aragua (inclusive) + agregado del resto del país."""
    if ct.empty:
        return ct, ct.iloc[0:0].copy()
    full = ct.copy()
    estados = full.index.astype(str).tolist()
    if ESTADOS_DETALLE_HASTA in estados:
        i = estados.index(ESTADOS_DETALLE_HASTA)
        detalle = full.iloc[: i + 1].copy()
        resto = full.iloc[i + 1 :].copy()
    else:
        # Fallback: top 5 vs resto
        detalle = full.iloc[:5].copy()
        resto = full.iloc[5:].copy()
    if resto.empty:
        return detalle, resto
    # Una sola fila agregada
    agg = resto.drop(columns="__t", errors="ignore").sum()
    total = int(agg.sum())
    row = {**{e: int(agg.get(e, 0)) for e in ETIQUETAS}, "__t": total}
    resto_agg = pd.DataFrame([row], index=["RESTO DEL PAÍS"])
    return detalle, resto_agg


def _sem_counts(df: pd.DataFrame) -> dict[str, int]:
    counts = df["etiqueta_n"].value_counts()
    return {e: int(counts.get(e, 0)) for e in ETIQUETAS}


def _crosstab_estados(df: pd.DataFrame) -> pd.DataFrame:
    sub = df.loc[df["etiqueta_n"].isin(ETIQUETAS)].copy()
    sub = sub.loc[~sub["estado_n"].isin({"(SIN ESTADO)", "(sin estado)", "NAN", ""})]
    if sub.empty:
        return pd.DataFrame()
    ct = pd.crosstab(sub["estado_n"], sub["etiqueta_n"])
    for e in ETIQUETAS:
        if e not in ct.columns:
            ct[e] = 0
    ct = ct.reindex(columns=list(ETIQUETAS), fill_value=0)
    ct["__t"] = ct.sum(axis=1)
    return ct.sort_values("__t", ascending=False)


def _partir_en_carabobo(ct: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if ct.empty:
        return ct, ct
    estados = ct.index.astype(str).tolist()
    if CORTE_ESTADO in estados:
        i = estados.index(CORTE_ESTADO)
        return ct.iloc[:i], ct.iloc[i:]
    return ct.iloc[:3], ct.iloc[3:]


def _inject_css() -> None:
    st.markdown(
        """
        <style>
        .nac-shell {
            background: #fff;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 0.75rem 0.9rem 0.4rem;
            margin: 0.4rem 0 1rem 0;
            box-shadow: 0 1px 3px rgba(12,35,64,0.06);
        }
        .nac-shell .nac-title {
            font-size: 0.8rem;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: #64748B;
            margin-bottom: 0.25rem;
        }
        iframe[title="streamlit_ficha_estado"] {
            margin-bottom: 0.35rem;
        }
        /* Refuerzo local: pestañas como botones redondeados */
        .stTabs [data-baseweb="tab-list"],
        [role="tablist"] {
            gap: 0.75rem !important;
            background: transparent !important;
            border: none !important;
            flex-wrap: wrap !important;
        }
        .stTabs [data-baseweb="tab"],
        button[data-baseweb="tab"],
        [role="tablist"] [role="tab"] {
            background: #fff !important;
            border: 1.5px solid #CBD5E1 !important;
            border-radius: 18px !important;
            overflow: hidden !important;
            padding: 0.7rem 1.15rem !important;
            font-weight: 700 !important;
            color: #0C2340 !important;
            box-shadow: 0 1px 3px rgba(12,35,64,0.07) !important;
        }
        .stTabs [aria-selected="true"],
        button[data-baseweb="tab"][aria-selected="true"],
        [role="tablist"] [role="tab"][aria-selected="true"] {
            background: #0C2340 !important;
            color: #fff !important;
            border-color: #0C2340 !important;
            border-radius: 18px !important;
            box-shadow: 0 4px 12px rgba(12,35,64,0.24) !important;
        }
        .stTabs [aria-selected="true"] p,
        .stTabs [aria-selected="true"] span,
        button[data-baseweb="tab"][aria-selected="true"] p,
        button[data-baseweb="tab"][aria-selected="true"] span,
        [role="tablist"] [role="tab"][aria-selected="true"] p,
        [role="tablist"] [role="tab"][aria-selected="true"] span {
            color: #fff !important;
        }
        .stTabs [data-baseweb="tab-highlight"],
        .stTabs [data-baseweb="tab-border"] {
            display: none !important;
        }
        .stTabs [data-baseweb="tab-panel"] {
            border: 1px solid #E2E8F0 !important;
            border-radius: 16px !important;
            padding: 1rem !important;
            background: #fff !important;
        }
        /* Pastillas de sección (Análisis dimensional, etc.) */
        div[data-testid="stMain"] div[class*="st-key-ad_pill_"] button,
        div[data-testid="stMain"] div[class*="st-key-dep_"] button {
            border-radius: 18px !important;
            min-height: 2.85rem !important;
            font-weight: 700 !important;
            border-width: 1.5px !important;
        }
        div[data-testid="stMain"] div[class*="st-key-ad_pill_"] button[kind="secondary"],
        div[data-testid="stMain"] div[class*="st-key-ad_pill_"] button[data-testid="baseButton-secondary"] {
            background: #FFFFFF !important;
            color: #0C2340 !important;
            border: 1.5px solid #CBD5E1 !important;
        }
        div[data-testid="stMain"] div[class*="st-key-ad_pill_"] button[kind="primary"],
        div[data-testid="stMain"] div[class*="st-key-ad_pill_"] button[data-testid="baseButton-primary"] {
            background: #0C2340 !important;
            color: #FFFFFF !important;
            border: 1.5px solid #0C2340 !important;
            box-shadow: 0 4px 12px rgba(12,35,64,0.24) !important;
        }
        /* Radios horizontales → pastillas */
        div[data-testid="stMain"] div[role="radiogroup"] {
            display: flex !important;
            flex-wrap: wrap !important;
            gap: 0.65rem !important;
            background: transparent !important;
            border: none !important;
        }
        div[data-testid="stMain"] div[role="radiogroup"] label {
            background: #FFFFFF !important;
            border: 1.5px solid #CBD5E1 !important;
            border-radius: 18px !important;
            padding: 0.55rem 1.05rem !important;
            margin: 0 !important;
            font-weight: 700 !important;
            color: #0C2340 !important;
            box-shadow: 0 1px 3px rgba(12,35,64,0.07) !important;
        }
        div[data-testid="stMain"] div[role="radiogroup"] label:has(input:checked) {
            background: #0C2340 !important;
            color: #FFFFFF !important;
            border-color: #0C2340 !important;
            box-shadow: 0 4px 12px rgba(12,35,64,0.24) !important;
        }
        div[data-testid="stMain"] div[role="radiogroup"] label:has(input:checked) p,
        div[data-testid="stMain"] div[role="radiogroup"] label:has(input:checked) span {
            color: #FFFFFF !important;
        }
        div[data-testid="stMain"] div[role="radiogroup"] label [data-testid="stMarkdownContainer"] p {
            font-weight: 700 !important;
        }
        div[data-testid="stMain"] div[role="radiogroup"] label > div:first-child {
            display: none !important; /* oculta el círculo del radio */
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _html_ficha_estado(
    estado: str,
    *,
    total_est: int,
    pct_nac: float,
    sem: dict[str, int],
    chart_id: str,
) -> str:
    """Ficha única (texto + torta) de tamaño fijo."""
    total_sem = max(sum(int(sem.get(e, 0)) for e in ETIQUETAS), 1)
    pill_styles = {
        "VERDE": ("#DCFCE7", "#14532D", "#86EFAC"),
        "AMARILLO": ("#FEF9C3", "#713F12", "#FDE047"),
        "ROJO": ("#FEE2E2", "#7F1D1D", "#FCA5A5"),
        "NEGRO": ("#E2E8F0", "#0F172A", "#94A3B8"),
    }
    pills = []
    for e in ETIQUETAS:
        n = int(sem.get(e, 0))
        pct = 100.0 * n / total_sem
        bg, fg, bd = pill_styles[e]
        pills.append(
            f'<div style="background:{bg};color:{fg};border:1px solid {bd};'
            f'border-radius:8px;padding:6px 4px;text-align:center;'
            f'font-size:11px;font-weight:700;line-height:1.25">'
            f"{fmt_es_int(n)} · {pct:.1f}%</div>"
        )
    pie_data = [
        {"name": e, "value": int(sem.get(e, 0)), "itemStyle": {"color": ETIQUETA_COLORS[e]}}
        for e in ETIQUETAS
        if int(sem.get(e, 0)) > 0
    ]
    opt = {
        "animation": True,
        "animationDuration": 800,
        "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
        "series": [
            {
                "type": "pie",
                "radius": ["38%", "68%"],
                "center": ["50%", "52%"],
                "animationType": "expansion",
                "itemStyle": {"borderRadius": 4, "borderColor": "#fff", "borderWidth": 2},
                "label": {"show": False},
                "labelLine": {"show": False},
                "data": pie_data,
            }
        ],
    }
    opt_json = json.dumps(opt, ensure_ascii=False)
    return f"""
<!DOCTYPE html>
<html><head>
<meta charset="utf-8"/>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"></script>
<style>
  html, body {{ margin:0; padding:0; background:transparent; font-family:'Source Sans 3',Segoe UI,sans-serif; }}
  .card {{
    height: 392px;
    box-sizing: border-box;
    background:#fff;
    border:1px solid #E2E8F0;
    border-radius:12px;
    padding:14px 14px 8px;
    box-shadow:0 1px 3px rgba(12,35,64,0.06);
    display:flex;
    flex-direction:column;
  }}
  .name {{ margin:0; font-size:15px; font-weight:700; color:#0C2340; letter-spacing:0.02em; }}
  .n {{ margin:8px 0 2px; font-size:15px; font-weight:700; color:#0F172A; }}
  .pct {{ margin:0 0 10px; font-size:12px; font-weight:600; color:#64748B; }}
  .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:6px; }}
  .chart {{ flex:1; min-height:190px; width:100%; margin-top:8px; }}
</style>
</head><body>
<div class="card">
  <p class="name">{estado}</p>
  <p class="n">{fmt_es_int(total_est)} inspecciones</p>
  <p class="pct">{pct_nac:.1f}% del total nacional</p>
  <div class="grid">{"".join(pills)}</div>
  <div class="chart" id="{chart_id}"></div>
</div>
<script>
  var el = document.getElementById("{chart_id}");
  var chart = echarts.init(el);
  chart.setOption({opt_json});
  window.addEventListener('resize', function() {{ chart.resize(); }});
</script>
</body></html>
"""


def _render_tortas_estados(ct: pd.DataFrame, *, n_nacional: int, key_prefix: str) -> None:
    """Fichas del mismo tamaño: valores + torta unidos en un solo bloque."""
    if ct.empty:
        return
    work = ct.drop(columns="__t", errors="ignore")
    estados = work.index.astype(str).tolist()
    FICHA_H = 410

    for i in range(0, len(estados), 3):
        chunk = list(estados[i : i + 3])
        while len(chunk) < 3:
            chunk.append("")
        cols = st.columns(3, gap="medium")
        for col, estado in zip(cols, chunk, strict=True):
            with col:
                if not estado:
                    components.html(
                        "<div style='height:392px'></div>",
                        height=FICHA_H,
                        scrolling=False,
                    )
                    continue
                total_est = int(ct.loc[estado, "__t"])
                pct_nac = 100.0 * total_est / max(n_nacional, 1)
                sem = {e: int(work.loc[estado, e]) for e in ETIQUETAS}
                cid = f"{key_prefix}_{estado}".replace(" ", "_").lower()
                html = _html_ficha_estado(
                    estado,
                    total_est=total_est,
                    pct_nac=pct_nac,
                    sem=sem,
                    chart_id=cid,
                )
                components.html(html, height=FICHA_H, scrolling=False)


def _opts_semaforo_nacional(sem: dict[str, int], *, total: int) -> dict[str, Any]:
    """Barras nacionales con total y % encima de cada color."""
    labels = list(ETIQUETAS)
    data = []
    for lab in labels:
        v = int(sem.get(lab, 0))
        pct = 100.0 * v / max(total, 1)
        data.append(
            {
                "value": v,
                "itemStyle": {"color": ETIQUETA_COLORS[lab], "borderRadius": [6, 6, 0, 0]},
                "label": {
                    "show": True,
                    "position": "top",
                    "formatter": f"{fmt_es_int(v)}\n{pct:.1f}%",
                    "fontSize": 12,
                    "fontWeight": 700,
                    "color": "#0F172A",
                    "lineHeight": 16,
                },
            }
        )
    return _base_opts(
        animation=True,
        animationDuration=900,
        animationEasing="cubicOut",
        tooltip={"trigger": "axis", "formatter": "{b}: {c}"},
        legend={"show": False},
        grid={"left": 48, "right": 24, "top": 56, "bottom": 36},
        xAxis={
            "type": "category",
            "data": labels,
            "axisLabel": {"color": "#64748B", "fontWeight": 600, "fontSize": 12},
            "axisTick": {"show": False},
            "axisLine": {"lineStyle": {"color": "#E2E8F0"}},
        },
        yAxis={
            "type": "value",
            "splitLine": {"lineStyle": {"color": "#F1F5F9"}},
            "axisLabel": {"color": "#94A3B8"},
        },
        series=[{"type": "bar", "data": data, "barMaxWidth": 56}],
    )


def _opts_barras_cobertura(resumen: pd.DataFrame) -> dict[str, Any] | None:
    """% con dato vs % sin dato por bloque (lee la cobertura, no el riesgo)."""
    if resumen.empty:
        return None
    labs = resumen["Bloque planilla"].tolist()
    con, sin = [], []
    for _, row in resumen.iterrows():
        a, b, c = int(row["A"]), int(row["B"]), int(row["C"])
        sd = int(row["Sin dato"])
        tot = max(a + b + c + sd, 1)
        con.append(round(100.0 * (a + b + c) / tot, 1))
        sin.append(round(100.0 * sd / tot, 1))
    return _base_opts(
        animationDuration=800,
        tooltip={"trigger": "axis", "axisPointer": {"type": "shadow"}},
        legend={"top": 0},
        grid={"left": 16, "right": 24, "top": 40, "bottom": 70, "containLabel": True},
        xAxis={
            "type": "category",
            "data": labs,
            "axisLabel": {"rotate": 18, "fontSize": 10},
        },
        yAxis={"type": "value", "max": 100, "name": "%", "axisLabel": {"formatter": "{value}%"}},
        series=[
            {
                "name": "% con dato",
                "type": "bar",
                "stack": "cob",
                "itemStyle": {"color": STEEL},
                "data": con,
                "label": {"show": True, "formatter": "{c}%", "fontSize": 10},
            },
            {
                "name": "% sin dato",
                "type": "bar",
                "stack": "cob",
                "itemStyle": {"color": "#CBD5E1"},
                "data": sin,
                "label": {"show": True, "formatter": "{c}%", "fontSize": 10, "color": "#334155"},
            },
        ],
    )


def _opts_barras_riesgo_alto(resumen: pd.DataFrame) -> dict[str, Any] | None:
    """% B y % C entre evaluados por bloque — lectura de presión de riesgo."""
    if resumen.empty:
        return None
    labs = resumen["Bloque planilla"].tolist()[::-1]  # horizontal: más legible de arriba a abajo
    pct_b, pct_c, pct_a = [], [], []
    for i in range(len(resumen) - 1, -1, -1):
        row = resumen.iloc[i]
        eval_n = max(int(row["A"]) + int(row["B"]) + int(row["C"]), 1)
        pct_a.append(round(100.0 * int(row["A"]) / eval_n, 1))
        pct_b.append(round(100.0 * int(row["B"]) / eval_n, 1))
        pct_c.append(round(100.0 * int(row["C"]) / eval_n, 1))
    return _base_opts(
        animationDuration=800,
        tooltip={"trigger": "axis", "axisPointer": {"type": "shadow"}},
        legend={"top": 0},
        grid={"left": 16, "right": 48, "top": 40, "bottom": 24, "containLabel": True},
        xAxis={"type": "value", "max": 100, "axisLabel": {"formatter": "{value}%"}},
        yAxis={"type": "category", "data": labs, "axisLabel": {"fontSize": 11}},
        series=[
            {
                "name": "A · Bajo",
                "type": "bar",
                "stack": "p",
                "itemStyle": {"color": "#22C55E"},
                "data": pct_a,
            },
            {
                "name": "B · Medio",
                "type": "bar",
                "stack": "p",
                "itemStyle": {"color": "#FACC15"},
                "data": pct_b,
            },
            {
                "name": "C · Alto",
                "type": "bar",
                "stack": "p",
                "itemStyle": {"color": "#EF4444"},
                "data": pct_c,
                "label": {
                    "show": True,
                    "position": "right",
                    "formatter": "",  # labels on stack are noisy; tooltip suffices
                },
            },
        ],
    )


def _opts_barras_pct_c(resumen: pd.DataFrame) -> dict[str, Any] | None:
    """Solo % C (alto) entre evaluados — señal de alerta por bloque."""
    if resumen.empty:
        return None
    rows = []
    for i in range(len(resumen)):
        row = resumen.iloc[i]
        eval_n = max(int(row["A"]) + int(row["B"]) + int(row["C"]), 1)
        rows.append(
            {
                "bloque": row["Bloque planilla"],
                "pct_c": round(100.0 * int(row["C"]) / eval_n, 1),
                "n_eval": int(row["A"]) + int(row["B"]) + int(row["C"]),
            }
        )
    rows = sorted(rows, key=lambda r: r["pct_c"])
    return _base_opts(
        animationDuration=800,
        tooltip={
            "trigger": "axis",
            "formatter": "{b}<br/>Riesgo C: {c}% de evaluados",
        },
        legend={"show": False},
        grid={"left": 16, "right": 56, "top": 28, "bottom": 24, "containLabel": True},
        xAxis={"type": "value", "max": 100, "name": "% C", "axisLabel": {"formatter": "{value}%"}},
        yAxis={
            "type": "category",
            "data": [r["bloque"] for r in rows],
            "axisLabel": {"fontSize": 11},
        },
        series=[
            {
                "type": "bar",
                "data": [
                    {
                        "value": r["pct_c"],
                        "itemStyle": {"color": "#EF4444", "borderRadius": [0, 6, 6, 0]},
                    }
                    for r in rows
                ],
                "barMaxWidth": 28,
                "label": {
                    "show": True,
                    "position": "right",
                    "formatter": "{c}%",
                    "fontWeight": 700,
                    "color": "#0F172A",
                },
            }
        ],
    )


def _opts_barras_abc_evaluados(resumen: pd.DataFrame) -> dict[str, Any] | None:
    """100% apilado A/B/C solo entre evaluados (sin la barra gris)."""
    if resumen.empty:
        return None
    labs = resumen["Bloque planilla"].tolist()
    colors = {"A": "#22C55E", "B": "#FACC15", "C": "#EF4444"}
    series = []
    for nivel in ("A", "B", "C"):
        vals = []
        for i in range(len(resumen)):
            row = resumen.iloc[i]
            eval_n = max(int(row["A"]) + int(row["B"]) + int(row["C"]), 1)
            vals.append(round(100.0 * int(row[nivel]) / eval_n, 1))
        series.append(
            {
                "name": nivel,
                "type": "bar",
                "stack": "pct",
                "itemStyle": {"color": colors[nivel]},
                "data": vals,
            }
        )
    return _base_opts(
        animationDuration=800,
        tooltip={"trigger": "axis"},
        legend={"top": 0},
        grid={"left": 16, "right": 24, "top": 40, "bottom": 70, "containLabel": True},
        xAxis={"type": "category", "data": labs, "axisLabel": {"rotate": 18, "fontSize": 10}},
        yAxis={"type": "value", "max": 100, "name": "% evaluados", "axisLabel": {"formatter": "{value}%"}},
        series=series,
    )


@st.cache_data(show_spinner="Derivando riesgos ANIH (planilla V.8)…")
def _anih_cached(df: pd.DataFrame) -> pd.DataFrame:
    return enriquecer_riesgos_anih(df)


def _tab_semaforo_tortas(df: pd.DataFrame, summary: dict[str, Any]) -> None:
    n = len(df)
    sem = _sem_counts(df)
    render_kpi_strip(
        [
            {"label": "Inspecciones", "value": fmt_es_int(n)},
            {
                "label": "% Verde",
                "value": f"{100.0 * sem['VERDE'] / max(n, 1):.1f} %",
                "tone": "success",
                "hint": fmt_es_int(sem["VERDE"]),
            },
            {
                "label": "% Amarillo",
                "value": f"{100.0 * sem['AMARILLO'] / max(n, 1):.1f} %",
                "tone": "flag",
                "hint": fmt_es_int(sem["AMARILLO"]),
            },
            {
                "label": "% Rojo",
                "value": f"{100.0 * sem['ROJO'] / max(n, 1):.1f} %",
                "tone": "warning",
                "hint": fmt_es_int(sem["ROJO"]),
            },
            {
                "label": "% Pérdida total",
                "value": f"{100.0 * sem['NEGRO'] / max(n, 1):.1f} %",
                "tone": "muted",
                "hint": fmt_es_int(sem["NEGRO"]),
            },
        ]
    )
    st.caption(
        f"Fuente: **{summary.get('fuente', '—')}** · "
        f"Procesado: **{summary.get('corte_generado_en', '—')}**"
    )

    st.markdown(
        '<div class="nac-shell"><div class="nac-title">Distribución nacional</div></div>',
        unsafe_allow_html=True,
    )
    st_echarts(_opts_semaforo_nacional(sem, total=n), height="300px", key="exe-sem-bar")

    # Todas las filas de estado (sin filtrar por 200) para armar el resto agregado;
    # el detalle muestra los de mayor volumen hasta Aragua.
    ct_all = _crosstab_estados(df)
    detalle, resto = _partir_detalle_y_resto(ct_all)
    # Mostrar detalle + resto en una sola grilla
    combo = pd.concat([detalle, resto]) if not resto.empty else detalle
    st.caption("Detalle por estado (hasta Aragua) y resto del país agrupado.")
    _render_tortas_estados(combo, n_nacional=n, key_prefix="torta")


def _opts_sankey_flujo(m: dict[str, Any]) -> dict[str, Any] | None:
    """Sankey del protocolo con n absoluto y % (sobre iniciadas) en nodos y flujos."""
    n = int(m["n"])
    if n <= 0:
        return None
    n_ext = int(m["n_descarte_ext"])
    n_p3 = int(m["n_paso3"])
    n_sev = int(m["n_descarte_sev"])
    n_p4 = int(m["n_paso4"])
    n_sin = int(m["n_sin_avance"])

    def _pct(x: int) -> float:
        return round(100.0 * x / max(n, 1), 1)

    def _node(name: str, n_node: int) -> dict[str, Any]:
        return {
            "name": name,
            "label": {
                "show": True,
                "formatter": f"{name}\n{fmt_es_int(n_node)} ({_pct(n_node)}%)",
                "fontSize": 11,
                "fontWeight": 600,
                "color": "#0F172A",
                "lineHeight": 16,
            },
        }

    def _link(src: str, tgt: str, n_link: int) -> dict[str, Any]:
        return {
            "source": src,
            "target": tgt,
            "value": n_link,
            "pct": _pct(n_link),
        }

    n_iniciadas = n
    nodes = [
        _node("Iniciadas · Paso 2 (riesgo externo)", n_iniciadas),
        _node("Descarte · riesgo externo C", n_ext),
        _node("Paso 3 · daño severo", n_p3),
        _node("Descarte · daño severo C", n_sev),
        _node("Paso 4 · daño moderado", n_p4),
        _node("Sin avance interno documentado", n_sin),
    ]
    links: list[dict[str, Any]] = []
    if n_ext > 0:
        links.append(
            _link(
                "Iniciadas · Paso 2 (riesgo externo)",
                "Descarte · riesgo externo C",
                n_ext,
            )
        )
    if n_p3 > 0:
        links.append(
            _link(
                "Iniciadas · Paso 2 (riesgo externo)",
                "Paso 3 · daño severo",
                n_p3,
            )
        )
    if n_sev > 0:
        links.append(_link("Paso 3 · daño severo", "Descarte · daño severo C", n_sev))
    if n_p4 > 0:
        links.append(_link("Paso 3 · daño severo", "Paso 4 · daño moderado", n_p4))
    if n_sin > 0:
        links.append(
            _link("Paso 3 · daño severo", "Sin avance interno documentado", n_sin)
        )
    if not links:
        return None

    edge_fmt = JsCode(
        """function (params) {
            var v = (params && params.value != null) ? params.value : 0;
            var pct = (params && params.data && params.data.pct != null)
                ? params.data.pct : null;
            var abs = Number(v).toLocaleString('es-VE');
            if (pct == null) { return abs; }
            return abs + ' (' + pct + '%)';
        }"""
    )
    tip_fmt = JsCode(
        """function (params) {
            if (!params) { return ''; }
            if (params.dataType === 'edge' || (params.data && params.data.source != null)) {
                var v = params.data.value;
                var pct = params.data.pct;
                var abs = Number(v).toLocaleString('es-VE');
                return params.data.source + ' → ' + params.data.target
                    + '<br/><b>' + abs + '</b> inspecciones (' + pct + '% del total)';
            }
            var name = params.name || '';
            return name;
        }"""
    )

    return _base_opts(
        tooltip={"trigger": "item", "triggerOn": "mousemove", "formatter": tip_fmt},
        series=[
            {
                "type": "sankey",
                "emphasis": {"focus": "adjacency"},
                "nodeAlign": "left",
                "orient": "horizontal",
                "nodeGap": 14,
                "nodeWidth": 18,
                "data": nodes,
                "links": links,
                "lineStyle": {"color": "gradient", "curveness": 0.45, "opacity": 0.5},
                "label": {"show": True},
                "edgeLabel": {
                    "show": True,
                    "fontSize": 11,
                    "fontWeight": 700,
                    "color": "#0F172A",
                    "formatter": edge_fmt,
                },
                "itemStyle": {"borderWidth": 0},
                "levels": [
                    {},
                    {"depth": 0, "itemStyle": {"color": NAVY}},
                    {"depth": 1, "itemStyle": {"color": STEEL}},
                    {"depth": 2, "itemStyle": {"color": "#B45309"}},
                ],
            }
        ],
    )


def _opts_funnel_flujo(m: dict[str, Any]) -> dict[str, Any] | None:
    """Embudo de la rama que avanza (complemento visual del Sankey)."""
    n = int(m["n"])
    if n <= 0:
        return None
    data = [
        {"value": n, "name": "Iniciadas (Paso 2)"},
        {"value": int(m["n_paso3"]), "name": "Continúan a Paso 3"},
        {"value": int(m["n_paso4"]), "name": "Requieren Paso 4"},
    ]
    return _base_opts(
        tooltip={"trigger": "item", "formatter": "{b}<br/>n = {c}"},
        series=[
            {
                "type": "funnel",
                "left": "12%",
                "width": "76%",
                "min": 0,
                "max": n,
                "minSize": "18%",
                "maxSize": "100%",
                "sort": "descending",
                "gap": 4,
                "label": {
                    "show": True,
                    "position": "inside",
                    "formatter": "{b}\n{c}",
                    "fontSize": 11,
                    "fontWeight": 700,
                    "color": "#FFFFFF",
                },
                "itemStyle": {"borderColor": "#FFFFFF", "borderWidth": 1},
                "data": [
                    {**data[0], "itemStyle": {"color": NAVY}},
                    {**data[1], "itemStyle": {"color": STEEL}},
                    {**data[2], "itemStyle": {"color": "#B45309"}},
                ],
            }
        ],
    )


def _tab_elementos(df: pd.DataFrame) -> None:
    render_section(
        "Flujo de Decisión y Embudo de Daños",
        "Protocolo secuencial ANIH V.8: salidas tempranas por seguridad "
        "frente a inspección interna detallada.",
    )

    filtros = render_filtros_analisis(df, titulo="Filtros")
    df_f = aplicar_filtros_analisis(df, filtros)
    st.caption(
        f"Corte activo: **{fmt_es_int(len(df_f))}** de **{fmt_es_int(len(df))}** inspecciones "
        "(solo esta pestaña)."
    )
    if df_f.empty:
        st.warning("El filtro no deja filas. Amplíe la selección.")
        return

    with st.spinner("Clasificando flujo de inspección (Pasos 2–4)…"):
        anih = _anih_cached(df_f)
        m = metricas_flujo_inspeccion(anih)

    st.caption(
        "Las casillas vacías **después** de un Riesgo externo C se interpretan como "
        "**descarte temprano legítimo** (protocolo), no como dato faltante."
    )

    # —— KPIs: tasa de terminación temprana ——
    st.markdown("##### Tasa de terminación temprana")
    render_kpi_strip(
        [
            {
                "label": "Inspecciones iniciadas",
                "value": fmt_es_int(m["n"]),
            },
            {
                "label": "% sin ingresar (Ext. C)",
                "value": f"{m['pct_sin_ingresar']:.1f} %",
                "tone": "warning",
                "hint": f"{fmt_es_int(m['n_descarte_ext'])} descartes legítimos",
            },
            {
                "label": "% a inspección interna",
                "value": f"{m['pct_paso3']:.1f} %",
                "tone": "flag",
                "hint": fmt_es_int(m["n_paso3"]),
            },
            {
                "label": "% hasta daño moderado",
                "value": f"{m['pct_paso4']:.1f} %",
                "tone": "muted",
                "hint": fmt_es_int(m["n_paso4"]),
            },
            {
                "label": "Paro en daño severo C",
                "value": f"{m['pct_descarte_sev']:.1f} %",
                "hint": fmt_es_int(m["n_descarte_sev"]),
            },
        ]
    )

    # —— Embudo / Sankey ——
    c_left, c_right = st.columns([0.62, 0.38])
    with c_left:
        st.markdown("##### Flujo de decisión (Sankey)")
        st.caption(
            "Ancho del flujo = volumen. Etiquetas: **n absoluto** y **% sobre inspecciones iniciadas**. "
            "Izquierda: riesgo externo; derecha: descarte o profundización."
        )
        sankey = _opts_sankey_flujo(m)
        if sankey:
            st_echarts(sankey, height="460px", key="anih-flujo-sankey-v2")
        else:
            st.info("Sin datos suficientes para el flujo.")
    with c_right:
        st.markdown("##### Embudo de avance")
        st.caption("Solo la rama que continúa (sin los descartes laterales).")
        funnel = _opts_funnel_flujo(m)
        if funnel:
            st_echarts(funnel, height="420px", key="anih-flujo-funnel")

    # —— Síntesis dinámica ——
    st.markdown("##### Síntesis del flujo")
    st.success(texto_sintesis_flujo(m))

    # —— Detalle opcional (antes tablas ABC) ——
    with st.expander("Detalle de causas C en evaluación interna", expanded=False):
        causas = m.get("causas_c") or {}
        if causas:
            tab_c = pd.DataFrame(
                [{"Bloque interno": k, "Inspecciones con C": v} for k, v in causas.items()]
            )
            st.dataframe(tab_c, use_container_width=True, hide_index=True)
        st.caption(
            f"Sin avance interno documentado (ni descarte severo ni Paso 4): "
            f"**{fmt_es_int(m['n_sin_avance'])}**."
        )

    res = resumen_elementos_abc(anih)
    with st.expander("Conteo A/B/C por bloque (referencia técnica)", expanded=False):
        st.dataframe(res, use_container_width=True, hide_index=True)

    with st.expander("Regla de decisión · Planilla V.8 / ANIH (referencia)", expanded=False):
        st.markdown(RESUMEN_METODO)


def page_ejecutivo(df: pd.DataFrame, summary: dict[str, Any]) -> None:
    """Inicio: semáforo nacional y tortas por estado."""
    _inject_css()
    render_section(
        "Inicio",
        "Panorama nacional de inspecciones · semáforo y distribución por estado.",
    )
    _tab_semaforo_tortas(df, summary)
