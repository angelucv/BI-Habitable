"""Lienzo principal: cinco pestañas de decisión (prompt UX v2)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st
from streamlit_echarts import st_echarts

from charts_habitable import (
    opts_barras_grupos_uso,
    opts_barras_semaforo,
    opts_decada_apilada_pct,
    opts_donut_pdna,
    opts_heatmap_material_mun_severo,
    opts_pareto_uso,
    opts_sankey_material_falla_sem,
    opts_sunburst_estado_mun_sem,
)
from clean_catalog import resumen_calidad
from export_utils import download_csv_button, fmt_es_int, fmt_es_money
from pdna_costs import proyectar_pdna
from ui_theme import render_section

# Multiplicadores de reposición por uso (órdenes de magnitud relativos)
MULT_USO_PDNA: dict[str, float] = {
    "Salud": 3.5,
    "Educativo": 2.2,
    "Institucional": 2.0,
    "Industrial": 1.8,
    "Establecimientos turísticos": 1.8,
    "Comercio": 1.5,
    "Oficina": 1.5,  # compat → se fusiona con Comercio
    "Comercio / oficina": 1.5,  # compat marts antiguos
    "Mixto": 1.35,
    "Edificio": 1.25,
    "Casa": 1.0,
    "Vivienda sin dato de pisos": 1.1,
    "Otros": 1.0,
}

ETIQUETA_RGB = {
    "VERDE": [31, 107, 74],
    "AMARILLO": [180, 83, 9],
    "ROJO": [155, 44, 44],
    "NEGRO": [51, 65, 85],
}


def _ensure_session_df(df: pd.DataFrame) -> pd.DataFrame:
    if "df_editado" not in st.session_state:
        st.session_state["df_editado"] = None
    edited = st.session_state.get("df_editado")
    if isinstance(edited, pd.DataFrame) and not edited.empty:
        # Fusionar correcciones por id si existe
        if "id" in df.columns and "id" in edited.columns:
            base = df.set_index("id", drop=False)
            corr = edited.set_index("id", drop=False)
            for col in ("etiqueta_n", "municipio_n", "uso_n", "material_n"):
                if col in corr.columns and col in base.columns:
                    base.loc[corr.index.intersection(base.index), col] = corr.loc[
                        corr.index.intersection(base.index), col
                    ]
            return base.reset_index(drop=True)
    return df


def render_tablero_cinco_pestanas(df: pd.DataFrame, summary: dict[str, Any], n_total: int) -> None:
    """Arquitectura canónica de 5 pestañas sobre el corte filtrado."""
    df = _ensure_session_df(df)
    tabs = st.tabs(
        [
            "1 · Comando ejecutivo",
            "2 · Auditoría QA",
            "3 · Disección estructural",
            "4 · Patrones forenses",
            "5 · PDNA económico",
        ]
    )

    with tabs[0]:
        _tab_comando(df, n_total)
    with tabs[1]:
        _tab_auditoria(df, summary)
    with tabs[2]:
        _tab_estructural(df)
    with tabs[3]:
        _tab_forense(df)
    with tabs[4]:
        _tab_pdna(df)


def _tab_comando(df: pd.DataFrame, n_total: int) -> None:
    render_section(
        "Comando ejecutivo",
        "Visión general del corte filtrado y nube geográfica coloreada por semáforo.",
    )
    n = len(df)
    verd = int((df["etiqueta_n"] == "VERDE").sum())
    letal = int(df["etiqueta_n"].isin(["ROJO", "NEGRO"]).sum())
    muns = int(df["municipio_n"].nunique()) if "municipio_n" in df.columns else 0
    pct_v = 100.0 * verd / max(n, 1)
    pct_l = 100.0 * letal / max(n, 1)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Inspecciones (corte)", fmt_es_int(n))
    c2.metric("% Habitable (VERDE)", f"{pct_v:.1f} %")
    c3.metric("% Riesgo letal (R+N)", f"{pct_l:.1f} %")
    c4.metric("Municipios en corte", fmt_es_int(muns))
    st.caption(f"Universo del mart: **{fmt_es_int(n_total)}** · proporción activa **{100.0 * n / max(n_total, 1):.1f} %**")

    counts = df["etiqueta_n"].value_counts()
    st_echarts(opts_barras_semaforo(counts), height="300px", key="tab1-sem")

    geo = df.loc[df.get("geo_valida", df.get("con_gps", False))].copy() if n else df
    if "lat" in geo.columns and "lng" in geo.columns and not geo.empty:
        render_section("Mapa de inspecciones", "Color = semáforo de campo (muestra hasta 8.000 puntos).")
        sample = geo.head(8000)
        try:
            import pydeck as pdk

            def _rgba(et: str) -> list[int]:
                rgb = ETIQUETA_RGB.get(str(et).upper(), [100, 116, 139])
                return [*rgb, 180]

            plot = sample[["lat", "lng", "etiqueta_n"]].dropna().copy()
            plot["color"] = plot["etiqueta_n"].map(_rgba)
            layer = pdk.Layer(
                "ScatterplotLayer",
                data=plot,
                get_position="[lng, lat]",
                get_fill_color="color",
                get_radius=45,
                radius_min_pixels=2,
                radius_max_pixels=8,
                pickable=True,
            )
            view = pdk.ViewState(
                latitude=float(plot["lat"].median()),
                longitude=float(plot["lng"].median()),
                zoom=9,
                pitch=0,
            )
            st.pydeck_chart(
                pdk.Deck(
                    layers=[layer],
                    initial_view_state=view,
                    tooltip={"text": "Semáforo: {etiqueta_n}"},
                    map_style="light",
                ),
                use_container_width=True,
            )
        except Exception:
            st.map(sample.rename(columns={"lat": "lat", "lng": "lon"})[["lat", "lon"]], size=8)
    else:
        st.info("Sin coordenadas válidas en el filtro actual.")


def _tab_auditoria(df: pd.DataFrame, summary: dict[str, Any]) -> None:
    render_section(
        "Auditoría y aseguramiento de calidad",
        "Eficacia de la reducción de cardinalidad de uso y diagnóstico de nulos.",
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Cardinalidad uso (antes)", fmt_es_int(summary.get("uso_cardinalidad_antes", 0)))
    c2.metric("Cardinalidad uso (después)", fmt_es_int(summary.get("uso_cardinalidad_despues", 0)))
    c3.metric("Sin GPS / fuera VE", fmt_es_int(summary.get("n_sin_gps_o_fuera_ve", 0)))

    pareto = pd.DataFrame(summary.get("uso_pareto") or [])
    if not pareto.empty:
        st.markdown("##### Pareto de uso · antes vs después")
        opts = opts_pareto_uso(pareto)
        if opts:
            st_echarts(opts, height="380px", key="qa-pareto")
    if "uso_grupo" in df.columns:
        st.markdown("##### Distribución de supercategorías (corte)")
        st_echarts(
            opts_barras_grupos_uso(df["uso_grupo"].value_counts()),
            height="320px",
            key="qa-grupos",
        )

    cols_qa = [
        "etiqueta_n",
        "estado_n",
        "municipio_n",
        "uso_raw_n",
        "uso_grupo",
        "material_n",
        "anio_construccion_n",
        "lat",
        "lng",
        "nombre_edificacion",
    ]
    diag = resumen_calidad(df, cols_qa)
    st.markdown("##### Densidad de no asignados")
    st.dataframe(diag, use_container_width=True, hide_index=True)
    download_csv_button(diag, filename="qa_nulos.csv", key="dl_qa")

    # Duplicados volumétricos (nombre + celda geo gruesa)
    if {"nombre_edificacion", "lat", "lng"}.issubset(df.columns):
        tmp = df.copy()
        tmp["_k"] = (
            tmp["nombre_edificacion"].astype(str).str.upper().str.strip()
            + "|"
            + tmp["lat"].round(4).astype(str)
            + "|"
            + tmp["lng"].round(4).astype(str)
        )
        dups = int(tmp["_k"].duplicated().sum())
        st.metric("Filas con clave nombre+geo repetida", fmt_es_int(dups))

    st.markdown("##### Corrección asistida (muestra editable)")
    st.caption(
        "Edite anomalías residuales; al guardar se aplican sobre el corte de la sesión "
        "(por `id`) y refrescan el resto del tablero."
    )
    cols_edit = [c for c in ("id", "nombre_edificacion", "etiqueta_n", "municipio_n", "uso_n", "material_n") if c in df.columns]
    sample = df.loc[df["uso_grupo"].eq("Otros")].head(200) if "uso_grupo" in df.columns else df.head(200)
    if sample.empty:
        sample = df.head(200)
    edited = st.data_editor(
        sample[cols_edit],
        use_container_width=True,
        num_rows="fixed",
        key="editor_qa",
        disabled=["id"] if "id" in cols_edit else [],
    )
    if st.button("Aplicar correcciones al tablero", type="primary"):
        st.session_state["df_editado"] = edited
        st.success("Correcciones aplicadas a la sesión.")
        st.rerun()


def _tab_estructural(df: pd.DataFrame) -> None:
    render_section(
        "Disección estructural",
        "Sunburst Estado→Municipio→Semáforo y resiliencia por década de construcción.",
    )
    sun = opts_sunburst_estado_mun_sem(df)
    if sun:
        st_echarts(sun, height="520px", key="sunburst")
    else:
        st.warning("Sin datos para sunburst.")

    st.markdown("##### Década de construcción × mezcla de semáforo (100 %)")
    dec = opts_decada_apilada_pct(df)
    if dec:
        st_echarts(dec, height="400px", key="decada")
        st.caption(
            "Lectura orientativa de resiliencia histórica frente a códigos sísmicos; "
            "no atribuye causalidad sola al año de construcción."
        )
    else:
        st.info("Pocos años de construcción válidos en el filtro.")


def _tab_forense(df: pd.DataFrame) -> None:
    render_section(
        "Patrones y patologías",
        "Sankey material → modo de falla → semáforo; heatmap de afectación severa.",
    )
    sankey = opts_sankey_material_falla_sem(df)
    if sankey:
        st_echarts(sankey, height="480px", key="sankey-falla")
    heat = opts_heatmap_material_mun_severo(df)
    if heat:
        st.markdown("##### Intensidad de afectación severa · material × municipio")
        st_echarts(heat, height="420px", key="heat-sev")


def _tab_pdna(df: pd.DataFrame) -> None:
    render_section(
        "Proyección económica PDNA",
        "Pérdida operativa (ROJO+NEGRO) × uso limpio, con multiplicadores sectoriales.",
    )
    perdida = df.loc[df["etiqueta_n"].isin(["ROJO", "NEGRO"])].copy()
    if perdida.empty:
        st.warning("No hay registros ROJO/NEGRO en el filtro actual.")
        return

    base = proyectar_pdna(perdida)
    mult = base["uso_n"].map(lambda u: float(MULT_USO_PDNA.get(str(u), 1.0)))
    base["mult_uso"] = mult
    base["costo_recuperacion_usd"] = base["costo_pdna_usd"] * base["mult_uso"]

    total = float(base["costo_recuperacion_usd"].sum())
    st.metric("Costo de recuperación proyectado (R+N)", fmt_es_money(total))

    tabla = (
        base.groupby("uso_n", as_index=False)
        .agg(
            inspecciones=("costo_recuperacion_usd", "size"),
            costo_base_usd=("costo_pdna_usd", "sum"),
            costo_recuperacion_usd=("costo_recuperacion_usd", "sum"),
        )
        .sort_values("costo_recuperacion_usd", ascending=False)
    )
    st.dataframe(
        tabla,
        use_container_width=True,
        hide_index=True,
        column_config={
            "uso_n": "Uso (grupo)",
            "inspecciones": st.column_config.NumberColumn("Inspecciones", format="%d"),
            "costo_base_usd": st.column_config.NumberColumn("Costo base USD", format="$%.0f"),
            "costo_recuperacion_usd": st.column_config.NumberColumn(
                "Recuperación proyectada USD", format="$%.0f"
            ),
        },
    )
    download_csv_button(tabla, filename="pdna_por_uso.csv", key="dl_pdna_uso")

    donut = opts_donut_pdna(tabla, col_cat="uso_n", col_val="costo_recuperacion_usd")
    if donut:
        st_echarts(donut, height="400px", key="donut-pdna")
    st.caption(
        "Multiplicadores ilustrativos (Salud 3,5× … Casa 1× · Edificio 1,25×). "
        "Ajuste fino de USD/m² en la sección PDNA detallada si se requiere."
    )
