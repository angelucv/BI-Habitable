"""
BI Habitable — Inicio · Análisis dimensional · Carga

  streamlit run app.py --server.port 8786
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from nav_schema import HOME_ID, resolve_nav  # noqa: E402
from page_analisis_dimensional import page_analisis_dimensional  # noqa: E402
from page_carga import page_carga  # noqa: E402
from page_depuracion import page_depuracion  # noqa: E402
from page_ejecutivo import page_ejecutivo  # noqa: E402
from page_explorar_perspective import page_explorar_perspective  # noqa: E402
from page_pdna import page_pdna  # noqa: E402
from page_pdna_guia import render_guia_modelo_valoracion  # noqa: E402
from process_habitable import mart_paths  # noqa: E402
from ui_theme import (  # noqa: E402
    inject_executive_css,
    render_hero,
    render_main_nav_grid,
    render_page_crumb,
    render_sidebar_nav,
)


st.set_page_config(
    page_title="BI Habitable · CPEH",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _init_state() -> None:
    st.session_state.setdefault("nav_item", HOME_ID)


@st.cache_data(show_spinner="Cargando mart Habitable…")
def load_mart() -> tuple[pd.DataFrame | None, dict]:
    pq, meta = mart_paths(ROOT)
    if not pq.is_file():
        return None, {}
    df = pd.read_parquet(pq)
    summary: dict = {}
    if meta.is_file():
        summary = json.loads(meta.read_text(encoding="utf-8"))
    return df, summary


def main() -> None:
    _init_state()
    inject_executive_css()
    active = render_sidebar_nav(st.session_state.get("nav_item", HOME_ID))
    st.session_state["nav_item"] = active

    df, summary = load_mart()
    tiene = df is not None and not df.empty

    with st.sidebar:
        st.markdown("---")
        if tiene:
            st.metric("Inspecciones", f"{len(df):,}".replace(",", "."))
            st.caption(summary.get("fuente", "mart local"))
        else:
            st.warning("Sin datos. Use **Cargar información**.")

    # Atajo compacto 2×2 también en pantalla
    render_main_nav_grid(active)

    sec, item = resolve_nav(active)
    if sec and item and active != HOME_ID:
        render_page_crumb(sec.label, item.label)

    if active == "carga_datos":
        render_hero(
            title="Cargar información",
            subtitle="Única entrada de datos del tablero.",
            kicker="Operación",
        )
        page_carga(ROOT)
        return

    if active == "dep_auditoria":
        render_hero(
            title="Depuración de datos",
            subtitle="Auditoría de multiplicidad y conflictos de semáforo en el mismo lugar.",
            kicker="Calidad de datos · Habitable",
        )
        if not tiene:
            st.info("Todavía no hay mart. Abra **Cargar información** en el menú.")
            return
        page_depuracion(df)
        return

    if active == "pdna_guia":
        render_hero(
            title="PDNA · Guía del modelo",
            subtitle="Explicación didáctica del modelo de valoración y de los parámetros a calibrar.",
            kicker="Post-Disaster Needs Assessment · Capacitación sectorial",
        )
        render_guia_modelo_valoracion()
        return

    if active == "pdna_matriz":
        render_hero(
            title="PDNA · Sector vivienda",
            subtitle="Matriz tipología × semáforo y estimación parametrizable de daños (vivienda + contenidos).",
            kicker="Post-Disaster Needs Assessment · Volume A",
        )
        if not tiene:
            st.info("Todavía no hay mart. Abra **Cargar información** en el menú.")
            return
        page_pdna(df, summary=summary)
        return

    if active == "explorar_perspective":
        render_hero(
            title="Explorar / cruces libres",
            subtitle="Perspective · pivotes y gráficos con año, pisos, uso y material.",
            kicker="Análisis libre · Habitable",
        )
        if not tiene:
            st.info("Todavía no hay mart. Abra **Cargar información** en el menú.")
            return
        page_explorar_perspective(df)
        return

    if active in {"dim_elementos", "dim_anio", "dim_pisos", "dim_uso", "dim_material"}:
        render_hero(
            title="Análisis dimensional",
            subtitle="Flujo ANIH, año, pisos, uso agrupado y material agrupado.",
            kicker="Comisión Presidencial · Evaluación de Habitabilidad",
        )
        if not tiene:
            st.info("Todavía no hay mart. Abra **Cargar información** en el menú.")
            return
        page_analisis_dimensional(df, initial_tab=active)
        return

    # Inicio
    render_hero(
        title="BI Habitable",
        subtitle="Panorama nacional de inspecciones · distribución por estado y semáforo.",
        kicker="Comisión Presidencial · Evaluación de Habitabilidad",
    )
    if not tiene:
        st.info("Todavía no hay mart. Abra **Cargar información** en el menú.")
        return
    page_ejecutivo(df, summary)


if __name__ == "__main__":
    main()
