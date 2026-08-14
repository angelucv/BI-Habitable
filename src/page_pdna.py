"""Sección PDNA — vista ejecutiva: KPIs, síntesis y matriz agregada."""

from __future__ import annotations

import html

import pandas as pd
import streamlit as st
from streamlit_echarts import st_echarts

from charts_habitable import opts_barras_costo, opts_barras_tipologia
from export_utils import download_csv_button, fmt_es_int, fmt_es_money
from pdna_costs import (
    AREA_MINIMA_DEFAULT,
    COSTO_M2_DEFAULT,
    FACTORES_CONTENIDOS_DEFAULT,
    FACTORES_VIVIENDA_DEFAULT,
    M2_POR_PISO_DEFAULT,
    RATIO_CONTENIDOS_DEFAULT,
    kpis_pdna,
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
    st.markdown("##### Esquema de tipologías de la matriz")
    st.caption(
        "La plantilla Excel es una **referencia de presentación**, no un catálogo cerrado. "
        "Las variables del cruce son material × uso (casa/edificio) × banda de pisos × semáforo. "
        "Los pisos sí son variables: puede usar el ejemplo de 12 filas o bandas más detalladas."
    )
    opciones = list(ESQUEMAS_PDNA_LABELS.keys())
    st.session_state.setdefault("pdna_esquema_tip", ESQUEMA_PDNA_EXCEL)
    return st.radio(
        "Combinaciones de filas",
        opciones,
        format_func=lambda k: ESQUEMAS_PDNA_LABELS[k],
        horizontal=False,
        key="pdna_esquema_tip",
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


def _fmt_money_plain(n: float) -> str:
    return fmt_es_int(n)


def _sintesis_html(
    *,
    n_inspecciones: int,
    total_dano: float,
    total_necesidades: float,
    tipologia_mas_costosa: str,
    porcentaje_costo: float,
) -> str:
    tip = html.escape(tipologia_mas_costosa)
    return f"""
<div class="pdna-exec-summary">
  <h3>Resumen de Necesidades de Recuperación (PDNA)</h3>
  <p>En el corte territorial seleccionado, se han cuantificado los efectos sobre los activos
  físicos de <strong>{fmt_es_int(n_inspecciones)}</strong> unidades habitacionales.</p>
  <p>Utilizando el costo de reposición parametrizado, el <strong>Daño Físico Directo</strong>
  (infraestructura + contenidos) se estima en
  <strong>USD {_fmt_money_plain(total_dano)}</strong>.
  Al incorporar los factores de mitigación de riesgo y mejoras estructurales requeridas por
  la metodología internacional (<em>Build Back Better</em>), las
  <strong>Necesidades Totales de Recuperación</strong> para el sector vivienda ascienden a
  <strong>USD {_fmt_money_plain(total_necesidades)}</strong>.</p>
  <ul>
    <li><strong>Foco de Inversión:</strong> el modelo financiero indica que la mayor
    concentración de capital deberá destinarse a la recuperación de estructuras de
    <strong>{tip}</strong>, las cuales representan el
    <strong>{porcentaje_costo:.1f}%</strong> del presupuesto total estimado.</li>
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


def _render_matriz_con_databars(mat: pd.DataFrame) -> None:
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

    st.dataframe(
        show,
        width="stretch",
        hide_index=True,
        column_config={
            "Tipología": st.column_config.TextColumn("Tipología", width="large"),
            "Verde": st.column_config.NumberColumn("Verde", format="%d"),
            "Amarillo": st.column_config.NumberColumn("Amarillo", format="%d"),
            "Rojo": st.column_config.NumberColumn("Rojo", format="%d"),
            "Negro": st.column_config.NumberColumn("Negro", format="%d"),
            "Total": st.column_config.NumberColumn("Total", format="%d"),
            "Daño físico infraestructura (USD)": st.column_config.ProgressColumn(
                "Daño físico infraestructura (USD)",
                help="Daño directo en vivienda (sin prima BBB). Barra = peso sobre el total.",
                format="USD %.0f",
                min_value=0,
                max_value=max_viv,
            ),
            "Daño a contenidos (USD)": st.column_config.ProgressColumn(
                "Daño a contenidos (USD)",
                help="Mobiliario y enseres. Barra = peso sobre el total.",
                format="USD %.0f",
                min_value=0,
                max_value=max_cont,
            ),
            "Necesidades de recuperación (USD)": st.column_config.ProgressColumn(
                "Necesidades de recuperación (USD)",
                help="Incluye Build Back Better. Barra = peso sobre el presupuesto total.",
                format="USD %.0f",
                min_value=0,
                max_value=max_tot,
            ),
        },
    )
    download_csv_button(
        export_df,
        filename="pdna_matriz_agregada.csv",
        key="dl_pdna_mat",
        label="Exportar matriz agregada (CSV)",
    )


def page_pdna(df: pd.DataFrame) -> None:
    render_section(
        "Evaluación de necesidades post-desastre (PDNA)",
        "Insumos agregados para el equipo sectorial: unidades físicas, daño y necesidades de recuperación.",
    )

    work = _filtros_territorio(df)
    esquema = _selector_esquema_tipologia()
    # Recalcular tipología según esquema (la del mart sigue siendo el ejemplo Excel).
    esquema_calc = ESQUEMA_PDNA_EXCEL if esquema == ESQUEMA_PDNA_EXCEL else ESQUEMA_PDNA_DETALLADO
    work = aplicar_tipologia_pdna(work, esquema=esquema_calc)
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
        )

    proj_ok = proj.loc[
        proj["tipologia_pdna"].notna()
        & proj["etiqueta_n"].isin(("VERDE", "AMARILLO", "ROJO", "NEGRO"))
    ].copy()
    k = kpis_pdna(proj_ok)

    orden = tipos_pdna_orden(esquema_calc)
    solo_obs = esquema == ESQUEMA_PDNA_OBSERVADO
    incluir_vacias = esquema == ESQUEMA_PDNA_EXCEL
    mat = matriz_pdna_completa(
        proj,
        orden_tipologias=orden,
        solo_observadas=solo_obs,
        incluir_filas_vacias=incluir_vacias,
    )

    n_unidades = int(k["n_con_tipologia"])
    tip_foco = "—"
    pct_foco = 0.0
    if not mat.empty and float(mat["costo_total_usd"].sum()) > 0:
        top = mat.sort_values("costo_total_usd", ascending=False).iloc[0]
        tip_foco = str(top["tipologia"])
        pct_foco = 100.0 * float(top["costo_total_usd"]) / float(mat["costo_total_usd"].sum())

    render_kpi_strip(
        [
            {
                "label": "Unidades físicas (muestra)",
                "value": fmt_es_int(n_unidades),
                "hint": "Unidades habitacionales cuantificadas",
            },
            {
                "label": "Daño físico (infraestructura)",
                "value": fmt_es_money(k["dano_vivienda_directo"]),
                "tone": "warning",
                "hint": "Reposición vivienda · sin prima BBB",
            },
            {
                "label": "Daño a contenidos",
                "value": fmt_es_money(k["dano_contenidos"]),
                "tone": "flag",
                "hint": "Mobiliario y enseres",
            },
            {
                "label": "Necesidades de recuperación (incluye BBB)",
                "value": fmt_es_money(k["necesidades_recuperacion"]),
                "tone": "hero",
                "hint": "Cifra clave para movilización de recursos",
            },
        ]
    )

    st.markdown(
        _sintesis_html(
            n_inspecciones=n_unidades,
            total_dano=float(k["dano_fisico_directo"]),
            total_necesidades=float(k["necesidades_recuperacion"]),
            tipologia_mas_costosa=tip_foco,
            porcentaje_costo=pct_foco,
        ),
        unsafe_allow_html=True,
    )

    tab_mat, tab_geo, tab_guia, tab_met = st.tabs(
        [
            "Matriz de afectación y costos",
            "Por territorio",
            "Guía del modelo",
            "Método",
        ]
    )

    with tab_mat:
        st.markdown("##### Matriz agregada · tipología × semáforo")
        st.caption(
            f"Esquema activo: **{ESQUEMAS_PDNA_LABELS.get(esquema, esquema)}**. "
            "Insumo para el equipo PDNA/ONU. Las barras indican el peso financiero relativo."
        )
        if mat.empty:
            st.warning("No hay filas con tipología PDNA y semáforo válido en este corte.")
        else:
            _render_matriz_con_databars(mat)
            resumen_counts = resumen_danos_pdna(work)
            if not resumen_counts.empty:
                with st.expander("Distribución física (gráfico)", expanded=False):
                    opts = opts_barras_tipologia(resumen_counts)
                    if opts:
                        st_echarts(opts, height="420px", key="pdna-barras-tip")
            cost_bar = mat[["tipologia", "costo_total_usd"]].rename(
                columns={"tipologia": "cat", "costo_total_usd": "costo_pdna_usd"}
            )
            opts_c = opts_barras_costo(cost_bar, col_cat="cat", col_val="costo_pdna_usd", top=12)
            if opts_c:
                with st.expander("Necesidades por tipología (gráfico)", expanded=False):
                    st_echarts(opts_c, height="380px", key="pdna-barras-cost-tip")

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
        st.markdown("##### ¿Las 12 filas del Excel son las únicas?")
        st.markdown(
            """
No. La hoja dice explícitamente que es una **referencia de cómo presentar** resultados,
no un listado cerrado que haya que llenar a mano.

**Lo que sí es estable (ejes del cruce):**
- Material: concreto, acero, mampostería formal / informal  
- Uso: casa vs edificio  
- Pisos: **variable** (el Excel solo muestra un ejemplo de bandas)  
- Semáforo: verde / amarillo / rojo / negro  
- Costos: daño vivienda + contenidos (y aquí, necesidades con BBB)

**Pisos en el ejemplo Excel:** casas siempre «1-2 pisos»; edificios «menor a 5» o «≥ 5».
Eso comprime la altura real. Con el esquema **Ampliado** la matriz abre más bandas
(casas 1 / 2 / 3+; edificios menor a 5 / 5–8 / 9–12 / 13+). Con **Dinámico** solo salen
combinaciones presentes en el corte territorial.
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
según el parque edificado local; Volume A no fija las 12 filas del Excel de ejemplo.

**Daño físico (infraestructura):** factor de semáforo acotado a 100 % del valor de reposición.

**Necesidades de recuperación:** incluyen la prima *Build Back Better* cuando el factor
supera 1.

**Fuera de alcance aquí:** pérdidas de producción, acceso a servicios e impacto macro.
                """
            )

    _panel_parametros()
