"""UI · Depuración / auditoría interna del mart Habitable."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from depuracion_datos import filas_de_grupo, resumen_depuracion, tabla_grupos
from export_utils import fmt_es_int
from ui_theme import render_kpi_strip, render_section


def page_depuracion(df: pd.DataFrame) -> None:
    render_section(
        "Depuración de datos",
        "Auditoría interna de multiplicidad: varias inspecciones que parecen el mismo lugar, "
        "y conflictos de semáforo dentro del mismo grupo.",
    )

    gps_label = st.selectbox(
        "Precisión GPS para agrupar el mismo lugar",
        options=[
            "Más estricto · ≈ 1 m (5 decimales · mismo edificio)",
            "Equilibrado · ≈ 11 m (4 decimales · misma manzana)",
            "Menos estricto · ≈ 110 m (3 decimales · entorno)",
        ],
        index=0,
        help=(
            "Más estricto = solo casi el mismo punto. "
            "Menos estricto = junta inspecciones más alejadas "
            "(más grupos, más riesgo de mezclar lugares distintos)."
        ),
        key="dep_gps_label",
    )
    gps_dec = {
        "Más estricto · ≈ 1 m (5 decimales · mismo edificio)": 5,
        "Equilibrado · ≈ 11 m (4 decimales · misma manzana)": 4,
        "Menos estricto · ≈ 110 m (3 decimales · entorno)": 3,
    }[gps_label]

    with st.spinner("Calculando grupos duplicados…"):
        res = resumen_depuracion(df, gps_decimals=gps_dec)

    render_kpi_strip(
        [
            {"label": "Inspecciones", "value": fmt_es_int(res["n_total"])},
            {
                "label": "Grupos mismo GPS",
                "value": fmt_es_int(res["gps_grupos"]),
                "tone": "warning" if res["gps_grupos"] else "",
            },
            {
                "label": "Filas en dups GPS",
                "value": fmt_es_int(res["gps_filas"]),
            },
            {
                "label": "Conflictos semáforo (GPS)",
                "value": fmt_es_int(res["gps_conflictos"]),
                "tone": "warning" if res["gps_conflictos"] else "",
            },
        ]
    )

    st.info(
        "**Qué revisamos:** un mismo edificio puede tener varias planillas (reinspección, "
        "doble carga o GPS compartido). Aquí no se borran datos: se **auditan** grupos "
        "sospechosos para que coordinación decida qué conservar.\n\n"
        f"- GPS válido: **{fmt_es_int(res['gps_ok'])}** · nombres útiles (no genéricos): "
        f"**{fmt_es_int(res['nombre_util'])}** · direcciones útiles: **{fmt_es_int(res['dir_util'])}**.\n"
        f"- Mismo nombre+municipio **y** GPS en la precisión elegida: "
        f"**{fmt_es_int(res['nombre_grupos'])}** grupos "
        f"({fmt_es_int(res['nombre_filas'])} filas; {fmt_es_int(res['nombre_conflictos'])} con semáforo distinto).\n"
        f"- Misma dirección+municipio **y** GPS cercano: **{fmt_es_int(res['dir_grupos'])}** grupos "
        f"({fmt_es_int(res['dir_filas'])} filas). Sin GPS válido no se alerta. "
        "Se excluyen textos genéricos (S/N, CASA, etc.)."
    )

    t1, t2, t3, t4 = st.tabs(
        [
            "1 · Mismo GPS",
            "2 · Nombre + municipio + GPS",
            "3 · Dirección + municipio + GPS",
            "4 · Conflictos de semáforo",
        ]
    )

    with t1:
        _panel_criterio(df, criterio="gps", gps_dec=gps_dec, titulo="Mismo punto GPS")
    with t2:
        _panel_criterio(
            df,
            criterio="nombre_mun",
            gps_dec=gps_dec,
            titulo="Mismo nombre + municipio + GPS cercano",
            nota=(
                "Solo cuenta si el nombre y el municipio coinciden **y** las coordenadas "
                "caen en la misma celda de la precisión GPS seleccionada. "
                "Mismo nombre en otro punto del municipio **no** genera alerta."
            ),
        )
    with t3:
        _panel_criterio(
            df,
            criterio="direccion_mun",
            gps_dec=gps_dec,
            titulo="Misma dirección + municipio + GPS cercano",
            nota=(
                "Misma lógica que nombre: dirección + municipio + GPS en la precisión elegida. "
                "Sin GPS válido no entra en el listado."
            ),
        )
    with t4:
        st.markdown("##### Grupos con **más de una etiqueta** de semáforo")
        st.caption(
            "Prioridad de auditoría: el mismo lugar aparece como VERDE y ROJO/NEGRO (u otras mezclas)."
        )
        crit = st.radio(
            "Criterio de agrupación",
            options=["gps", "nombre_mun", "direccion_mun"],
            format_func=lambda x: {
                "gps": "GPS",
                "nombre_mun": "Nombre + municipio + GPS",
                "direccion_mun": "Dirección + municipio + GPS",
            }[x],
            horizontal=True,
            key="dep_conf_crit",
        )
        g = tabla_grupos(df, criterio=crit, gps_decimals=gps_dec, solo_conflicto=True, min_n=2)
        if g.empty:
            st.success("Sin conflictos de semáforo con este criterio.")
        else:
            st.dataframe(_vista_grupos(g), use_container_width=True, hide_index=True)
            _detalle_grupo(df, criterio=crit, gps_dec=gps_dec, grupos=g, key_pref="dep_conf")


def _vista_grupos(g: pd.DataFrame) -> pd.DataFrame:
    cols = [
        c
        for c in (
            "clave",
            "n_insp",
            "n_etiquetas",
            "etiquetas",
            "conflicto_semaforo",
            "estados",
            "municipios",
            "nombre_ej",
            "dir_ej",
            "lat_ej",
            "lng_ej",
        )
        if c in g.columns
    ]
    return g[cols]


def _panel_criterio(
    df: pd.DataFrame,
    *,
    criterio: str,
    gps_dec: int,
    titulo: str,
    nota: str | None = None,
) -> None:
    st.markdown(f"##### {titulo}")
    if nota:
        st.caption(nota)
    c1, c2 = st.columns(2)
    with c1:
        min_n = st.number_input(
            "Mínimo de inspecciones por grupo",
            min_value=2,
            max_value=50,
            value=2,
            key=f"dep_min_{criterio}",
        )
    with c2:
        solo_c = st.checkbox(
            "Solo grupos con conflicto de semáforo",
            value=False,
            key=f"dep_solo_{criterio}",
        )
    g = tabla_grupos(
        df,
        criterio=criterio,  # type: ignore[arg-type]
        gps_decimals=gps_dec,
        solo_conflicto=solo_c,
        min_n=int(min_n),
    )
    if g.empty:
        st.info("No hay grupos duplicados con estos parámetros.")
        return
    st.caption(f"**{fmt_es_int(len(g))}** grupos · **{fmt_es_int(int(g['n_insp'].sum()))}** filas involucradas.")
    st.dataframe(_vista_grupos(g).head(500), use_container_width=True, hide_index=True)
    _detalle_grupo(df, criterio=criterio, gps_dec=gps_dec, grupos=g, key_pref=f"dep_{criterio}")


def _detalle_grupo(
    df: pd.DataFrame,
    *,
    criterio: str,
    gps_dec: int,
    grupos: pd.DataFrame,
    key_pref: str,
) -> None:
    opciones = grupos["clave"].astype(str).head(200).tolist()
    if not opciones:
        return
    clave = st.selectbox(
        "Inspeccionar un grupo (detalle de filas)",
        options=opciones,
        key=f"{key_pref}_sel",
    )
    det = filas_de_grupo(
        df,
        criterio=criterio,  # type: ignore[arg-type]
        clave=clave,
        gps_decimals=gps_dec,
    )
    st.markdown(f"**{fmt_es_int(len(det))}** inspecciones en el grupo seleccionado")
    st.dataframe(det, use_container_width=True, hide_index=True)
