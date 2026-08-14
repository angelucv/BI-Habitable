"""Gráficos ECharts con paleta institucional Habitable."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

NAVY = "#0C2340"
STEEL = "#1F4E79"
# Semáforo vivo (legible en sala de crisis / ECharts)
ETIQUETA_COLORS = {
    "VERDE": "#22C55E",
    "AMARILLO": "#FACC15",
    "ROJO": "#EF4444",
    "NEGRO": "#1E293B",
    "OTRO": "#94A3B8",
}

# Alias didácticos (leyendas): NEGRO → Pérdida total
ETIQUETA_LABEL = {
    "VERDE": "Verde",
    "AMARILLO": "Amarillo",
    "ROJO": "Rojo",
    "NEGRO": "Pérdida total",
    "OTRO": "Otro",
}


def etiqueta_label(code: str) -> str:
    return ETIQUETA_LABEL.get(str(code).strip().upper(), str(code))


def _fmt_es_compact(n: float | int, *, money: bool = False) -> str:
    """Etiquetas cortas para ejes/barras (evita solapamiento de ceros)."""
    x = float(n)
    sign = "-" if x < 0 else ""
    x = abs(x)
    if x >= 1_000_000_000:
        s = f"{x / 1_000_000_000:.1f}".rstrip("0").rstrip(".") + " mil M"
    elif x >= 1_000_000:
        s = f"{x / 1_000_000:.1f}".rstrip("0").rstrip(".") + " M"
    elif x >= 10_000:
        s = f"{x / 1_000:.0f} mil"
    else:
        s = f"{int(round(x)):,}".replace(",", ".")
    if money:
        return f"{sign}USD {s}"
    return f"{sign}{s}"


def _legend_semaforo(present: list[str] | tuple[str, ...]) -> dict[str, Any]:
    """Leyenda semáforo abajo al centro (no choca con toolbox)."""
    return {
        "orient": "horizontal",
        "left": "center",
        "bottom": 2,
        "itemGap": 16,
        "itemWidth": 14,
        "itemHeight": 10,
        "icon": "roundRect",
        "padding": [2, 8],
        "textStyle": {"fontSize": 12, "fontWeight": 600, "color": "#0F172A"},
        "data": [etiqueta_label(e) for e in present],
    }


def _toolbox() -> dict[str, Any]:
    return {
        "show": True,
        "right": 4,
        "top": 2,
        "itemSize": 14,
        "itemGap": 8,
        "feature": {
            "saveAsImage": {"title": "Guardar imagen", "pixelRatio": 2},
            "restore": {"title": "Restablecer"},
            "dataView": {"title": "Datos", "readOnly": True},
        },
    }


def _base_opts(**extra: Any) -> dict[str, Any]:
    opts: dict[str, Any] = {
        "backgroundColor": "#ffffff",
        "animation": True,
        "animationDuration": 600,
        "textStyle": {"fontFamily": "Source Sans 3, Segoe UI, sans-serif", "color": "#0F172A"},
        "toolbox": _toolbox(),
    }
    opts.update(extra)
    return opts


def opts_barras_semaforo(counts: dict[str, int] | pd.Series) -> dict[str, Any]:
    if isinstance(counts, pd.Series):
        counts = counts.to_dict()
    codes = [e for e in ("VERDE", "AMARILLO", "ROJO", "NEGRO") if counts.get(e, 0) > 0]
    if not codes:
        codes = ["VERDE", "AMARILLO", "ROJO", "NEGRO"]
    labels = [etiqueta_label(e) for e in codes]
    vals = [int(counts.get(e, 0)) for e in codes]
    return _base_opts(
        tooltip={"trigger": "axis"},
        legend={"show": False},
        grid={"left": 48, "right": 24, "top": 40, "bottom": 40},
        xAxis={
            "type": "category",
            "data": labels,
            "axisLabel": {"color": "#334155", "fontWeight": 600},
        },
        yAxis={"type": "value", "splitLine": {"lineStyle": {"color": "#E2E8F0"}}},
        series=[
            {
                "type": "bar",
                "data": [
                    {
                        "value": v,
                        "itemStyle": {"color": ETIQUETA_COLORS.get(code, STEEL)},
                    }
                    for code, v in zip(codes, vals, strict=True)
                ],
                "barMaxWidth": 48,
            }
        ],
    )


def opts_apilado_territorio(df: pd.DataFrame, col: str, *, top: int = 12) -> dict[str, Any] | None:
    sub = df.loc[df["etiqueta_n"].isin(ETIQUETA_COLORS)].copy()
    if sub.empty or col not in sub.columns:
        return None
    top_vals = sub[col].value_counts().head(top).index.tolist()
    sub = sub.loc[sub[col].isin(top_vals)]
    ct = pd.crosstab(sub[col], sub["etiqueta_n"])
    for e in ("VERDE", "AMARILLO", "ROJO", "NEGRO"):
        if e not in ct.columns:
            ct[e] = 0
    ct = ct.reindex(columns=["VERDE", "AMARILLO", "ROJO", "NEGRO"], fill_value=0)
    ct = ct.loc[top_vals]
    cats = [str(x) for x in ct.index.tolist()]
    series = []
    for e in ("VERDE", "AMARILLO", "ROJO", "NEGRO"):
        series.append(
            {
                "name": etiqueta_label(e),
                "type": "bar",
                "stack": "total",
                "emphasis": {"focus": "series"},
                "itemStyle": {"color": ETIQUETA_COLORS[e]},
                "data": [int(v) for v in ct[e].tolist()],
            }
        )
    return _base_opts(
        tooltip={"trigger": "axis", "axisPointer": {"type": "shadow"}},
        legend={
            "top": 28,
            "data": [etiqueta_label(e) for e in ("VERDE", "AMARILLO", "ROJO", "NEGRO")],
        },
        grid={"left": 16, "right": 16, "top": 64, "bottom": 80, "containLabel": True},
        xAxis={
            "type": "category",
            "data": cats,
            "axisLabel": {"rotate": 35, "fontSize": 10},
        },
        yAxis={"type": "value"},
        series=series,
    )


def opts_barras_tipologia(
    resumen: pd.DataFrame,
    *,
    horizontal: bool = False,
) -> dict[str, Any] | None:
    if resumen is None or resumen.empty:
        return None
    cats = resumen["tipologia"].astype(str).tolist()
    presentes = [e for e in ("VERDE", "AMARILLO", "ROJO", "NEGRO") if e in resumen.columns]
    series = []
    for e in presentes:
        vals = [int(v) for v in resumen[e].tolist()]
        series.append(
            {
                "name": etiqueta_label(e),
                "type": "bar",
                "stack": "pdna",
                "itemStyle": {"color": ETIQUETA_COLORS[e]},
                "data": list(reversed(vals)) if horizontal else vals,
                "emphasis": {"focus": "series"},
                "barMaxWidth": 22,
            }
        )
    legend = _legend_semaforo(presentes)
    tooltip = {
        "trigger": "axis",
        "axisPointer": {"type": "shadow"},
        "confine": True,
    }
    if horizontal:
        cats_h = list(reversed(cats))
        return _base_opts(
            tooltip=tooltip,
            legend=legend,
            grid={
                "left": 8,
                "right": 36,
                "top": 28,
                "bottom": 44,
                "containLabel": True,
            },
            yAxis={
                "type": "category",
                "data": cats_h,
                "axisLabel": {
                    "fontSize": 11,
                    "interval": 0,
                    "width": 160,
                    "overflow": "truncate",
                    "color": "#334155",
                },
                "axisTick": {"show": False},
            },
            xAxis={
                "type": "value",
                "name": "Unidades",
                "nameLocation": "middle",
                "nameGap": 28,
                "nameTextStyle": {"fontSize": 11, "color": "#64748B"},
                "splitLine": {"show": True, "lineStyle": {"color": "#E2E8F0"}},
                "axisLabel": {
                    "hideOverlap": True,
                    "fontSize": 10,
                    "color": "#64748B",
                    # Etiquetas ya cortas vía formatter de plantilla ECharts
                    "formatter": "{value}",
                },
            },
            series=series,
        )
    return _base_opts(
        tooltip=tooltip,
        legend={
            "orient": "horizontal",
            "left": "center",
            "top": 8,
            "itemGap": 16,
            "itemWidth": 14,
            "itemHeight": 10,
            "icon": "roundRect",
            "textStyle": {"fontSize": 12, "fontWeight": 600, "color": "#0F172A"},
            "data": [etiqueta_label(e) for e in presentes],
        },
        grid={"left": 16, "right": 24, "top": 56, "bottom": 100, "containLabel": True},
        xAxis={
            "type": "category",
            "data": cats,
            "axisLabel": {"rotate": 40, "fontSize": 9, "interval": 0},
        },
        yAxis={"type": "value", "name": "Inspecciones"},
        series=series,
    )


def opts_barras_costo(
    df: pd.DataFrame,
    *,
    col_cat: str,
    col_val: str,
    top: int = 15,
    horizontal: bool = False,
) -> dict[str, Any] | None:
    if df is None or df.empty or col_cat not in df.columns or col_val not in df.columns:
        return None
    g = (
        df.groupby(col_cat, as_index=False)[col_val]
        .sum()
        .sort_values(col_val, ascending=False)
        .head(top)
    )
    if horizontal:
        # Ascendente: la mayor queda arriba en eje categoría ECharts
        g = g.sort_values(col_val, ascending=True)
        vals = [float(x) for x in g[col_val].tolist()]
        # Eje en millones USD para no saturar con ceros
        vals_m = [v / 1_000_000.0 for v in vals]
        data_pts = [
            {
                "value": round(vm, 2),
                "label": {
                    "show": True,
                    "position": "right",
                    "fontSize": 10,
                    "color": "#0F172A",
                    "formatter": _fmt_es_compact(v, money=True),
                },
            }
            for v, vm in zip(vals, vals_m, strict=True)
        ]
        return _base_opts(
            tooltip={
                "trigger": "axis",
                "axisPointer": {"type": "shadow"},
                "confine": True,
            },
            legend={"show": False},
            grid={"left": 8, "right": 96, "top": 28, "bottom": 40, "containLabel": True},
            yAxis={
                "type": "category",
                "data": g[col_cat].astype(str).tolist(),
                "axisLabel": {
                    "fontSize": 11,
                    "interval": 0,
                    "width": 160,
                    "overflow": "truncate",
                    "color": "#334155",
                },
                "axisTick": {"show": False},
            },
            xAxis={
                "type": "value",
                "name": "Millones USD",
                "nameLocation": "middle",
                "nameGap": 30,
                "nameTextStyle": {"fontSize": 11, "color": "#64748B"},
                "splitNumber": 4,
                "axisLabel": {
                    "hideOverlap": True,
                    "fontSize": 10,
                    "color": "#64748B",
                },
                "splitLine": {"show": True, "lineStyle": {"color": "#E2E8F0"}},
            },
            series=[
                {
                    "name": "Necesidades de recuperación",
                    "type": "bar",
                    "data": data_pts,
                    "itemStyle": {"color": STEEL, "borderRadius": [0, 4, 4, 0]},
                    "barMaxWidth": 22,
                }
            ],
        )
    return _base_opts(
        tooltip={"trigger": "axis"},
        legend={"show": False},
        grid={"left": 16, "right": 24, "top": 40, "bottom": 80, "containLabel": True},
        xAxis={
            "type": "category",
            "data": g[col_cat].astype(str).tolist(),
            "axisLabel": {"rotate": 35, "fontSize": 10},
        },
        yAxis={"type": "value", "name": "USD"},
        series=[
            {
                "type": "bar",
                "data": [round(float(x), 0) for x in g[col_val].tolist()],
                "itemStyle": {"color": STEEL},
            }
        ],
    )


def opts_heatmap_cramer(mat: pd.DataFrame) -> dict[str, Any] | None:
    if mat is None or mat.empty:
        return None
    labels = [str(c) for c in mat.columns]
    data = []
    vals = mat.values
    for i in range(len(labels)):
        for j in range(len(labels)):
            data.append([j, i, round(float(vals[i, j]), 3)])
    return _base_opts(
        tooltip={"position": "top", "formatter": "{c}"},
        grid={"left": 120, "right": 40, "top": 48, "bottom": 80},
        xAxis={
            "type": "category",
            "data": labels,
            "splitArea": {"show": True},
            "axisLabel": {"rotate": 30, "fontSize": 10},
        },
        yAxis={"type": "category", "data": labels, "splitArea": {"show": True}},
        visualMap={
            "min": 0,
            "max": 1,
            "calculable": True,
            "orient": "horizontal",
            "left": "center",
            "bottom": 8,
            "inRange": {"color": ["#F8FAFC", "#93C5FD", "#1F4E79", "#0C2340"]},
        },
        series=[
            {
                "name": "V de Cramer",
                "type": "heatmap",
                "data": data,
                "label": {"show": True, "fontSize": 9},
                "emphasis": {"itemStyle": {"shadowBlur": 8}},
            }
        ],
    )


def opts_sankey_anio_material_etiqueta(df_cat: pd.DataFrame) -> dict[str, Any] | None:
    """Flujo: banda de año → material → semáforo (pesos = conteos)."""
    need = {"anio_banda", "material", "etiqueta"}
    if not need.issubset(df_cat.columns) or df_cat.empty:
        return None
    sub = df_cat.loc[df_cat["etiqueta"].isin(["VERDE", "AMARILLO", "ROJO", "NEGRO"])].copy()
    if sub.empty:
        return None

    def _node(prefix: str, val: str) -> str:
        return f"{prefix}|{val}"

    # Colapsar material a top-N + «Otros» para no explotar el Sankey
    top_mat = sub["material"].value_counts().head(12).index
    sub = sub.copy()
    sub["material"] = sub["material"].where(sub["material"].isin(top_mat), "Otros")

    links: dict[tuple[str, str], int] = {}
    g1 = sub.groupby(["anio_banda", "material"], dropna=False).size()
    for (anio, mat), n in g1.items():
        a = _node("Año", str(anio))
        m = _node("Mat", str(mat)[:40])
        links[(a, m)] = links.get((a, m), 0) + int(n)
    g2 = sub.groupby(["material", "etiqueta"], dropna=False).size()
    for (mat, et), n in g2.items():
        m = _node("Mat", str(mat)[:40])
        e = _node("Sem", str(et))
        links[(m, e)] = links.get((m, e), 0) + int(n)

    nodes_set: set[str] = set()
    link_list = []
    for (s, t), v in links.items():
        nodes_set.add(s)
        nodes_set.add(t)
        link_list.append({"source": s, "target": t, "value": int(v)})

    def _label(n: str) -> str:
        return n.split("|", 1)[-1]

    nodes = []
    for n in sorted(nodes_set):
        lab = _label(n)
        item: dict[str, Any] = {"name": n, "label": {"formatter": lab}}
        if n.startswith("Sem|"):
            item["label"] = {"formatter": etiqueta_label(lab)}
            item["itemStyle"] = {"color": ETIQUETA_COLORS.get(lab, STEEL)}
        nodes.append(item)

    return _base_opts(
        tooltip={"trigger": "item", "triggerOn": "mousemove"},
        series=[
            {
                "type": "sankey",
                "emphasis": {"focus": "adjacency"},
                "nodeAlign": "justify",
                "data": nodes,
                "links": link_list,
                "lineStyle": {"color": "gradient", "curveness": 0.4},
                "label": {"fontSize": 10},
            }
        ],
    )


def opts_pareto_uso(diag: pd.DataFrame) -> dict[str, Any] | None:
    """Barras comparativas antes/después (fase en el eje)."""
    if diag is None or diag.empty:
        return None
    # Mostrar top categorías por fase en dos series agrupadas es engorroso;
    # usamos barras horizontales filtradas por fase en el caller, o stacked count.
    fases = diag["fase"].unique().tolist()
    cats = (
        diag.loc[diag["fase"] == fases[0], "categoria"].head(12).tolist()
        if fases
        else []
    )
    if not cats and not diag.empty:
        cats = diag["categoria"].head(12).tolist()
    series = []
    for fase in fases:
        sub = diag.loc[diag["fase"] == fase].set_index("categoria")
        series.append(
            {
                "name": fase,
                "type": "bar",
                "data": [int(sub["conteo"].get(c, 0)) for c in cats],
            }
        )
    return _base_opts(
        tooltip={"trigger": "axis"},
        legend={"top": 0},
        grid={"left": 16, "right": 24, "top": 48, "bottom": 100, "containLabel": True},
        xAxis={"type": "category", "data": [str(c)[:28] for c in cats], "axisLabel": {"rotate": 40, "fontSize": 9}},
        yAxis={"type": "value", "name": "Inspecciones"},
        series=series,
    )


def opts_barras_grupos_uso(counts: pd.Series) -> dict[str, Any] | None:
    if counts is None or counts.empty:
        return None
    labs = counts.index.astype(str).tolist()
    vals = [int(x) for x in counts.tolist()]
    return _base_opts(
        tooltip={"trigger": "axis"},
        grid={"left": 16, "right": 24, "top": 40, "bottom": 80, "containLabel": True},
        xAxis={"type": "category", "data": labs, "axisLabel": {"rotate": 30, "fontSize": 10}},
        yAxis={"type": "value"},
        series=[{"type": "bar", "data": vals, "itemStyle": {"color": STEEL}, "barMaxWidth": 40}],
    )


def opts_sunburst_estado_mun_sem(df: pd.DataFrame, *, top_estados: int = 6) -> dict[str, Any] | None:
    """Sunburst: Estado → Municipio → Semáforo (hojas con color semántico)."""
    sub = df.loc[df["etiqueta_n"].isin(ETIQUETA_COLORS)].copy()
    if sub.empty:
        return None
    top_e = sub["estado_n"].value_counts().head(top_estados).index.tolist()
    sub = sub.loc[sub["estado_n"].isin(top_e)]
    children_est: list[dict[str, Any]] = []
    for est, g_e in sub.groupby("estado_n", sort=False):
        mun_children: list[dict[str, Any]] = []
        top_m = g_e["municipio_n"].value_counts().head(8).index
        g_e2 = g_e.loc[g_e["municipio_n"].isin(top_m)]
        for mun, g_m in g_e2.groupby("municipio_n", sort=False):
            leaves = []
            for et, n in g_m["etiqueta_n"].value_counts().items():
                leaves.append(
                    {
                        "name": etiqueta_label(str(et)),
                        "value": int(n),
                        "itemStyle": {"color": ETIQUETA_COLORS.get(str(et), STEEL)},
                    }
                )
            mun_children.append({"name": str(mun)[:32], "children": leaves})
        children_est.append({"name": str(est)[:28], "children": mun_children})

    return _base_opts(
        tooltip={"trigger": "item"},
        series=[
            {
                "type": "sunburst",
                "radius": ["12%", "92%"],
                "sort": None,
                "emphasis": {"focus": "ancestor"},
                "data": children_est,
                "label": {"rotate": "radial", "minAngle": 4, "fontSize": 9},
                "levels": [
                    {},
                    {"r0": "12%", "r": "38%", "label": {"align": "right"}},
                    {"r0": "38%", "r": "65%"},
                    {"r0": "65%", "r": "92%", "label": {"position": "outside", "padding": 2}},
                ],
            }
        ],
    )


def opts_decada_apilada_pct(df: pd.DataFrame) -> dict[str, Any] | None:
    """Barras 100 %: década de construcción × semáforo."""
    an = pd.to_numeric(df.get("anio_construccion_n", df.get("anio_construccion")), errors="coerce")
    sub = df.loc[an.notna() & df["etiqueta_n"].isin(ETIQUETA_COLORS)].copy()
    if sub.empty:
        return None
    an2 = an.loc[sub.index]
    bins = list(range(1900, 2040, 10))
    labels = [f"{b}-{b + 9}" for b in bins[:-1]]
    sub = sub.assign(decada=pd.cut(an2, bins=bins, labels=labels, right=False))
    sub = sub.loc[sub["decada"].notna()]
    if sub.empty:
        return None
    ct = pd.crosstab(sub["decada"], sub["etiqueta_n"], normalize="index") * 100.0
    for e in ETIQUETA_COLORS:
        if e not in ct.columns:
            ct[e] = 0.0
    ct = ct[[e for e in ("VERDE", "AMARILLO", "ROJO", "NEGRO") if e in ct.columns]]
    x = [str(i) for i in ct.index.tolist()]
    series = []
    for e in ct.columns:
        series.append(
            {
                "name": etiqueta_label(str(e)),
                "type": "bar",
                "stack": "pct",
                "emphasis": {"focus": "series"},
                "itemStyle": {"color": ETIQUETA_COLORS[e]},
                "data": [round(float(v), 1) for v in ct[e].tolist()],
            }
        )
    return _base_opts(
        tooltip={"trigger": "axis", "axisPointer": {"type": "shadow"}},
        legend={"top": 0, "data": [etiqueta_label(str(e)) for e in ct.columns]},
        grid={"left": 48, "right": 24, "top": 40, "bottom": 60},
        xAxis={"type": "category", "data": x, "axisLabel": {"rotate": 30, "fontSize": 10}},
        yAxis={"type": "value", "max": 100, "name": "%", "axisLabel": {"formatter": "{value}%"}},
        series=series,
    )


def opts_heatmap_material_mun_severo(df: pd.DataFrame, *, top_mun: int = 12) -> dict[str, Any] | None:
    """Heatmap material × municipio: intensidad de afectación severa (rojo+negro o flag)."""
    sub = df.copy()
    if "riesgo_severo" in sub.columns:
        severo = sub["riesgo_severo"].fillna(False) | sub["etiqueta_n"].isin(["ROJO", "NEGRO"])
    else:
        severo = sub["etiqueta_n"].isin(["ROJO", "NEGRO"])
    sub = sub.loc[severo]
    if sub.empty:
        return None
    topm = sub["municipio_n"].value_counts().head(top_mun).index
    sub = sub.loc[sub["municipio_n"].isin(topm)]
    # Colapsar material a top
    top_mat = sub["material_n"].value_counts().head(8).index
    sub = sub.assign(
        mat=sub["material_n"].where(sub["material_n"].isin(top_mat), "OTROS"),
    )
    ct = pd.crosstab(sub["mat"], sub["municipio_n"])
    mats = ct.index.tolist()
    muns = ct.columns.tolist()
    data = []
    for i, mat in enumerate(mats):
        for j, mun in enumerate(muns):
            data.append([j, i, int(ct.loc[mat, mun])])
    return _base_opts(
        tooltip={"position": "top"},
        grid={"left": 120, "right": 24, "top": 40, "bottom": 100},
        xAxis={"type": "category", "data": [str(m)[:22] for m in muns], "axisLabel": {"rotate": 35, "fontSize": 9}},
        yAxis={"type": "category", "data": [str(m)[:28] for m in mats], "axisLabel": {"fontSize": 9}},
        visualMap={
            "min": 0,
            "max": max((d[2] for d in data), default=1),
            "calculable": True,
            "orient": "horizontal",
            "left": "center",
            "bottom": 0,
            "inRange": {"color": ["#F8FAFC", "#FCD116", "#CF142B", "#0C2340"]},
        },
        series=[{"type": "heatmap", "data": data, "label": {"show": True, "fontSize": 9}}],
    )


def opts_sankey_material_falla_sem(df: pd.DataFrame) -> dict[str, Any] | None:
    """Material → modo de falla → semáforo."""
    sub = df.loc[df["etiqueta_n"].isin(["VERDE", "AMARILLO", "ROJO", "NEGRO"])].copy()
    if sub.empty:
        return None

    def _mat_node(m: Any) -> str:
        n = str(m or "").upper()
        if "ACERO" in n:
            return "Mat|Acero"
        if "INFORMAL" in n:
            return "Mat|Mamp. informal"
        if "FORMAL" in n or "MAMP" in n:
            return "Mat|Mamp. formal"
        if "CONCRETO" in n or "HORMIG" in n or "MIXTO" in n:
            return "Mat|Concreto"
        return "Mat|Otro"

    sub["_mat"] = sub["material_n"].map(_mat_node) if "material_n" in sub.columns else "Mat|Otro"
    rext = sub["riesgo_externo"].fillna(False) if "riesgo_externo" in sub.columns else False
    rsev = sub["riesgo_severo"].fillna(False) if "riesgo_severo" in sub.columns else False
    rmod = sub["riesgo_moderado"].fillna(False) if "riesgo_moderado" in sub.columns else False
    rcomp = sub["riesgo_componentes"].fillna(False) if "riesgo_componentes" in sub.columns else False
    sub["_falla"] = np.where(
        rext,
        "Falla|Afectación geotécnica / externa",
        np.where(
            rsev,
            "Falla|Deterioro estructural",
            np.where(
                rmod | rcomp,
                "Falla|Colapso / daño de tabiquería",
                "Falla|Sin patología marcada",
            ),
        ),
    )
    sub["_sem"] = "Sem|" + sub["etiqueta_n"].astype(str)

    links: dict[tuple[str, str], int] = {}
    for (a, b), n in sub.groupby(["_mat", "_falla"]).size().items():
        links[(a, b)] = links.get((a, b), 0) + int(n)
    for (a, b), n in sub.groupby(["_falla", "_sem"]).size().items():
        links[(a, b)] = links.get((a, b), 0) + int(n)

    nodes_set = set()
    link_list = []
    for (s, t), v in links.items():
        nodes_set.add(s)
        nodes_set.add(t)
        link_list.append({"source": s, "target": t, "value": int(v)})

    def _lab(n: str) -> str:
        return n.split("|", 1)[-1]

    nodes = []
    for n in sorted(nodes_set):
        item: dict[str, Any] = {"name": n, "label": {"formatter": _lab(n)}}
        if n.startswith("Sem|"):
            item["itemStyle"] = {"color": ETIQUETA_COLORS.get(_lab(n), STEEL)}
        nodes.append(item)

    return _base_opts(
        tooltip={"trigger": "item"},
        series=[
            {
                "type": "sankey",
                "emphasis": {"focus": "adjacency"},
                "data": nodes,
                "links": link_list,
                "lineStyle": {"color": "gradient", "curveness": 0.45},
                "label": {"fontSize": 10},
            }
        ],
    )


def opts_donut_pdna(resumen: pd.DataFrame, *, col_cat: str, col_val: str) -> dict[str, Any] | None:
    if resumen is None or resumen.empty:
        return None
    g = resumen.groupby(col_cat, as_index=False)[col_val].sum().sort_values(col_val, ascending=False)
    data = [{"name": str(r[col_cat]), "value": round(float(r[col_val]), 0)} for _, r in g.iterrows()]
    return _base_opts(
        tooltip={"trigger": "item", "formatter": "{b}: ${c} ({d}%)"},
        legend={"type": "scroll", "orient": "vertical", "right": 0, "top": 20},
        series=[
            {
                "type": "pie",
                "radius": ["42%", "70%"],
                "center": ["40%", "50%"],
                "data": data,
                "label": {"formatter": "{b}\n{d}%"},
            }
        ],
    )
