"""Páginas de análisis del BI Habitable (fases prompt completo)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit_echarts import st_echarts

from audit_fuzzy import detectar_conflictos_semaforo
from charts_habitable import (
    opts_apilado_territorio,
    opts_barras_costo,
    opts_barras_semaforo,
    opts_barras_tipologia,
    opts_heatmap_cramer,
    opts_sankey_anio_material_etiqueta,
)
from export_utils import download_csv_button, fmt_es_int, fmt_es_money
from pdna_costs import (
    COSTO_M2_DEFAULT,
    FACTORES_DEFAULT,
    M2_POR_PISO_DEFAULT,
    proyectar_pdna,
    resumen_pdna_territorio,
)
from process_habitable import (
    ETIQUETAS,
    cargar_csv,
    guardar_mart,
    mart_paths,
    procesar_dataframe,
    resumen_danos_pdna,
)
from stats_asociacion import (
    detalle_asociacion_vs_etiqueta,
    matriz_cramers_v,
    preparar_categoricas,
)
from ui_theme import render_kpi_strip, render_section


def fmt_n(n: float | int) -> str:
    return fmt_es_int(n)


def page_inicio(df: pd.DataFrame, summary: dict) -> None:
    render_section(
        "Resumen ejecutivo",
        "Corte Habitable filtrado · semáforo y cobertura (responde a filtros globales).",
    )
    counts = df["etiqueta_n"].value_counts()
    sem = {e: int(counts.get(e, 0)) for e in ETIQUETAS}
    render_kpi_strip(
        [
            {"label": "Inspecciones (filtro)", "value": fmt_n(len(df))},
            {
                "label": "Con GPS",
                "value": fmt_n(int(df["con_gps"].sum()) if "con_gps" in df.columns else 0),
            },
            {"label": "Verde", "value": fmt_n(sem["VERDE"]), "tone": "success"},
            {"label": "Amarillo", "value": fmt_n(sem["AMARILLO"]), "tone": "warning"},
            {"label": "Rojo + pérdida total", "value": fmt_n(sem["ROJO"] + sem["NEGRO"])},
        ]
    )
    st.caption(
        f"Fuente mart: **{summary.get('fuente', '—')}** · "
        f"Procesado: **{summary.get('corte_generado_en', '—')}**"
    )
    st_echarts(opts_barras_semaforo(sem), height="320px", key="hab-inicio-semaforo")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Top estados")
        top_e = df["estado_n"].value_counts().head(8).rename("Inspecciones").reset_index()
        top_e.columns = ["Estado", "Inspecciones"]
        st.dataframe(top_e, use_container_width=True, hide_index=True)
        download_csv_button(top_e, filename="top_estados.csv", key="dl_top_est")
    with c2:
        st.markdown("##### Riesgos marcados")
        rows = []
        for col, lab in [
            ("riesgo_externo", "Externo"),
            ("riesgo_severo", "Severo"),
            ("riesgo_moderado", "Moderado"),
            ("riesgo_componentes", "Componentes"),
            ("emergencia_gas", "Emergencia gas"),
        ]:
            if col in df.columns:
                rows.append({"Riesgo": lab, "Casos": int(df[col].fillna(False).sum())})
        riesgos = pd.DataFrame(rows)
        st.dataframe(riesgos, use_container_width=True, hide_index=True)
        download_csv_button(riesgos, filename="riesgos_flags.csv", key="dl_riesgos")


def page_carga(root: Path) -> None:
    render_section(
        "Cargar Habitable",
        "Suba el CSV de inspecciones. Se normalizan nulos, semáforo, territorio y tipología PDNA.",
    )
    up = st.file_uploader("CSV Habitable", type=["csv"], key="up_hab_csv")
    raw_dir = root / "data" / "uploads"
    raw_dir.mkdir(parents=True, exist_ok=True)

    default = Path(r"C:\Users\Angel\Downloads\habitable_inspecciones_2026-08-13_21-31-18.csv")
    usar_local = st.checkbox(
        "Usar CSV de muestra en Descargas (si existe)",
        value=default.is_file() and up is None,
    )

    if st.button("Procesar corte", type="primary"):
        try:
            if up is not None:
                dest = raw_dir / up.name
                dest.write_bytes(up.getvalue())
                fuente = up.name
                path = dest
            elif usar_local and default.is_file():
                path = default
                fuente = default.name
            else:
                st.error("Seleccione un CSV o active la muestra local.")
                return
            with st.spinner("Procesando…"):
                raw = cargar_csv(path)
                work, summary = procesar_dataframe(raw, fuente=fuente)
                guardar_mart(work, summary, root=root)
            st.success(
                f"Listo: **{fmt_n(len(work))}** inspecciones · "
                f"V {fmt_n(summary['semaforo']['VERDE'])} / "
                f"A {fmt_n(summary['semaforo']['AMARILLO'])} / "
                f"R {fmt_n(summary['semaforo']['ROJO'])} / "
                f"N {fmt_n(summary['semaforo']['NEGRO'])}"
            )
            st.cache_data.clear()
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(f"No se pudo procesar: {exc}")

    pq, meta = mart_paths(root)
    if pq.is_file():
        st.info(f"Mart actual: `{pq.name}` · meta `{meta.name}`")
    else:
        st.info("Aún no hay mart. Suba un CSV para continuar el análisis.")


def page_semaforo(df: pd.DataFrame) -> None:
    render_section("Semáforo", "Distribución de etiquetas de habitabilidad.")
    counts = df["etiqueta_n"].value_counts()
    st_echarts(opts_barras_semaforo(counts), height="360px", key="hab-semaforo")
    pct = (counts / max(counts.sum(), 1) * 100).round(1)
    tabla = pd.DataFrame(
        {
            "Etiqueta": list(ETIQUETAS),
            "Inspecciones": [int(counts.get(e, 0)) for e in ETIQUETAS],
            "%": [float(pct.get(e, 0.0)) for e in ETIQUETAS],
        }
    )
    st.dataframe(tabla, use_container_width=True, hide_index=True)
    download_csv_button(tabla, filename="semaforo.csv", key="dl_sem")


def page_territorio(df: pd.DataFrame) -> None:
    render_section("Territorio", "Mezcla de semáforo por estado / municipio / parroquia.")
    nivel = st.radio(
        "Nivel",
        ["estado_n", "municipio_n", "parroquia_n"],
        horizontal=True,
        format_func=lambda x: {
            "estado_n": "Estado",
            "municipio_n": "Municipio",
            "parroquia_n": "Parroquia",
        }[x],
    )
    opts = opts_apilado_territorio(df, nivel, top=15)
    if opts:
        st_echarts(opts, height="420px", key=f"hab-terr-{nivel}")
    else:
        st.warning("Sin datos para el territorio seleccionado.")
    ct = pd.crosstab(df[nivel], df["etiqueta_n"])
    download_csv_button(ct.reset_index(), filename=f"territorio_{nivel}.csv", key=f"dl_terr_{nivel}")


def page_danos(df: pd.DataFrame) -> None:
    render_section(
        "Tipología de daños",
        "Flags de riesgo del formulario ERD (externo, severo, moderado, componentes).",
    )
    flags = [
        ("riesgo_externo", "Riesgo externo"),
        ("riesgo_severo", "Riesgo severo"),
        ("riesgo_moderado", "Riesgo moderado"),
        ("riesgo_componentes", "Componentes"),
        ("emergencia_gas", "Emergencia gas"),
    ]
    rows = []
    for col, lab in flags:
        if col not in df.columns:
            continue
        mask = df[col].fillna(False)
        sub = df.loc[mask]
        row = {"Dimensión": lab, "Casos": int(mask.sum())}
        for e in ETIQUETAS:
            row[e] = int((sub["etiqueta_n"] == e).sum())
        rows.append(row)
    tabla = pd.DataFrame(rows)
    st.dataframe(tabla, use_container_width=True, hide_index=True)
    download_csv_button(tabla, filename="danos_flags.csv", key="dl_danos")

    st.markdown("##### Material × uso")
    mat = (
        df.assign(uso_g=df["uso_n"], mat_g=df["material_n"])
        .groupby(["mat_g", "uso_g"])
        .size()
        .reset_index(name="n")
        .sort_values("n", ascending=False)
        .head(25)
    )
    st.dataframe(mat, use_container_width=True, hide_index=True)
    download_csv_button(mat, filename="material_uso.csv", key="dl_mat_uso")


def page_pdna_conteos(df: pd.DataFrame) -> None:
    render_section(
        "Resumen daños · tipologías",
        "Matriz tipología constructiva × semáforo (referencia hoja Resumen daños PDNA).",
    )
    resumen = resumen_danos_pdna(df)
    if resumen.empty:
        st.warning("No hay filas con tipología PDNA derivable en el filtro actual.")
        return
    st_echarts(opts_barras_tipologia(resumen), height="480px", key="hab-pdna-tip")
    st.dataframe(resumen, use_container_width=True, hide_index=True)
    download_csv_button(resumen, filename="pdna_tipologias.csv", key="dl_pdna_tip")
    cubiertos = int(df["tipologia_pdna"].notna().sum())
    st.caption(
        f"Tipologías asignadas: **{fmt_n(cubiertos)}** de **{fmt_n(len(df))}** "
        f"({100.0 * cubiertos / max(len(df), 1):.1f} %)."
    )


def page_pdna_costos(df: pd.DataFrame) -> None:
    render_section(
        "Estimación PDNA (USD)",
        "Supuestos editables de recuperación. No sustituye avalúo de campo; "
        "factores VERDE 2 % · AMARILLO 25 % · ROJO 65 % · NEGRO 115 % (Build Back Better).",
    )
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        usd_conc = st.number_input("USD/m² concreto", value=float(COSTO_M2_DEFAULT["concreto"]), min_value=50.0)
    with c2:
        usd_ace = st.number_input("USD/m² acero", value=float(COSTO_M2_DEFAULT["acero"]), min_value=50.0)
    with c3:
        usd_mf = st.number_input(
            "USD/m² mamp. formal", value=float(COSTO_M2_DEFAULT["mampostería formal"]), min_value=50.0
        )
    with c4:
        usd_mi = st.number_input(
            "USD/m² mamp. informal", value=float(COSTO_M2_DEFAULT["mampostería informal"]), min_value=50.0
        )
    m2_piso = st.number_input("m² estimados por piso", value=float(M2_POR_PISO_DEFAULT), min_value=20.0)

    f1, f2, f3, f4 = st.columns(4)
    with f1:
        fv = st.number_input("Factor VERDE", value=float(FACTORES_DEFAULT["VERDE"]), min_value=0.0, max_value=2.0, format="%.2f")
    with f2:
        fa = st.number_input("Factor AMARILLO", value=float(FACTORES_DEFAULT["AMARILLO"]), min_value=0.0, max_value=2.0, format="%.2f")
    with f3:
        fr = st.number_input("Factor ROJO", value=float(FACTORES_DEFAULT["ROJO"]), min_value=0.0, max_value=2.0, format="%.2f")
    with f4:
        fn = st.number_input("Factor NEGRO", value=float(FACTORES_DEFAULT["NEGRO"]), min_value=0.0, max_value=2.0, format="%.2f")

    costos = {
        "concreto": usd_conc,
        "acero": usd_ace,
        "mampostería formal": usd_mf,
        "mampostería informal": usd_mi,
    }
    factores = {"VERDE": fv, "AMARILLO": fa, "ROJO": fr, "NEGRO": fn}
    with st.spinner("Proyectando PDNA…"):
        proj = proyectar_pdna(df, costo_m2=costos, factores=factores, m2_por_piso=m2_piso)

    total = float(proj["costo_pdna_usd"].sum())
    repos = float(proj["valor_reposicion_usd"].sum())
    k1, k2, k3 = st.columns(3)
    k1.metric("Costo PDNA estimado", fmt_es_money(total))
    k2.metric("Valor reposición (bruto)", fmt_es_money(repos))
    k3.metric("Inspecciones en cálculo", fmt_n(len(proj)))

    nivel = st.radio("Agregar por", ["municipio_n", "parroquia_n", "estado_n"], horizontal=True)
    res = resumen_pdna_territorio(proj, nivel=nivel)
    opts = opts_barras_costo(res.rename(columns={nivel: "cat"}), col_cat="cat", col_val="costo_pdna_usd")
    if opts:
        st_echarts(opts, height="400px", key=f"pdna-cost-{nivel}")
    st.dataframe(res, use_container_width=True, hide_index=True)
    download_csv_button(res, filename="pdna_costos_territorio.csv", key="dl_pdna_cost")
    download_csv_button(
        proj[
            [
                c
                for c in (
                    "id",
                    "etiqueta_n",
                    "estado_n",
                    "municipio_n",
                    "material_n",
                    "num_pisos",
                    "familia_material",
                    "area_m2_est",
                    "valor_reposicion_usd",
                    "factor_pdna",
                    "costo_pdna_usd",
                )
                if c in proj.columns
            ]
        ].head(50000),
        filename="pdna_costos_detalle.csv",
        key="dl_pdna_det",
        label="Descargar detalle (hasta 50 mil filas)",
    )


def page_auditoria(df: pd.DataFrame) -> None:
    render_section(
        "Auditoría de duplicados y conflictos",
        "Vecindad GPS (lat/lng redondeados) + similitud de nombre (token_set_ratio). "
        "Alerta crítica = mismo posible duplicado con semáforo distinto.",
    )
    umbral = st.slider("Umbral de similitud (%)", min_value=70, max_value=98, value=85, step=1)
    dec = st.selectbox("Decimales de celda geo", options=[3, 4], index=1)
    with st.spinner("Auditando emparejamientos…"):
        dups, alerta = detectar_conflictos_semaforo(df, umbral=float(umbral), decimales_geo=int(dec))

    c1, c2 = st.columns(2)
    c1.metric("Posibles duplicados (pares)", fmt_n(len(dups)))
    c2.metric("Alerta crítica (conflicto semáforo)", fmt_n(len(alerta)))

    st.markdown("##### Alerta crítica: conflicto de veredicto")
    if alerta.empty:
        st.success("No se detectaron conflictos de semáforo con el umbral actual.")
    else:
        show = alerta[
            [
                "similitud_pct",
                "id_a",
                "id_b",
                "nombre_a",
                "nombre_b",
                "etiqueta_a",
                "etiqueta_b",
                "inspector_a",
                "inspector_b",
            ]
        ].sort_values("similitud_pct", ascending=False)
        st.dataframe(show, use_container_width=True, hide_index=True)
        download_csv_button(show, filename="alerta_conflicto_semaforo.csv", key="dl_alerta")

    with st.expander("Todos los posibles duplicados", expanded=False):
        if dups.empty:
            st.info("Sin pares sobre el umbral.")
        else:
            st.dataframe(dups.head(2000), use_container_width=True, hide_index=True)
            download_csv_button(dups, filename="posibles_duplicados.csv", key="dl_dups")


def page_asociacion(df: pd.DataFrame) -> None:
    render_section(
        "Asociación categórica (V de Cramer)",
        "Dependencia entre variables discretas (no implica causalidad). "
        "Heatmap = matriz V; detalle = cada variable vs semáforo.",
    )
    with st.spinner("Calculando asociaciones…"):
        cat = preparar_categoricas(df)
        if cat.empty or len(cat) < 30:
            st.warning("Muestra insuficiente tras filtros para tests categóricos.")
            return
        mat = matriz_cramers_v(cat)
        det = detalle_asociacion_vs_etiqueta(cat)

    opts = opts_heatmap_cramer(mat)
    if opts:
        st_echarts(opts, height="480px", key="cramer-heat")
    st.dataframe(det, use_container_width=True, hide_index=True)
    download_csv_button(det, filename="cramer_vs_etiqueta.csv", key="dl_cramer")
    download_csv_button(mat.reset_index(), filename="cramer_matriz.csv", key="dl_cramer_mat")

    st.markdown("##### Flujo Sankey · año → material → semáforo")
    sankey = opts_sankey_anio_material_etiqueta(cat)
    if sankey:
        st_echarts(sankey, height="520px", key="sankey-causal")
    else:
        st.info("No hay datos suficientes para el Sankey.")
    st.caption(
        "Grosor de enlaces = conteo de inspecciones. "
        "Interpretar como patrón asociativo del corte filtrado."
    )
