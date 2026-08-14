"""Sección PDNA — vista ejecutiva: KPIs, síntesis y matriz agregada."""

from __future__ import annotations

import html

import pandas as pd
import streamlit as st
from streamlit_echarts import st_echarts

from charts_habitable import opts_barras_costo, opts_barras_tipologia
from export_utils import download_csv_button, download_excel_button, fmt_es_int, fmt_es_money
from pdna_costs import (
    AREA_MINIMA_DEFAULT,
    COSTO_M2_DEFAULT,
    FACTORES_CONTENIDOS_DEFAULT,
    FACTORES_VIVIENDA_DEFAULT,
    M2_POR_PISO_DEFAULT,
    RATIO_CONTENIDOS_DEFAULT,
    marco_pdna_ligero,
    matriz_pdna_completa,
    proyectar_pdna,
    resumen_pdna_territorio,
)
from pdna_export import construir_export_pdna_fisico, matriz_fisica_desglosada
from process_habitable import (
    ESQUEMA_PDNA_DETALLADO,
    ESQUEMA_PDNA_EXCEL,
    ESQUEMA_PDNA_OBSERVADO,
    ESQUEMA_PDNA_PISO_A_PISO,
    ESQUEMAS_PDNA_LABELS,
    aplicar_tipologia_pdna,
    bandas_pisos_catalogo,
    desglosar_tipologia_pdna,
    tipos_pdna_orden,
)
from ui_theme import render_kpi_strip, render_section


def _filtros_territorio(df: pd.DataFrame) -> pd.DataFrame:
    st.markdown("##### Ámbito territorial")
    c1, c2 = st.columns(2)
    with c1:
        est_opts = sorted(
            x
            for x in df["estado_n"].dropna().astype(str).unique().tolist()
            if x and x not in {"(SIN ESTADO)", "(sin estado)", "NAN"}
        )
        estados = st.multiselect(
            "Estado",
            est_opts,
            default=[],
            key="pdna_estado",
            help="Vacío = vista nacional. Seleccione estados para el corte territorial.",
        )
    work = df if not estados else df.loc[df["estado_n"].isin(estados)]
    with c2:
        mun_opts = sorted(
            x
            for x in work["municipio_n"].dropna().astype(str).unique().tolist()
            if x and x not in {"", "SIN EVALUAR", "Sin Evaluar", "CARACAS"}
        )
        municipios = st.multiselect("Municipio", mun_opts, default=[], key="pdna_mun")
    if municipios:
        work = work.loc[work["municipio_n"].isin(municipios)]
    return work


def _selector_esquema_tipologia() -> str:
    st.markdown("##### Esquema de tipologías")
    prev = st.session_state.get("pdna_esquema_tip")
    # Por defecto: piso a piso. Migra claves viejas / inválidas.
    if prev is None or prev == "excel_ejemplo" or prev not in ESQUEMAS_PDNA_LABELS:
        st.session_state["pdna_esquema_tip"] = ESQUEMA_PDNA_PISO_A_PISO
    # Migrar «Ampliado» previo solo si el usuario no había elegido otra cosa explícita
    # (si ya tiene Ampliado guardado, se respeta).

    opciones = list(ESQUEMAS_PDNA_LABELS.keys())
    cortos = {
        ESQUEMA_PDNA_PISO_A_PISO: "Piso a piso (recomendado)",
        ESQUEMA_PDNA_DETALLADO: "Ampliado (bandas)",
        ESQUEMA_PDNA_EXCEL: "Plantilla (12)",
        ESQUEMA_PDNA_OBSERVADO: "Dinámico",
    }
    esquema = st.radio(
        "Combinaciones de filas",
        opciones,
        format_func=lambda k: cortos.get(k, ESQUEMAS_PDNA_LABELS[k]),
        horizontal=True,
        key="pdna_esquema_tip",
        label_visibility="collapsed",
        help=(
            "Piso a piso (1–20 + 21 o más) · Ampliado (bandas) · Plantilla · "
            "Dinámico (solo presentes en el corte)"
        ),
    )
    return str(esquema)


def _caption_esquema(esquema: str, mat: pd.DataFrame, n_tips_distintas: int) -> None:
    label = ESQUEMAS_PDNA_LABELS.get(esquema, esquema)
    n_filas = int(len(mat)) if mat is not None and not mat.empty else 0
    st.caption(
        f"Esquema: {label} · {fmt_es_int(n_filas)} filas en matriz · "
        f"{fmt_es_int(n_tips_distintas)} tipologías en datos"
    )


def _ensure_param_defaults() -> None:
    defaults = {
        "pdna_usd_conc": float(COSTO_M2_DEFAULT["concreto"]),
        "pdna_usd_ace": float(COSTO_M2_DEFAULT["acero"]),
        "pdna_usd_mf": float(COSTO_M2_DEFAULT["mampostería formal"]),
        "pdna_usd_mi": float(COSTO_M2_DEFAULT["mampostería informal"]),
        "pdna_m2_piso": float(M2_POR_PISO_DEFAULT),
        "pdna_area_min": float(AREA_MINIMA_DEFAULT),
        "pdna_fv": float(FACTORES_VIVIENDA_DEFAULT["VERDE"]),
        "pdna_fa": float(FACTORES_VIVIENDA_DEFAULT["AMARILLO"]),
        "pdna_fr": float(FACTORES_VIVIENDA_DEFAULT["ROJO"]),
        "pdna_fn": float(FACTORES_VIVIENDA_DEFAULT["NEGRO"]),
        "pdna_ratio_cont": int(round(RATIO_CONTENIDOS_DEFAULT * 100)),
        "pdna_cv": float(FACTORES_CONTENIDOS_DEFAULT["VERDE"]),
        "pdna_ca": float(FACTORES_CONTENIDOS_DEFAULT["AMARILLO"]),
        "pdna_cr": float(FACTORES_CONTENIDOS_DEFAULT["ROJO"]),
        "pdna_cn": float(FACTORES_CONTENIDOS_DEFAULT["NEGRO"]),
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def _params_from_session() -> dict:
    _ensure_param_defaults()
    return {
        "costo_m2": {
            "concreto": float(st.session_state["pdna_usd_conc"]),
            "acero": float(st.session_state["pdna_usd_ace"]),
            "mampostería formal": float(st.session_state["pdna_usd_mf"]),
            "mampostería informal": float(st.session_state["pdna_usd_mi"]),
        },
        "factores_vivienda": {
            "VERDE": float(st.session_state["pdna_fv"]),
            "AMARILLO": float(st.session_state["pdna_fa"]),
            "ROJO": float(st.session_state["pdna_fr"]),
            "NEGRO": float(st.session_state["pdna_fn"]),
        },
        "factores_contenidos": {
            "VERDE": float(st.session_state["pdna_cv"]),
            "AMARILLO": float(st.session_state["pdna_ca"]),
            "ROJO": float(st.session_state["pdna_cr"]),
            "NEGRO": float(st.session_state["pdna_cn"]),
        },
        "ratio_contenidos": float(st.session_state["pdna_ratio_cont"]) / 100.0,
        "m2_por_piso": float(st.session_state["pdna_m2_piso"]),
        "area_minima": float(st.session_state["pdna_area_min"]),
    }


def _panel_parametros() -> None:
    """Widgets de configuración al final (cerrado por defecto)."""
    with st.expander(
        "⚙️ Configuración del Modelo de Valoración (Parámetros)",
        expanded=False,
    ):
        st.caption(
            "Abra solo para estresar el modelo o cambiar premisas. "
            "Los resultados de arriba se recalculan al modificar un valor."
        )
        st.markdown(
            """
<div class="pdna-exec-summary">
  <h3>Cómo usar estos parámetros (lectura rápida)</h3>
  <p>No son precios oficiales: son <strong>premisas de trabajo</strong>. Al subir un número,
  suben los totales en USD; al bajarlo, bajan. Use <strong>+</strong> / <strong>−</strong>
  o el deslizador. Los valores por defecto son un <strong>escenario de partida</strong>;
  las bandas indican rangos habituales de calibración sectorial (no límites rígidos).</p>

  <p><strong>1. Costo de reposición (USD/m²)</strong> — cuánto cuesta reponer 1&nbsp;m² según material.
  Ordene de mayor a menor costo: acero ≥ concreto ≥ mamp. formal ≥ mamp. informal.</p>
  <ul>
    <li><strong>Concreto:</strong> partida <em>450</em> · banda sugerida <strong>350–550</strong>.</li>
    <li><strong>Acero:</strong> partida <em>520</em> · banda <strong>420–650</strong>.</li>
    <li><strong>Mamp. formal:</strong> partida <em>320</em> · banda <strong>250–400</strong>.</li>
    <li><strong>Mamp. informal:</strong> partida <em>220</em> · banda <strong>150–280</strong>.</li>
  </ul>

  <p><strong>2. Área estimada</strong> — Habitable no trae m² fiables en todas las fichas.
  Área ≈ max(pisos × m²/piso, área mínima).</p>
  <ul>
    <li><strong>m² por piso:</strong> partida <em>80</em> · banda <strong>60–100</strong>
      (casas populares hacia abajo; viviendas amplias / plantas tipicas de edificio hacia arriba).</li>
    <li><strong>Área mínima:</strong> partida <em>40</em> · banda <strong>25–50</strong>
      (evita subestimar unidades de 1 piso muy pequeñas).</li>
  </ul>

  <p><strong>3. Factores de daño en vivienda</strong> — fracción del valor de reposición
  que se cuenta como daño. <em>0,25</em> = 25&nbsp;%. Mantenga el orden
  Verde &lt; Amarillo &lt; Rojo ≤ 1 ≤ Negro.</p>
  <ul>
    <li><strong>Verde:</strong> partida <em>0,02</em> · banda <strong>0,01–0,05</strong> (daños menores / cosméticos).</li>
    <li><strong>Amarillo:</strong> partida <em>0,25</em> · banda <strong>0,15–0,40</strong> (reparación parcial).</li>
    <li><strong>Rojo:</strong> partida <em>0,65</em> · banda <strong>0,50–0,85</strong> (reparación mayor / casi reposición).</li>
    <li><strong>Negro:</strong> partida <em>1,15</em> · banda <strong>1,00–1,25</strong>
      (1,00 = solo reponer; &gt;1 = prima <em>Build Back Better</em>; p.&nbsp;ej. 1,15 = +15&nbsp;%).</li>
  </ul>

  <p><strong>4. Contenidos</strong> — mobiliario y enseres.</p>
  <ul>
    <li><strong>% inventario:</strong> partida <em>20&nbsp;%</em> · banda <strong>10–30&nbsp;%</strong>
      (hogares modestos ~10–15&nbsp;%; parque más amueblado ~25–30&nbsp;%). Evite &gt;40&nbsp;% salvo estudio propio.</li>
    <li><strong>Cont. verde:</strong> partida <em>0,05</em> · banda <strong>0,02–0,10</strong>.</li>
    <li><strong>Cont. amarillo:</strong> partida <em>0,35</em> · banda <strong>0,20–0,50</strong>.</li>
    <li><strong>Cont. rojo:</strong> partida <em>0,80</em> · banda <strong>0,60–0,95</strong>.</li>
    <li><strong>Cont. negro:</strong> partida <em>1,00</em> · banda <strong>0,90–1,00</strong> (pérdida casi total del inventario).</li>
  </ul>

  <p><strong>Cálculo en una frase:</strong>
  daño vivienda ≈ valor × factor vivienda del color;
  daño contenidos ≈ (valor × % inventario) × factor contenidos del color;
  necesidades ≈ ambos (con BBB si el factor de vivienda &gt; 1).</p>
  <p><strong>Ejemplo:</strong> casa concreto, 2 pisos, Rojo → área 160&nbsp;m² → valor 72.000&nbsp;USD →
  daño vivienda 46.800 · contenidos (20&nbsp;%) 14.400 × 0,80 = 11.520 · total ≈ 58.320&nbsp;USD.</p>
  <p>Checklist completo: pestaña <strong>Guía del modelo</strong>.</p>
</div>
""",
            unsafe_allow_html=True,
        )
        st.markdown("**Costo de reposición de vivienda (USD/m²)**")
        st.caption(
            "Partida: concreto 450 · acero 520 · mamp. formal 320 · informal 220. "
            "Bandas típicas: 350–550 · 420–650 · 250–400 · 150–280."
        )
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.number_input("Concreto", min_value=50.0, step=10.0, key="pdna_usd_conc")
        with c2:
            st.number_input("Acero", min_value=50.0, step=10.0, key="pdna_usd_ace")
        with c3:
            st.number_input("Mamp. formal", min_value=50.0, step=10.0, key="pdna_usd_mf")
        with c4:
            st.number_input("Mamp. informal", min_value=50.0, step=10.0, key="pdna_usd_mi")

        a1, a2 = st.columns(2)
        with a1:
            st.number_input("m² estimados por piso", min_value=20.0, step=5.0, key="pdna_m2_piso")
        with a2:
            st.number_input("Área mínima (m²)", min_value=20.0, step=5.0, key="pdna_area_min")
        st.caption("Partida: 80 m²/piso · mínimo 40 m². Bandas típicas: 60–100 y 25–50.")

        st.markdown("**Factores de daño en vivienda** (estructural + no estructural)")
        st.caption(
            "Partida: V 0,02 · A 0,25 · R 0,65 · N 1,15. "
            "Bandas: 0,01–0,05 · 0,15–0,40 · 0,50–0,85 · 1,00–1,25. "
            "Negro > 1 = prima Build Back Better en necesidades."
        )
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            st.number_input("Verde", min_value=0.0, max_value=2.0, format="%.2f", key="pdna_fv")
        with f2:
            st.number_input("Amarillo", min_value=0.0, max_value=2.0, format="%.2f", key="pdna_fa")
        with f3:
            st.number_input("Rojo", min_value=0.0, max_value=2.0, format="%.2f", key="pdna_fr")
        with f4:
            st.number_input(
                "Negro (pérdida total)",
                min_value=0.0,
                max_value=2.5,
                format="%.2f",
                key="pdna_fn",
            )

        st.markdown("**Contenidos de la vivienda**")
        st.caption(
            "Inventario partida 20 % (banda 10–30 %). "
            "Factores Cont. partida: 0,05 · 0,35 · 0,80 · 1,00. "
            "Bandas: 0,02–0,10 · 0,20–0,50 · 0,60–0,95 · 0,90–1,00."
        )
        st.slider(
            "Inventario de contenidos (% del valor de reposición)",
            min_value=0,
            max_value=60,
            step=5,
            key="pdna_ratio_cont",
        )
        g1, g2, g3, g4 = st.columns(4)
        with g1:
            st.number_input("Cont. verde", min_value=0.0, max_value=1.5, format="%.2f", key="pdna_cv")
        with g2:
            st.number_input("Cont. amarillo", min_value=0.0, max_value=1.5, format="%.2f", key="pdna_ca")
        with g3:
            st.number_input("Cont. rojo", min_value=0.0, max_value=1.5, format="%.2f", key="pdna_cr")
        with g4:
            st.number_input("Cont. negro", min_value=0.0, max_value=1.5, format="%.2f", key="pdna_cn")


def _sintesis_html(
    *,
    n_inspecciones: int,
    n_criticos: int,
    tasa_critica: float,
    n_verde: int,
    tipologia_mas_afectada: str,
    pct_tipologia: float,
) -> str:
    tip = html.escape(tipologia_mas_afectada)
    return f"""
<div class="pdna-exec-summary">
  <h3>Resumen de afectación física (insumo PDNA)</h3>
  <p>En el corte territorial seleccionado se cuantificaron
  <strong>{fmt_es_int(n_inspecciones)}</strong> unidades habitacionales con tipología asignada.
  De ellas, <strong>{fmt_es_int(n_criticos)}</strong>
  (<strong>{tasa_critica:.1f}%</strong>) presentan daño crítico
  (Rojo o pérdida total), mientras que <strong>{fmt_es_int(n_verde)}</strong> permanecen en Verde.</p>
  <ul>
    <li><strong>Foco operativo:</strong> la tipología con mayor volumen de daño crítico es
    <strong>{tip}</strong>
    (<strong>{pct_tipologia:.1f}%</strong> de las unidades críticas del corte).</li>
    <li>Los <strong>montos estimados</strong> (vivienda, contenidos y necesidades con BBB)
    se calculan con el modelo de valoración y se muestran en la
    <strong>matriz agregada</strong> y en la pestaña territorial — no en estos KPIs.</li>
  </ul>
</div>
"""


def _matriz_para_export(mat: pd.DataFrame) -> pd.DataFrame:
    """Matriz completa (conteos + USD) + fila TOTAL."""
    pie = {
        "tipologia": "TOTAL",
        "verde": int(mat["verde"].sum()),
        "amarillo": int(mat["amarillo"].sum()),
        "rojo": int(mat["rojo"].sum()),
        "negro": int(mat["negro"].sum()),
        "total": int(mat["total"].sum()),
        "dano_vivienda_usd": float(mat["dano_vivienda_usd"].sum()),
        "dano_contenidos_usd": float(mat["dano_contenidos_usd"].sum()),
        "costo_total_usd": float(mat["costo_total_usd"].sum()),
    }
    return pd.concat([mat, pd.DataFrame([pie])], ignore_index=True)


def _agregar_matriz_por_tip_corta(mat: pd.DataFrame) -> pd.DataFrame:
    """Colapsa tipologías a material×uso (sin banda) sumando conteos y USD."""
    if mat is None or mat.empty:
        return mat
    rows = []
    for _, r in mat.iterrows():
        m, u, _b = desglosar_tipologia_pdna(r["tipologia"])
        tip = f"{m} ({u})" if m and u else str(r["tipologia"])
        rows.append(
            {
                "tipologia": tip,
                "verde": int(r["verde"]),
                "amarillo": int(r["amarillo"]),
                "rojo": int(r["rojo"]),
                "negro": int(r["negro"]),
                "total": int(r["total"]),
                "dano_vivienda_usd": float(r.get("dano_vivienda_usd", 0) or 0),
                "dano_contenidos_usd": float(r.get("dano_contenidos_usd", 0) or 0),
                "costo_total_usd": float(r.get("costo_total_usd", 0) or 0),
            }
        )
    raw = pd.DataFrame(rows)
    return (
        raw.groupby("tipologia", as_index=False)
        .sum(numeric_only=True)
        .sort_values("total", ascending=False)
        .reset_index(drop=True)
    )


def _selector_banda_grafico(mat: pd.DataFrame, *, esquema: str) -> tuple[str, pd.DataFrame]:
    """Selector de banda de pisos para gráficos; devuelve (banda|TODAS, matriz filtrada/colapsada)."""
    if mat is None or mat.empty:
        return "TODAS", mat

    # Solo tipologías con unidades (evita barras vacías del catálogo ampliado)
    base = mat.loc[mat["total"].astype(int) > 0].copy()
    if base.empty:
        base = mat.copy()

    tmp = base.copy()
    tmp["_banda"] = [desglosar_tipologia_pdna(t)[2] for t in tmp["tipologia"]]
    presentes = [b for b in tmp["_banda"].dropna().astype(str).unique().tolist() if b]
    catalogo = list(bandas_pisos_catalogo(esquema))
    opciones_bandas = [b for b in catalogo if b in presentes] + sorted(
        set(presentes) - set(catalogo)
    )
    if not opciones_bandas:
        return "TODAS", _agregar_matriz_por_tip_corta(base)

    # Banda por defecto: la de mayor volumen (gráficos legibles)
    vol = tmp.groupby("_banda", dropna=False)["total"].sum().sort_values(ascending=False)
    default_banda = str(vol.index[0]) if len(vol) else opciones_bandas[0]
    labels = ["Todas (material × uso)"] + opciones_bandas
    prev = st.session_state.get("pdna_banda_graf")
    if prev not in labels:
        st.session_state["pdna_banda_graf"] = (
            default_banda if default_banda in labels else labels[0]
        )

    st.markdown("##### Vista de gráficos por banda de pisos")
    banda = st.selectbox(
        "Banda de pisos",
        labels,
        key="pdna_banda_graf",
        help="Filtra los gráficos a una banda para leer material × uso sin saturar el eje.",
    )
    if banda == "Todas (material × uso)":
        return "TODAS", _agregar_matriz_por_tip_corta(base)

    filtrada = tmp.loc[tmp["_banda"].astype(str) == str(banda)].drop(columns=["_banda"])
    # Etiqueta corta: material (uso) — la banda ya está fijada en el selector
    rows = []
    for _, r in filtrada.iterrows():
        m, u, _b = desglosar_tipologia_pdna(r["tipologia"])
        tip = f"{m} ({u})" if m and u else str(r["tipologia"])
        row = r.to_dict()
        row["tipologia"] = tip
        rows.append(row)
    if not rows:
        return str(banda), filtrada
    out = pd.DataFrame(rows)
    out = (
        out.groupby("tipologia", as_index=False)
        .sum(numeric_only=True)
        .sort_values("total", ascending=False)
        .reset_index(drop=True)
    )
    return str(banda), out


def _render_graficos_pdna(mat: pd.DataFrame, *, esquema: str) -> None:
    if mat is None or mat.empty:
        return
    banda_sel, mat_g = _selector_banda_grafico(mat, esquema=esquema)
    if mat_g is None or mat_g.empty:
        st.info("Sin tipologías para la banda seleccionada.")
        return

    resumen_counts = mat_g.rename(
        columns={
            "verde": "VERDE",
            "amarillo": "AMARILLO",
            "rojo": "ROJO",
            "negro": "NEGRO",
        }
    )
    n_rows_chart = max(len(mat_g), 4)
    chart_h = int(min(64 + n_rows_chart * 36, 560))
    titulo_banda = (
        "todas las bandas (agregado material × uso)"
        if banda_sel == "TODAS"
        else f"banda «{banda_sel}»"
    )
    st.caption(f"Gráficos para {titulo_banda}.")

    g1, g2 = st.columns(2)
    with g1:
        st.markdown("##### Distribución física por tipología")
        opts = opts_barras_tipologia(resumen_counts, horizontal=True)
        if opts:
            st_echarts(
                opts,
                height=f"{chart_h}px",
                key=f"pdna-barras-tip-h-{esquema}-{banda_sel}",
            )
    with g2:
        st.markdown("##### Necesidades de recuperación por tipología")
        cost_bar = mat_g.loc[mat_g["total"] > 0, ["tipologia", "costo_total_usd"]].rename(
            columns={"tipologia": "cat", "costo_total_usd": "costo_pdna_usd"}
        )
        if cost_bar.empty:
            cost_bar = mat_g[["tipologia", "costo_total_usd"]].rename(
                columns={"tipologia": "cat", "costo_total_usd": "costo_pdna_usd"}
            )
        opts_c = opts_barras_costo(
            cost_bar,
            col_cat="cat",
            col_val="costo_pdna_usd",
            top=min(16, len(cost_bar)),
            horizontal=True,
        )
        if opts_c:
            st_echarts(
                opts_c,
                height=f"{chart_h}px",
                key=f"pdna-barras-cost-h-{esquema}-{banda_sel}",
            )


def _render_matriz_con_databars(
    mat: pd.DataFrame,
    *,
    key_suffix: str = "mat",
    export_sheets: dict[str, pd.DataFrame] | None = None,
) -> None:
    export_df = _matriz_para_export(mat)
    show = export_df.rename(
        columns={
            "tipologia": "Tipología",
            "verde": "Verde",
            "amarillo": "Amarillo",
            "rojo": "Rojo",
            "negro": "Negro",
            "total": "Total",
            "dano_vivienda_usd": "Daño físico infraestructura (USD)",
            "dano_contenidos_usd": "Daño a contenidos (USD)",
            "costo_total_usd": "Necesidades de recuperación (USD)",
        }
    )
    for col in (
        "Daño físico infraestructura (USD)",
        "Daño a contenidos (USD)",
        "Necesidades de recuperación (USD)",
    ):
        show[col] = show[col].map(lambda x: fmt_es_money(float(round(float(x), 0))))

    col_cfg = {
        "Tipología": st.column_config.TextColumn("Tipología", width="large"),
        "Verde": st.column_config.NumberColumn("Verde", format="%d"),
        "Amarillo": st.column_config.NumberColumn("Amarillo", format="%d"),
        "Rojo": st.column_config.NumberColumn("Rojo", format="%d"),
        "Negro": st.column_config.NumberColumn("Negro", format="%d"),
        "Total": st.column_config.NumberColumn("Total", format="%d"),
        "Daño físico infraestructura (USD)": st.column_config.TextColumn(
            "Daño físico\ninfraestructura (USD)",
            help="Daño directo en vivienda (sin prima BBB).",
        ),
        "Daño a contenidos (USD)": st.column_config.TextColumn(
            "Daño a\ncontenidos (USD)",
            help="Mobiliario y enseres.",
        ),
        "Necesidades de recuperación (USD)": st.column_config.TextColumn(
            "Necesidades de\nrecuperación (USD)",
            help="Incluye Build Back Better.",
        ),
    }

    st.markdown("##### Matriz agregada · tipología × semáforo")
    st.caption(
        "Descargue el **Excel físico** (sin costos) con estado, municipio, parroquia, "
        "material, uso, banda y tipo de daño en columnas separadas, más totales por semáforo."
    )
    sheets = dict(export_sheets or {})
    sheets.setdefault("Matriz_tipologia_vista", matriz_fisica_desglosada(mat))
    d1, d2 = st.columns(2)
    with d1:
        download_excel_button(
            sheets,
            filename=f"pdna_matriz_fisica_{key_suffix}.xlsx",
            key=f"dl_pdna_mat_xlsx_{key_suffix}",
            label="Excel físico (sin costos)",
        )
    with d2:
        download_csv_button(
            export_df,
            filename=f"pdna_matriz_con_usd_{key_suffix}.csv",
            key=f"dl_pdna_mat_usd_{key_suffix}",
            label="Matriz con estimación USD (CSV)",
        )

    st.dataframe(
        show,
        width="stretch",
        hide_index=True,
        key=f"pdna_df_matriz_{key_suffix}",
        column_config=col_cfg,
    )


def page_pdna(df: pd.DataFrame, summary: dict | None = None) -> None:
    render_section(
        "Evaluación de necesidades post-desastre (PDNA)",
        "Insumos agregados para el equipo sectorial: unidades físicas, daño y necesidades de recuperación.",
    )

    work_geo = _filtros_territorio(df)
    esquema = _selector_esquema_tipologia()
    # Marco estrecho: una sola copia ligera (no duplicar las ~80 columnas del mart).
    work = marco_pdna_ligero(work_geo)
    if esquema == ESQUEMA_PDNA_EXCEL:
        esquema_calc = ESQUEMA_PDNA_EXCEL
    elif esquema == ESQUEMA_PDNA_PISO_A_PISO:
        esquema_calc = ESQUEMA_PDNA_PISO_A_PISO
    else:
        # Dinámico y Ampliado comparten reglas de altura; dinámico solo recorta filas.
        esquema_calc = ESQUEMA_PDNA_DETALLADO
    work = aplicar_tipologia_pdna(work, esquema=esquema_calc, copy=False)
    # Tipología también en el marco territorial completo (export Excel / daño estructural).
    work_geo = aplicar_tipologia_pdna(work_geo, esquema=esquema_calc, copy=True)
    params = _params_from_session()

    with st.spinner("Calculando efectos y necesidades…"):
        proj = proyectar_pdna(
            work,
            costo_m2=params["costo_m2"],
            factores_vivienda=params["factores_vivienda"],
            factores_contenidos=params["factores_contenidos"],
            ratio_contenidos=params["ratio_contenidos"],
            m2_por_piso=params["m2_por_piso"],
            area_minima=params["area_minima"],
            slim=False,  # work ya es ligero; no volver a recortar/copiar
        )

    mask_ok = proj["tipologia_pdna"].notna() & proj["etiqueta_n"].isin(
        ("VERDE", "AMARILLO", "ROJO", "NEGRO")
    )
    proj_ok = proj.loc[mask_ok]

    orden = tipos_pdna_orden(esquema_calc)
    solo_obs = esquema in (ESQUEMA_PDNA_OBSERVADO, ESQUEMA_PDNA_PISO_A_PISO)
    # Plantilla y Ampliado muestran el catálogo completo (ceros incluidos);
    # Piso a piso y Dinámico solo filas con unidades en el corte (evita cientos de filas vacías).
    incluir_vacias = esquema in (ESQUEMA_PDNA_EXCEL, ESQUEMA_PDNA_DETALLADO)
    mat = matriz_pdna_completa(
        proj,
        orden_tipologias=orden,
        solo_observadas=solo_obs,
        incluir_filas_vacias=incluir_vacias,
    )

    n_tips_distintas = int(proj_ok["tipologia_pdna"].nunique()) if not proj_ok.empty else 0
    _caption_esquema(esquema, mat, n_tips_distintas)

    n_unidades = int(len(proj_ok))

    et = proj_ok["etiqueta_n"].astype(str).str.upper() if not proj_ok.empty else pd.Series(dtype=str)
    n_verde = int((et == "VERDE").sum())
    n_amarillo = int((et == "AMARILLO").sum())
    n_rojo = int((et == "ROJO").sum())
    n_negro = int((et == "NEGRO").sum())
    n_criticos = n_rojo + n_negro
    tasa_critica = 100.0 * n_criticos / max(n_unidades, 1)

    tip_foco = "—"
    pct_tip = 0.0
    if not mat.empty and n_criticos > 0:
        crit_por_tip = (mat["rojo"].astype(int) + mat["negro"].astype(int)).astype(int)
        idx = int(crit_por_tip.idxmax())
        tip_foco = str(mat.loc[idx, "tipologia"])
        pct_tip = 100.0 * float(crit_por_tip.loc[idx]) / float(n_criticos)

    render_kpi_strip(
        [
            {
                "label": "Unidades físicas (muestra)",
                "value": fmt_es_int(n_unidades),
                "hint": "Con tipología PDNA en el corte",
            },
            {
                "label": "Daño crítico (Rojo + pérdida total)",
                "value": fmt_es_int(n_criticos),
                "tone": "warning",
                "hint": f"Rojo {fmt_es_int(n_rojo)} · Negro {fmt_es_int(n_negro)}",
            },
            {
                "label": "Tasa de daño crítico",
                "value": f"{tasa_critica:.1f}%",
                "tone": "flag" if tasa_critica >= 15 else "muted",
                "hint": f"Verde {fmt_es_int(n_verde)} · Amarillo {fmt_es_int(n_amarillo)}",
            },
            {
                "label": "Tipología más afectada",
                "value": tip_foco if len(tip_foco) <= 42 else tip_foco[:40] + "…",
                "tone": "hero",
                "hint": f"{pct_tip:.1f}% de las unidades críticas",
            },
        ]
    )

    st.markdown(
        _sintesis_html(
            n_inspecciones=n_unidades,
            n_criticos=n_criticos,
            tasa_critica=tasa_critica,
            n_verde=n_verde,
            tipologia_mas_afectada=tip_foco,
            pct_tipologia=pct_tip,
        ),
        unsafe_allow_html=True,
    )

    # Gráficos por banda (legibles) inmediatamente bajo la síntesis
    if not mat.empty:
        _render_graficos_pdna(mat, esquema=esquema_calc)

    export_sheets = construir_export_pdna_fisico(work_geo)

    tab_mat, tab_geo, tab_inf, tab_guia_sal, tab_guia, tab_met = st.tabs(
        [
            "Matriz de afectación y costos",
            "Por territorio",
            "Análisis 2.º nivel",
            "Guía de salidas",
            "Guía del modelo",
            "Método",
        ]
    )

    with tab_mat:
        if mat.empty:
            st.warning("No hay filas con tipología PDNA y semáforo válido en este corte.")
        else:
            _render_matriz_con_databars(
                mat,
                key_suffix=str(esquema),
                export_sheets=export_sheets,
            )

    with tab_geo:
        st.markdown("##### Agregación territorial")
        nivel = st.radio(
            "Nivel",
            ["estado_n", "municipio_n", "parroquia_n"],
            format_func=lambda x: {
                "estado_n": "Estado",
                "municipio_n": "Municipio",
                "parroquia_n": "Parroquia",
            }[x],
            horizontal=True,
            key="pdna_nivel_geo",
        )
        res = resumen_pdna_territorio(proj_ok, nivel=nivel)
        if res.empty:
            st.info("Sin datos territoriales en este corte.")
        else:
            show = res.rename(
                columns={
                    nivel: "Territorio",
                    "inspecciones": "Unidades",
                    "dano_vivienda_usd": "Infraestructura (USD)",
                    "dano_contenidos_usd": "Contenidos (USD)",
                    "costo_pdna_usd": "Necesidades (USD)",
                    "valor_reposicion_usd": "Valor reposición (USD)",
                }
            )
            for col in (
                "Infraestructura (USD)",
                "Contenidos (USD)",
                "Necesidades (USD)",
                "Valor reposición (USD)",
            ):
                if col in show.columns:
                    show[col] = show[col].map(lambda x: fmt_es_money(float(round(float(x), 0))))
            st.dataframe(show, width="stretch", hide_index=True)
            opts = opts_barras_costo(
                res.rename(columns={nivel: "cat"}),
                col_cat="cat",
                col_val="costo_pdna_usd",
            )
            if opts:
                st_echarts(opts, height="400px", key=f"pdna-geo-{nivel}")
            download_csv_button(
                res,
                filename="pdna_por_territorio.csv",
                key="dl_pdna_geo",
                label="Exportar agregación territorial (CSV)",
            )

    with tab_inf:
        from pdna_salidas import render_informe_ejecutivo_pdna

        render_informe_ejecutivo_pdna(
            work_geo,
            summary=summary or {},
            embebida=True,
        )

    with tab_guia_sal:
        from pdna_salidas import render_guia_salidas_reportes

        render_guia_salidas_reportes(embebida=True)

    with tab_guia:
        from page_pdna_guia import render_guia_modelo_valoracion

        render_guia_modelo_valoracion(embebida=True)

    with tab_met:
        st.markdown("##### Tipologías de la matriz")
        st.markdown(
            """
Las filas de la matriz se arman con estos **ejes**:

- **Material:** concreto, acero, mampostería formal / informal  
- **Uso:** casa · edificio · turismo · comercio (oficina incluida en comercio)  
- **Pisos:** piso a piso (1–20) o bandas, según esquema; valores &gt;60 se tratan como s/d  
- **Semáforo:** verde / amarillo / rojo / negro  

**Piso a piso (recomendado):** 1, 2, …, 20 pisos y cola «21 o más» (solo filas con unidades).  
**Ampliado:** casas 1 / 2 / 3+; edificios &lt;5 / 5–8 / 9–12 / 13+.  
**Plantilla sectorial (12 tipologías):** casas en «1-2 pisos»; edificios en «menor a 5» o «≥ 5».  
**Dinámico:** solo combinaciones presentes en el corte territorial.  
La descarga **Matriz física (sin costos)** entrega Material × Uso × Pisos × semáforo para que el equipo PDNA estime con sus propios parámetros.
            """
        )
        st.markdown("##### Catálogo del esquema activo")
        st.dataframe(
            pd.DataFrame(
                {"Orden": range(1, len(orden) + 1), "Tipología": list(orden)}
            ),
            width="stretch",
            hide_index=True,
        )
        cubiertos = int(work["tipologia_pdna"].notna().sum())
        st.caption(
            f"Cobertura en el corte: **{fmt_es_int(cubiertos)}** "
            f"({100.0 * cubiertos / max(len(work), 1):.1f} %). "
            f"Filas en matriz exportable: **{fmt_es_int(len(mat))}** "
            f"(sin contar TOTAL)."
        )
        with st.expander("Nota metodológica (PDNA Volume A)", expanded=False):
            st.markdown(
                """
**Efectos en infraestructura y activos físicos:** se cuantifican en unidades físicas y se
valoran a **costo de reposición**. La desagregación tipológica la define el sector vivienda
según el parque edificado local.

**Daño físico (infraestructura):** factor de semáforo acotado a 100 % del valor de reposición.

**Necesidades de recuperación:** incluyen la prima *Build Back Better* cuando el factor
supera 1.

**Fuera de alcance aquí:** pérdidas de producción, acceso a servicios e impacto macro.
                """
            )

    _panel_parametros()
