"""Sección Análisis dimensional: año · pisos · uso · material · flujo."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from page_dimension_anio import render_dimension_anio
from page_dimension_nominal import render_dimension_material, render_dimension_uso
from page_dimension_pisos import render_dimension_pisos
from page_ejecutivo import _inject_css, _tab_elementos
from ui_theme import render_section

_DIM_OPTS: tuple[tuple[str, str], ...] = (
    ("dim_anio", "1 · Año"),
    ("dim_pisos", "2 · Pisos"),
    ("dim_uso", "3 · Uso"),
    ("dim_material", "4 · Material"),
    ("dim_elementos", "5 · Flujo"),
)


def page_analisis_dimensional(df: pd.DataFrame, *, initial_tab: str | None = None) -> None:
    """Menú en pastillas redondeadas (como las pestañas anteriores)."""
    _inject_css()
    render_section(
        "Análisis dimensional",
        "Cruce de dimensiones de la edificación con el semáforo y la pérdida total.",
    )

    ids = [i for i, _ in _DIM_OPTS]
    st.session_state.setdefault("ad_choice", "dim_anio")
    # Solo alinear con el menú lateral cuando cambia el ítem de nav.
    if initial_tab in ids and st.session_state.get("_ad_nav_sync") != initial_tab:
        st.session_state["ad_choice"] = initial_tab
        st.session_state["_ad_nav_sync"] = initial_tab

    cols = st.columns(len(_DIM_OPTS), gap="small")
    for col, (cid, lab) in zip(cols, _DIM_OPTS):
        on = st.session_state["ad_choice"] == cid
        with col:
            if st.button(
                lab,
                key=f"ad_pill_{cid}",
                use_container_width=True,
                type="primary" if on else "secondary",
            ):
                st.session_state["ad_choice"] = cid
                st.session_state["nav_item"] = cid
                st.session_state["_ad_nav_sync"] = cid
                st.rerun()

    choice = st.session_state["ad_choice"]
    if choice == "dim_elementos":
        _tab_elementos(df)
    elif choice == "dim_anio":
        render_dimension_anio(df)
    elif choice == "dim_pisos":
        render_dimension_pisos(df)
    elif choice == "dim_uso":
        render_dimension_uso(df)
    else:
        render_dimension_material(df)
