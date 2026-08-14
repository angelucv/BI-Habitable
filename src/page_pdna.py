"""Sección PDNA — vista ejecutiva: KPIs, síntesis y matriz agregada."""

from __future__ import annotations

import html

import pandas as pd
import streamlit as st
from streamlit_echarts import st_echarts

from charts_habitable import opts_barras_costo, opts_barras_tipologia
from export_utils import download_csv_button, fmt_es_int
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
from process_habitable import (
    ESQUEMA_PDNA_DETALLADO,
    ESQUEMA_PDNA_EXCEL,
    ESQUEMA_PDNA_OBSERVADO,
    ESQUEMAS_PDNA_LABELS,
    aplicar_tipologia_pdna,
    resumen_danos_pdna,
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
    if prev == "excel_ejemplo" or (prev is not None and prev not in ESQUEMAS_PDNA_LABELS):
        st.session_state["pdna_esquema_tip"] = ESQUEMA_PDNA_EXCEL

    opciones = list(ESQUEMAS_PDNA_LABELS.keys())
    cortos = {
        ESQUEMA_PDNA_EXCEL: "Plantilla (12)",
        ESQUEMA_PDNA_DETALLADO: "Ampliado",
        ESQUEMA_PDNA_OBSERVADO: "Dinámico",
    }
    # Control segmentado horizontal (ahorro de espacio vertical)
    esquema = st.radio(
        "Combinaciones de filas",
        opciones,
        format_func=lambda k: cortos.get(k, ESQUEMAS_PDNA_LABELS[k]),
        horizontal=True,
        key="pdna_esquema_tip",
        label_visibility="collapsed",
        help="Plantilla · Ampliado (más bandas) · Dinámico (solo presentes)",
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
        st.markdown("**Costo de reposición de vivienda (USD/m²)**")
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

        st.markdown("**Factores de daño en vivienda** (estructural + no estructural)")
        st.caption("Negro > 1 incorpora Build Back Better en las necesidades de recuperación.")
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
    """12 filas canónicas + fila TOTAL (insumo ONU / PDNA)."""
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


def _render_matriz_con_databars(mat: pd.DataFrame, *, key_suffix: str = "mat") -> None:
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
        show[col] = show[col].map(lambda x: float(round(float(x), 0)))

    max_viv = max(float(mat["dano_vivienda_usd"].sum()), 1.0)
    max_cont = max(float(mat["dano_contenidos_usd"].sum()), 1.0)
    max_tot = max(float(mat["costo_total_usd"].sum()), 1.0)

    # Encabezados con salto de línea (word-wrap en cabecera de Streamlit)
    col_cfg = {
        "Tipología": st.column_config.TextColumn("Tipología", width="large"),
        "Verde": st.column_config.NumberColumn("Verde", format="%d"),
        "Amarillo": st.column_config.NumberColumn("Amarillo", format="%d"),
        "Rojo": st.column_config.NumberColumn("Rojo", format="%d"),
        "Negro": st.column_config.NumberColumn("Negro", format="%d"),
        "Total": st.column_config.NumberColumn("Total", format="%d"),
        "Daño físico infraestructura (USD)": st.column_config.ProgressColumn(
            "Daño físico\ninfraestructura (USD)",
            help="Pase el cursor para ver el monto. Daño directo en vivienda (sin prima BBB).",
            format="USD %d",
            min_value=0,
            max_value=max_viv,
        ),
        "Daño a contenidos (USD)": st.column_config.ProgressColumn(
            "Daño a\ncontenidos (USD)",
            help="Pase el cursor para ver el monto. Mobiliario y enseres.",
            format="USD %d",
            min_value=0,
            max_value=max_cont,
        ),
        "Necesidades de recuperación (USD)": st.column_config.ProgressColumn(
            "Necesidades de\nrecuperación (USD)",
            help="Pase el cursor para ver el monto. Incluye Build Back Better.",
            format="USD %d",
            min_value=0,
            max_value=max_tot,
        ),
    }

    h1, h2 = st.columns([3, 1])
    with h1:
        st.markdown("##### Matriz agregada · tipología × semáforo")
        st.caption("Insumo PDNA/ONU. Barras = peso financiero relativo; el valor exacto aparece al pasar el cursor.")
    with h2:
        st.markdown("<div style='height:0.55rem'></div>", unsafe_allow_html=True)
        download_csv_button(
            export_df,
            filename=f"pdna_matriz_agregada_{key_suffix}.csv",
            key=f"dl_pdna_mat_{key_suffix}",
            label="Exportar matriz (CSV)",
        )

    st.dataframe(
        show,
        width="stretch",
        hide_index=True,
        key=f"pdna_df_matriz_{key_suffix}",
        column_config=col_cfg,
    )


def page_pdna(df: pd.DataFrame) -> None:
    render_section(
        "Evaluación de necesidades post-desastre (PDNA)",
        "Insumos agregados para el equipo sectorial: unidades físicas, daño y necesidades de recuperación.",
    )

    work = _filtros_territorio(df)
    esquema = _selector_esquema_tipologia()
    # Marco estrecho: una sola copia ligera (no duplicar las ~80 columnas del mart).
    work = marco_pdna_ligero(work)
    esquema_calc = ESQUEMA_PDNA_EXCEL if esquema == ESQUEMA_PDNA_EXCEL else ESQUEMA_PDNA_DETALLADO
    work = aplicar_tipologia_pdna(work, esquema=esquema_calc, copy=False)
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
    solo_obs = esquema == ESQUEMA_PDNA_OBSERVADO
    # Plantilla y Ampliado muestran el catálogo completo (ceros incluidos);
    # Dinámico solo filas con unidades en el corte.
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

    # Gráficos horizontales inmediatamente bajo la síntesis (antes de la tabla)
    if not mat.empty:
        resumen_counts = resumen_danos_pdna(work)
        n_rows_chart = max(len(mat), 8)
        chart_h = int(min(56 + n_rows_chart * 28, 720))
        g1, g2 = st.columns(2)
        with g1:
            st.markdown("##### Distribución física por tipología")
            if not resumen_counts.empty:
                opts = opts_barras_tipologia(resumen_counts, horizontal=True)
                if opts:
                    st_echarts(opts, height=f"{chart_h}px", key=f"pdna-barras-tip-h-{esquema}")
        with g2:
            st.markdown("##### Necesidades de recuperación por tipología")
            cost_bar = mat.loc[mat["total"] > 0, ["tipologia", "costo_total_usd"]].rename(
                columns={"tipologia": "cat", "costo_total_usd": "costo_pdna_usd"}
            )
            if cost_bar.empty:
                cost_bar = mat[["tipologia", "costo_total_usd"]].rename(
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
                st_echarts(opts_c, height=f"{chart_h}px", key=f"pdna-barras-cost-h-{esquema}")

    tab_mat, tab_geo, tab_guia, tab_met = st.tabs(
        [
            "Matriz de afectación y costos",
            "Por territorio",
            "Guía del modelo",
            "Método",
        ]
    )

    with tab_mat:
        if mat.empty:
            st.warning("No hay filas con tipología PDNA y semáforo válido en este corte.")
        else:
            _render_matriz_con_databars(mat, key_suffix=str(esquema))

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
                    show[col] = show[col].map(lambda x: round(float(x), 0))
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

    with tab_guia:
        from page_pdna_guia import render_guia_modelo_valoracion

        render_guia_modelo_valoracion(embebida=True)

    with tab_met:
        st.markdown("##### Tipologías de la matriz")
        st.markdown(
            """
Las filas de la matriz se arman con estos **ejes**:

- **Material:** concreto, acero, mampostería formal / informal  
- **Uso:** casa vs edificio  
- **Pisos:** banda de altura (configurable según esquema)  
- **Semáforo:** verde / amarillo / rojo / negro  

**Plantilla sectorial (12 tipologías):** casas en «1-2 pisos»; edificios en «menor a 5» o «≥ 5».  
**Ampliado:** casas 1 / 2 / 3+; edificios menor a 5 / 5–8 / 9–12 / 13+.  
**Dinámico:** solo combinaciones presentes en el corte territorial.
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
