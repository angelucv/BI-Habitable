"""Salidas PDNA: guía de reportes CPEDHI + matriz de análisis 2.º nivel."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

from anih_logic import enriquecer_riesgos_anih
from export_utils import download_csv_button, download_excel_button, fmt_es_int
from process_habitable import _uso_pdna
from ui_theme import render_section

# Colores alineados al semáforo Habitable / estratificación 2.º nivel
_COLOR_EST = {
    "Riesgo externo / geotécnico": "#B91C1C",
    "Daño estructural": "#DC2626",
    "Daño no estructural": "#F97316",
    "Sin desagregar (rojo)": "#FB7185",
    "Amarillo con daño estructural": "#CA8A04",
    "Amarillo sin daño estructural": "#EAB308",
    "Verde": "#16A34A",
    "Pérdida total": "#0F172A",
    "Otros": "#94A3B8",
}

_ORDEN_EST = list(_COLOR_EST.keys())


def _tipologia_inmueble(df: pd.DataFrame) -> pd.Series:
    """casa · edificio · turismo · comercio · otros."""
    uso = df["uso"] if "uso" in df.columns else (
        df["uso_raw_n"] if "uso_raw_n" in df.columns else df.get("uso_n")
    )
    pisos = df.get("num_pisos")
    nom = df["nombre_edificacion"] if "nombre_edificacion" in df.columns else None
    obs = df["observaciones"] if "observaciones" in df.columns else None
    dire = df["direccion"] if "direccion" in df.columns else None
    if uso is None:
        return pd.Series("otros", index=df.index)
    rows = []
    for i, u in enumerate(uso):
        idx = uso.index[i] if hasattr(uso, "index") else i
        p = pisos.loc[idx] if pisos is not None else None
        n = nom.loc[idx] if nom is not None else None
        o = obs.loc[idx] if obs is not None else None
        d = dire.loc[idx] if dire is not None else None
        rows.append(_uso_pdna(u, p, nombre=n, observaciones=o, direccion=d) or "otros")
    return pd.Series(rows, index=df.index)


def _tiene_dano_estructural(df: pd.DataFrame) -> pd.Series:
    """Proxy alineado a reportes de 2.º nivel / Boletín 61 (elementos de carga)."""
    if "anih_sev" in df.columns:
        base = df["anih_sev"].astype(str).eq("C")
    else:
        base = pd.Series(False, index=df.index)
    for c in ("sev_columna", "sev_muro_concreto", "sev_muro_mamposteria", "sev_viga"):
        if c in df.columns:
            nums = pd.to_numeric(df[c], errors="coerce")
            base = base | (nums.fillna(0) > 0)
    return base


def clasificar_rojo_boletin(df: pd.DataFrame) -> pd.Series:
    """Clasificación de rojas: Riesgo externo · Daño estructural · No estructural."""
    out = pd.Series("Sin desagregar (rojo)", index=df.index, dtype=object)
    ext = df["anih_ext"].astype(str).eq("C") if "anih_ext" in df.columns else pd.Series(False, index=df.index)
    sev = df["anih_sev"].astype(str).eq("C") if "anih_sev" in df.columns else pd.Series(False, index=df.index)
    comp = df["anih_comp"].astype(str).eq("C") if "anih_comp" in df.columns else pd.Series(False, index=df.index)
    out = out.mask(comp & ~ext & ~sev, "Daño no estructural")
    out = out.mask(sev & ~ext, "Daño estructural")
    out = out.mask(ext, "Riesgo externo / geotécnico")
    return out


def _elementos_estructurales(df: pd.DataFrame) -> pd.Series:
    """Etiqueta tipo Excel 2.º nivel: Columnas · Muros · Vigas (combinaciones)."""
    col = (
        pd.to_numeric(df["sev_columna"], errors="coerce").fillna(0) > 0
        if "sev_columna" in df.columns
        else pd.Series(False, index=df.index)
    )
    muro_c = (
        pd.to_numeric(df["sev_muro_concreto"], errors="coerce").fillna(0) > 0
        if "sev_muro_concreto" in df.columns
        else pd.Series(False, index=df.index)
    )
    muro_m = (
        pd.to_numeric(df["sev_muro_mamposteria"], errors="coerce").fillna(0) > 0
        if "sev_muro_mamposteria" in df.columns
        else pd.Series(False, index=df.index)
    )
    vig = (
        pd.to_numeric(df["sev_viga"], errors="coerce").fillna(0) > 0
        if "sev_viga" in df.columns
        else pd.Series(False, index=df.index)
    )
    muro = muro_c | muro_m

    def _label(i: int) -> str:
        bits: list[str] = []
        if bool(col.iloc[i]):
            bits.append("Columnas")
        if bool(muro.iloc[i]):
            bits.append("Muros")
        if bool(vig.iloc[i]):
            bits.append("Vigas")
        return ", ".join(bits) if bits else "Ninguno/Menores"

    return pd.Series([_label(i) for i in range(len(df))], index=df.index, dtype=object)


def estratificacion_2do_nivel(df: pd.DataFrame) -> pd.Series:
    """Estrato operativo del Excel de 2.º nivel (rojo/amarillo/verde/pérdida)."""
    work = enriquecer_riesgos_anih(df) if "anih_ext" not in df.columns else df
    et = work["etiqueta_n"].astype(str).str.upper() if "etiqueta_n" in work.columns else pd.Series("", index=work.index)
    out = pd.Series("Otros", index=work.index, dtype=object)
    out = out.mask(et == "VERDE", "Verde")
    out = out.mask(et == "NEGRO", "Pérdida total")

    ama = et == "AMARILLO"
    if ama.any():
        con = _tiene_dano_estructural(work.loc[ama])
        out.loc[ama] = np.where(con, "Amarillo con daño estructural", "Amarillo sin daño estructural")

    rojo = et == "ROJO"
    if rojo.any():
        out.loc[rojo] = clasificar_rojo_boletin(work.loc[rojo]).values
    return out


def consolidar_indicadores_salida(df: pd.DataFrame) -> dict[str, Any]:
    """Indicadores tipo «Indicadores de Filtrado» + estratificación del informe PNUD."""
    if df is None or df.empty:
        return {"n": 0}
    work = enriquecer_riesgos_anih(df)
    et = work["etiqueta_n"].astype(str).str.upper() if "etiqueta_n" in work.columns else pd.Series("", index=work.index)
    n = int(len(work))
    n_v = int((et == "VERDE").sum())
    n_a = int((et == "AMARILLO").sum())
    n_r = int((et == "ROJO").sum())
    n_n = int((et == "NEGRO").sum())
    n_alerta = n_a + n_r + n_n
    tip = _tipologia_inmueble(work)
    work = work.assign(_tip=tip, _et=et)

    ama = work.loc[et == "AMARILLO"]
    ama_est = _tiene_dano_estructural(ama) if not ama.empty else pd.Series(dtype=bool)
    n_ama_con = int(ama_est.sum()) if len(ama_est) else 0
    n_ama_sin = int(len(ama) - n_ama_con)

    rojo = work.loc[et == "ROJO"]
    if rojo.empty:
        rojo_cat = pd.Series(dtype=object)
    else:
        rojo_cat = clasificar_rojo_boletin(rojo)
    n_rojo_ext = int((rojo_cat == "Riesgo externo / geotécnico").sum()) if len(rojo_cat) else 0
    n_rojo_est = int((rojo_cat == "Daño estructural").sum()) if len(rojo_cat) else 0
    n_rojo_noe = int((rojo_cat == "Daño no estructural").sum()) if len(rojo_cat) else 0
    n_rojo_sd = int((rojo_cat == "Sin desagregar (rojo)").sum()) if len(rojo_cat) else 0

    alerta = work.loc[et.isin(["AMARILLO", "ROJO", "NEGRO"])]
    casas_alerta = int((alerta["_tip"] == "casa").sum()) if not alerta.empty else 0
    edif_alerta = int((alerta["_tip"] == "edificio").sum()) if not alerta.empty else 0

    rojo_casa = rojo.loc[rojo["_tip"] == "casa"] if not rojo.empty else rojo
    rojo_edif = rojo.loc[rojo["_tip"] == "edificio"] if not rojo.empty else rojo

    def _split_tip(sub: pd.DataFrame) -> dict[str, int]:
        if sub.empty:
            return {"ext": 0, "est": 0, "total": 0}
        cat = clasificar_rojo_boletin(sub)
        return {
            "ext": int((cat == "Riesgo externo / geotécnico").sum()),
            "est": int((cat == "Daño estructural").sum()),
            "total": int(len(sub)),
        }

    personas = pd.to_numeric(work.get("num_personas"), errors="coerce").fillna(0).sum() if "num_personas" in work.columns else 0

    return {
        "n": n,
        "n_verde": n_v,
        "n_amarillo": n_a,
        "n_rojo": n_r,
        "n_negro": n_n,
        "n_alerta": n_alerta,
        "pct_alerta": 100.0 * n_alerta / max(n, 1),
        "pct_verde": 100.0 * n_v / max(n, 1),
        "ama_sin_est": n_ama_sin,
        "ama_con_est": n_ama_con,
        "pct_ama_sin": 100.0 * n_ama_sin / max(n_a, 1),
        "pct_ama_con": 100.0 * n_ama_con / max(n_a, 1),
        "ama_casa_sin": int(((ama["_tip"] == "casa") & ~ama_est).sum()) if not ama.empty else 0,
        "ama_edif_sin": int(((ama["_tip"] == "edificio") & ~ama_est).sum()) if not ama.empty else 0,
        "ama_casa_con": int(((ama["_tip"] == "casa") & ama_est).sum()) if not ama.empty else 0,
        "ama_edif_con": int(((ama["_tip"] == "edificio") & ama_est).sum()) if not ama.empty else 0,
        "rojo_ext": n_rojo_ext,
        "rojo_est": n_rojo_est,
        "rojo_noe": n_rojo_noe,
        "rojo_sd": n_rojo_sd,
        "pct_rojo_ext": 100.0 * n_rojo_ext / max(n_r, 1),
        "pct_rojo_est": 100.0 * n_rojo_est / max(n_r, 1),
        "casas_alerta": casas_alerta,
        "edif_alerta": edif_alerta,
        "pct_casas_alerta": 100.0 * casas_alerta / max(n_alerta, 1),
        "pct_edif_alerta": 100.0 * edif_alerta / max(n_alerta, 1),
        "rojo_casa": _split_tip(rojo_casa),
        "rojo_edif": _split_tip(rojo_edif),
        "criticos_rn": n_r + n_n,
        "personas": int(personas),
    }


def construir_matriz_2do_nivel(df: pd.DataFrame) -> pd.DataFrame:
    """Matriz larga estilo DataAnálisis_2doNivel: territorio × tipología × pisos × estrato."""
    if df is None or df.empty:
        return pd.DataFrame()

    work = enriquecer_riesgos_anih(df).copy()
    tip = _tipologia_inmueble(work)
    est = estratificacion_2do_nivel(work)
    elem = _elementos_estructurales(work)
    et = work["etiqueta_n"].astype(str).str.upper() if "etiqueta_n" in work.columns else pd.Series("", index=work.index)
    pisos = pd.to_numeric(work.get("num_pisos"), errors="coerce")
    # Evitar outliers absurdos en el pivote (p. ej. 1154): se muestran como «s/d» en banda
    pisos_ok = pisos.where((pisos >= 0) & (pisos <= 60))
    personas = pd.to_numeric(work.get("num_personas"), errors="coerce").fillna(0)

    base = pd.DataFrame(
        {
            "estado": work["estado_n"].astype(str) if "estado_n" in work.columns else "s/d",
            "municipio": work["municipio_n"].astype(str) if "municipio_n" in work.columns else "s/d",
            "parroquia": work["parroquia_n"].astype(str) if "parroquia_n" in work.columns else "s/d",
            "tipologia": tip.astype(str),
            "num_pisos": pisos_ok,
            "etiqueta": et,
            "estratificacion": est.astype(str),
            "elementos_estructurales": elem.astype(str),
            "inspecciones": 1,
            "personas": personas,
        }
    )
    # num_pisos como entero nullable
    base["num_pisos"] = pd.array(
        [int(x) if pd.notna(x) else pd.NA for x in base["num_pisos"]],
        dtype="Int64",
    )

    gcols = [
        "estado",
        "municipio",
        "parroquia",
        "tipologia",
        "num_pisos",
        "etiqueta",
        "estratificacion",
        "elementos_estructurales",
    ]
    out = (
        base.groupby(gcols, dropna=False, observed=True)
        .agg(inspecciones=("inspecciones", "sum"), personas=("personas", "sum"))
        .reset_index()
    )
    out["inspecciones"] = out["inspecciones"].astype(int)
    out["personas"] = out["personas"].astype(int)
    return out.sort_values(
        ["estado", "municipio", "parroquia", "tipologia", "num_pisos", "etiqueta", "estratificacion"],
        kind="mergesort",
    ).reset_index(drop=True)


def matriz_2do_nivel_ancha(mat: pd.DataFrame) -> pd.DataFrame:
    """Versión ancha (territorio × tipología × pisos) con columnas por estratificación."""
    if mat is None or mat.empty:
        return pd.DataFrame()
    keys = ["estado", "municipio", "parroquia", "tipologia", "num_pisos"]
    piv = (
        mat.pivot_table(
            index=keys,
            columns="estratificacion",
            values="inspecciones",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
    )
    piv.columns.name = None
    for c in _ORDEN_EST:
        if c not in piv.columns:
            piv[c] = 0
    extra = [c for c in piv.columns if c not in keys and c not in _ORDEN_EST]
    ordered = keys + [c for c in _ORDEN_EST if c in piv.columns] + extra
    piv = piv[ordered]
    piv["total_edificaciones"] = piv[[c for c in _ORDEN_EST if c in piv.columns]].sum(axis=1)
    pers = (
        mat.groupby(keys, dropna=False, observed=True)["personas"]
        .sum()
        .reset_index()
        .rename(columns={"personas": "total_personas"})
    )
    return piv.merge(pers, on=keys, how="left")


def _opts_apilado(
    tab: pd.DataFrame,
    *,
    col_cat: str,
    col_stack: str,
    col_val: str = "inspecciones",
    top: int = 15,
) -> dict[str, Any] | None:
    if tab is None or tab.empty or col_cat not in tab.columns:
        return None
    agg = tab.groupby([col_cat, col_stack], dropna=False)[col_val].sum().reset_index()
    tops = (
        agg.groupby(col_cat)[col_val]
        .sum()
        .sort_values(ascending=False)
        .head(top)
        .index.tolist()
    )
    if not tops:
        return None
    agg = agg.loc[agg[col_cat].isin(tops)]
    stacks = [s for s in _ORDEN_EST if s in set(agg[col_stack].astype(str))]
    if not stacks:
        stacks = sorted(agg[col_stack].astype(str).unique().tolist())
    cats = [str(c) for c in tops]
    series = []
    for s in stacks:
        sub = agg.loc[agg[col_stack].astype(str) == s].set_index(col_cat)[col_val]
        series.append(
            {
                "name": s,
                "type": "bar",
                "stack": "total",
                "emphasis": {"focus": "series"},
                "itemStyle": {"color": _COLOR_EST.get(s, "#64748B")},
                "data": [int(sub.get(c, 0)) for c in tops],
            }
        )
    return {
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "legend": {"type": "scroll", "top": 0, "data": stacks},
        "grid": {"left": 8, "right": 16, "top": 56, "bottom": 72, "containLabel": True},
        "xAxis": {
            "type": "category",
            "data": cats,
            "axisLabel": {"rotate": 28, "fontSize": 10},
        },
        "yAxis": {"type": "value", "name": "Inspecciones"},
        "series": series,
        "toolbox": {"feature": {"saveAsImage": {}}},
    }


def _opts_barras_simple(counts: dict[str, int]) -> dict[str, Any] | None:
    items = [(k, int(v)) for k, v in counts.items() if int(v) > 0]
    if not items:
        return None
    # Prefer known order
    ordered = [k for k in _ORDEN_EST if k in dict(items)]
    rest = [k for k, _ in items if k not in ordered]
    labels = ordered + rest
    vals = [dict(items)[k] for k in labels]
    return {
        "tooltip": {"trigger": "axis"},
        "grid": {"left": 8, "right": 16, "top": 24, "bottom": 96, "containLabel": True},
        "xAxis": {
            "type": "category",
            "data": labels,
            "axisLabel": {"rotate": 25, "fontSize": 10},
        },
        "yAxis": {"type": "value"},
        "series": [
            {
                "type": "bar",
                "data": [
                    {"value": v, "itemStyle": {"color": _COLOR_EST.get(lab, "#64748B")}}
                    for lab, v in zip(labels, vals, strict=True)
                ],
                "barMaxWidth": 42,
            }
        ],
        "toolbox": {"feature": {"saveAsImage": {}}},
    }


def render_guia_salidas_reportes(*, embebida: bool = True) -> None:
    """Guías de lectura al estilo de los reportes Excel/PDF del equipo CPEDHI."""
    if embebida:
        st.markdown("##### Guía de lectura de salidas (reportes CPEDHI → PNUD)")
        st.caption(
            "Cómo interpretar las clasificaciones de los reportes de nivel nacional / 2.º nivel "
            "y cómo se conectan con esta sección PDNA."
        )
    else:
        render_section(
            "Guía de lectura de salidas",
            "Clasificaciones de los reportes CPEDHI y su uso en el PDNA.",
        )

    st.info(
        "Los Excel de **nivel nacional (A+R)** y **análisis de 2.º nivel** desagregan el semáforo "
        "por **causa de inhabilitación** (riesgo externo, daño estructural, no estructural). "
        "La pestaña **Análisis 2.º nivel** reproduce esa matriz sobre el corte Habitable activo."
    )

    st.markdown(
        """
<div class="pdna-guide-grid">
  <div class="pdna-guide-card calibrar">
    <div class="pdna-guide-tag calibrar">Semáforo Habitable</div>
    <h4>Verde · Amarillo · Rojo · Pérdida total</h4>
    <p>Es la etiqueta operativa de habitabilidad (ANIH V.8 + extensión Habitable). En los reportes PNUD,
    <strong>alerta</strong> = Amarillo + Rojo + Pérdida total.</p>
    <ul>
      <li><strong>Verde:</strong> sin riesgo significativo de habitabilidad.</li>
      <li><strong>Amarillo:</strong> alerta preventiva; se subdivide con/sin daño estructural.</li>
      <li><strong>Rojo:</strong> crítico; se desagrega por causa (externo / estructural / no estructural).</li>
      <li><strong>Pérdida total (Negro):</strong> colapso extremo / pérdida total operativa.</li>
    </ul>
  </div>
  <div class="pdna-guide-card calibrar">
    <div class="pdna-guide-tag calibrar">Rojas — Boletín / 2.º nivel</div>
    <h4>Riesgo externo · Daño estructural · No estructural</h4>
    <p>Prioridad de clasificación (como en el Excel nacional y el informe a PNUD):</p>
    <ul>
      <li><strong>Riesgo externo / geotécnico:</strong> amenaza del entorno (aledaños, geología, inclinación, asentamiento).</li>
      <li><strong>Daño estructural:</strong> falla de elementos de carga (columnas, muros, vigas) sin dominio externo.</li>
      <li><strong>Daño no estructural:</strong> componentes / fachadas / servicios críticos sin falla primaria de carga.</li>
    </ul>
  </div>
  <div class="pdna-guide-card calibrar">
    <div class="pdna-guide-tag calibrar">Amarillas</div>
    <h4>Con / sin daño estructural</h4>
    <p>Sirve para priorizar recuperación temprana:</p>
    <ul>
      <li><strong>Sin daño estructural:</strong> riesgo más manejable; vigilancia y medidas menores.</li>
      <li><strong>Con daño estructural:</strong> riesgo de progresión ante réplicas; candidato a reforzamiento urgente.</li>
    </ul>
  </div>
  <div class="pdna-guide-card fijo">
    <div class="pdna-guide-tag fijo">Tipología del inmueble</div>
    <h4>Casa vs edificio</h4>
    <p>Los reportes de 2.º nivel cruzan territorio × tipología × pisos × causa de daño.
    En PDNA se traduce a tipología constructiva (material × uso × banda de pisos) para monetizar.</p>
  </div>
  <div class="pdna-guide-card fijo">
    <div class="pdna-guide-tag fijo">Salida PDNA</div>
    <h4>De conteos a costos</h4>
    <p>Los reportes CPEDHI aportan la <strong>estratificación física</strong>. Esta app aporta la
    <strong>matriz tipología × semáforo</strong> y, con premisas calibrables, daño en vivienda/contenidos (USD).</p>
    <ul>
      <li>Use el Excel físico (sin costos) para que PNUD/costos apliquen sus propios parámetros.</li>
      <li>Use la guía del modelo de valoración para calibrar USD/m² y factores.</li>
    </ul>
  </div>
  <div class="pdna-guide-card fijo">
    <div class="pdna-guide-tag fijo">Advertencia</div>
    <h4>Versión preliminar</h4>
    <p>El informe a PNUD indica que debe someterse al análisis multidisciplinario de la sala situacional
    (ingeniería, arquitectura, geografía). Las cifras de esta pantalla son del <strong>corte Habitable cargado</strong>
    y pueden diferir levemente del Excel externo si el filtro o la regla de tipología no coinciden.</p>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    with st.expander("Correspondencia rápida con los archivos de referencia", expanded=False):
        st.markdown(
            """
| Entregable de referencia | Qué aporta | Dónde se refleja aquí |
|---|---|---|
| Datos nivel nacional (A+R) | Indicadores de filtrado · pivote territorial · clasificación de rojas/amarillas | Guía de salidas + KPIs de estratificación |
| Análisis 2.º nivel | Cruce estado/municipio/parroquia × tipología × pisos × causa | Pestaña **Análisis 2.º nivel** (matriz + gráficos + Excel) |
| Informe CPEDHI → PNUD | Narrativa PDNA y prioridades | Referencia externa; aquí solo cifras de estratificación |
            """
        )


def render_informe_ejecutivo_pdna(
    df: pd.DataFrame,
    *,
    summary: dict[str, Any] | None = None,
    embebida: bool = True,
) -> None:
    """Análisis 2.º nivel: KPIs de estratificación + matriz interactiva descargable."""
    if embebida:
        st.markdown("##### Análisis de 2.º nivel")
        st.caption(
            "Matriz territorio × tipología × pisos × causa (estilo Excel DataAnálisis 2.º nivel), "
            "recalculada con el corte y filtros PDNA activos."
        )
    else:
        render_section(
            "Análisis de 2.º nivel",
            "Matriz estratificada estilo reportes CPEDHI.",
        )

    _ = summary  # reservado por si se muestra fuente en caption futuro

    with st.spinner("Consolidando matriz de 2.º nivel…"):
        ind = consolidar_indicadores_salida(df)
        mat = construir_matriz_2do_nivel(df)

    if ind.get("n", 0) <= 0 or mat.empty:
        st.warning("Sin datos para el análisis de 2.º nivel en este corte.")
        return

    # Solo cifras de estratificación que no están en la matriz PDNA tipología×semáforo
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Rojas (ext.)", fmt_es_int(ind["rojo_ext"]), f"{ind['pct_rojo_ext']:.0f}% del rojo")
    c2.metric("Rojas (est.)", fmt_es_int(ind["rojo_est"]), f"{ind['pct_rojo_est']:.0f}% del rojo")
    c3.metric("Amarillas c/ est.", fmt_es_int(ind["ama_con_est"]))
    c4.metric("Amarillas s/ est.", fmt_es_int(ind["ama_sin_est"]))
    c5.metric("Pérdida total", fmt_es_int(ind["n_negro"]))

    tip_c1, tip_c2, tip_c3 = st.columns(3)
    tip_c1.metric("Casas en alerta", fmt_es_int(ind["casas_alerta"]), f"{ind['pct_casas_alerta']:.0f}% alerta")
    tip_c2.metric("Edificios en alerta", fmt_es_int(ind["edif_alerta"]), f"{ind['pct_edif_alerta']:.0f}% alerta")
    tip_c3.metric(
        "Rojas s/ desagregar",
        fmt_es_int(ind["rojo_sd"]),
        f"No est. {fmt_es_int(ind['rojo_noe'])}",
    )

    from streamlit_echarts import st_echarts

    f1, f2, f3 = st.columns([1.2, 1, 1])
    with f1:
        nivel = st.radio(
            "Agregar gráficos por",
            ["estado", "municipio", "parroquia"],
            format_func=lambda x: {"estado": "Estado", "municipio": "Municipio", "parroquia": "Parroquia"}[x],
            horizontal=True,
            key="pdna_2n_nivel",
        )
    with f2:
        tips = sorted(mat["tipologia"].dropna().astype(str).unique().tolist())
        tip_sel = st.multiselect("Tipología", tips, default=tips, key="pdna_2n_tip")
    with f3:
        solo_alerta = st.checkbox("Solo alerta (A+R+pérdida)", value=True, key="pdna_2n_alerta")

    view = mat.copy()
    if tip_sel:
        view = view.loc[view["tipologia"].isin(tip_sel)]
    if solo_alerta:
        view = view.loc[view["etiqueta"].isin(["AMARILLO", "ROJO", "NEGRO"])]

    if view.empty:
        st.info("Sin filas con los filtros actuales.")
        return

    g1, g2 = st.columns(2)
    with g1:
        st.markdown("###### Por territorio (apilado)")
        opts_t = _opts_apilado(view, col_cat=nivel, col_stack="estratificacion", top=15)
        if opts_t:
            st_echarts(opts_t, height="420px", key=f"pdna-2n-terr-{nivel}")
        else:
            st.caption("Sin datos para el gráfico territorial.")
    with g2:
        st.markdown("###### Por tipología (apilado)")
        opts_tip = _opts_apilado(view, col_cat="tipologia", col_stack="estratificacion", top=10)
        if opts_tip:
            st_echarts(opts_tip, height="420px", key="pdna-2n-tipologia")
        else:
            st.caption("Sin datos para tipología.")

    st.markdown("###### Distribución de estratificación")
    dist = view.groupby("estratificacion", dropna=False)["inspecciones"].sum().to_dict()
    opts_d = _opts_barras_simple({str(k): int(v) for k, v in dist.items()})
    if opts_d:
        st_echarts(opts_d, height="320px", key="pdna-2n-dist")

    st.markdown("###### Matriz (detalle)")
    show = view.rename(
        columns={
            "estado": "Estado",
            "municipio": "Municipio",
            "parroquia": "Parroquia",
            "tipologia": "Tipología",
            "num_pisos": "N.º pisos",
            "etiqueta": "Semáforo",
            "estratificacion": "Estratificación",
            "elementos_estructurales": "Elementos estructurales",
            "inspecciones": "Inspecciones",
            "personas": "Personas",
        }
    )
    st.dataframe(show, width="stretch", hide_index=True, height=420)

    ancha = matriz_2do_nivel_ancha(view)
    sheets = {
        "Matriz_larga": view,
        "Matriz_ancha": ancha,
        "Resumen_estratificacion": (
            view.groupby("estratificacion", dropna=False)
            .agg(inspecciones=("inspecciones", "sum"), personas=("personas", "sum"))
            .reset_index()
            .sort_values("inspecciones", ascending=False)
        ),
    }
    d1, d2 = st.columns(2)
    with d1:
        download_excel_button(
            sheets,
            filename="analisis_2do_nivel_habitable.xlsx",
            label="Descargar matriz (Excel)",
            key="dl_pdna_2n_xlsx",
        )
    with d2:
        download_csv_button(
            view,
            filename="analisis_2do_nivel_larga.csv",
            label="Descargar matriz larga (CSV)",
            key="dl_pdna_2n_csv",
        )
    st.caption(
        "Filas: estado · municipio · parroquia · tipología · pisos · semáforo · estratificación · elementos. "
        "La hoja ancha pivota la estratificación en columnas (estilo Excel de 2.º nivel)."
    )
