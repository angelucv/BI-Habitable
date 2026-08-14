"""Carga del CSV Habitable (única operación de datos)."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from export_utils import fmt_es_int
from process_habitable import cargar_csv, guardar_mart, mart_paths, procesar_dataframe
from ui_theme import render_section


def page_carga(root: Path) -> None:
    render_section(
        "Cargar información",
        "Suba el CSV de inspecciones Habitable. Se normaliza territorio, uso y semáforo.",
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
                f"Listo: **{fmt_es_int(len(work))}** inspecciones · "
                f"V {fmt_es_int(summary['semaforo']['VERDE'])} / "
                f"A {fmt_es_int(summary['semaforo']['AMARILLO'])} / "
                f"R {fmt_es_int(summary['semaforo']['ROJO'])} / "
                f"N {fmt_es_int(summary['semaforo']['NEGRO'])}"
            )
            st.cache_data.clear()
            st.session_state["nav_item"] = "home"
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(f"No se pudo procesar: {exc}")

    pq, meta = mart_paths(root)
    if pq.is_file():
        st.info(f"Mart disponible: `{pq.name}`")
    else:
        st.warning("Aún no hay datos. Suba un CSV para abrir la vista ejecutiva.")
