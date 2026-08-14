"""Explorar / cruces libres con Perspective (FINOS)."""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from clean_catalog import clasificar_material
from export_utils import fmt_es_int
from process_habitable import ETIQUETAS, etiqueta_display
from stats_asociacion import banda_pisos, quinquenio_anio
from ui_theme import render_section


def _anios(df: pd.DataFrame) -> pd.Series:
    if "anio_construccion_n" in df.columns:
        return pd.to_numeric(df["anio_construccion_n"], errors="coerce")
    if "anio_construccion" in df.columns:
        return pd.to_numeric(df["anio_construccion"], errors="coerce")
    return pd.Series(np.nan, index=df.index)


def _pisos(df: pd.DataFrame) -> pd.Series:
    if "num_pisos_n" in df.columns:
        return pd.to_numeric(df["num_pisos_n"], errors="coerce")
    if "num_pisos" in df.columns:
        return pd.to_numeric(df["num_pisos"], errors="coerce")
    return pd.Series(np.nan, index=df.index)


@st.cache_data(show_spinner="Preparando marco para Perspective…")
def marco_perspective(df: pd.DataFrame) -> pd.DataFrame:
    """
    Universo tipificado para cruces libres.
        Campos: semáforo, año (quinquenio), pisos (1…12 + 13 o más), uso y material agrupados.
    """
    work = df.loc[df["etiqueta_n"].isin(ETIQUETAS)].copy()
    mat_src = work["material_n"] if "material_n" in work.columns else work.get("material")
    uso = (
        work["uso_n"].fillna("Otros").astype(str)
        if "uso_n" in work.columns
        else pd.Series(["Otros"] * len(work), index=work.index)
    )
    out = pd.DataFrame(
        {
            "Semáforo": [etiqueta_display(x) for x in work["etiqueta_n"]],
            "Año (quinquenio)": [quinquenio_anio(x) for x in _anios(work)],
            "Número de pisos": [banda_pisos(x) for x in _pisos(work)],
            "Uso agrupado": uso,
            "Material (agrupado)": (
                [clasificar_material(x) for x in mat_src]
                if mat_src is not None
                else ["Otro / sin dato"] * len(work)
            ),
            "Inspecciones": 1,
        }
    )
    if "estado_n" in work.columns:
        out.insert(1, "Estado", work["estado_n"].astype(str))
    return out.reset_index(drop=True)


def _default_config() -> dict[str, Any]:
    return {
        "plugin": "Datagrid",
        "theme": "Pro Light",
        "group_by": ["Semáforo"],
        "split_by": [],
        "columns": ["Inspecciones"],
        "aggregates": {"Inspecciones": "sum"},
        "sort": [["Inspecciones", "desc"]],
    }


def _arrow_ipc_b64(df: pd.DataFrame) -> str:
    import base64

    import pyarrow as pa
    import pyarrow.ipc as ipc

    table = pa.Table.from_pandas(df, preserve_index=False)
    sink = pa.BufferOutputStream()
    with ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)
    return base64.b64encode(sink.getvalue().to_pybytes()).decode("ascii")


def _render_perspective_cdn(df: pd.DataFrame, *, height: int = 720) -> None:
    """Visor Perspective vía CDN (FINOS) con datos Arrow IPC."""
    payload_b64 = _arrow_ipc_b64(df)
    config_js = json.dumps(_default_config(), ensure_ascii=False)
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <script type="module" src="https://cdn.jsdelivr.net/npm/@finos/perspective@3.2.1/dist/cdn/perspective.js"></script>
  <script type="module" src="https://cdn.jsdelivr.net/npm/@finos/perspective-viewer@3.2.1/dist/cdn/perspective-viewer.js"></script>
  <script type="module" src="https://cdn.jsdelivr.net/npm/@finos/perspective-viewer-datagrid@3.2.1/dist/cdn/perspective-viewer-datagrid.js"></script>
  <script type="module" src="https://cdn.jsdelivr.net/npm/@finos/perspective-viewer-d3fc@3.2.1/dist/cdn/perspective-viewer-d3fc.js"></script>
  <link rel="stylesheet" crossorigin href="https://cdn.jsdelivr.net/npm/@finos/perspective-viewer@3.2.1/dist/css/pro.css" />
  <style>
    html, body {{ margin: 0; height: 100%; background: #f8fafc; }}
    perspective-viewer {{ width: 100%; height: {height}px; }}
  </style>
</head>
<body>
  <perspective-viewer id="viewer"></perspective-viewer>
  <script type="module">
    import perspective from "https://cdn.jsdelivr.net/npm/@finos/perspective@3.2.1/dist/cdn/perspective.js";
    const B64 = "{payload_b64}";
    const CONFIG = {config_js};
    const raw = Uint8Array.from(atob(B64), (c) => c.charCodeAt(0));
    const worker = await perspective.worker();
    const table = await worker.table(raw.buffer);
    const viewer = document.getElementById("viewer");
    await viewer.load(table);
    await viewer.restore(CONFIG);
  </script>
</body>
</html>"""
    components.html(html, height=height + 16, scrolling=True)


def page_explorar_perspective(df: pd.DataFrame) -> None:
    render_section(
        "Explorar / cruces libres",
        "Perspective: pivotee, filtre y grafique arrastrando campos. "
        "Universo: semáforo · año · pisos · uso agrupado · material agrupado.",
    )
    marco = marco_perspective(df)
    if marco.empty:
        st.warning("Sin filas tipificadas para explorar.")
        return

    st.caption(
        f"**{fmt_es_int(len(marco))}** inspecciones · **{len(marco.columns)}** campos. "
        "Sugerencia: agrupe por **Semáforo** o **Año (quinquenio)** y sume **Inspecciones**. "
        "Cambie el tipo de vista (tabla / barras / treemap) en el menú del visor."
    )
    with st.expander("Campos disponibles", expanded=False):
        st.write(", ".join(marco.columns.tolist()))

    # CDN = Perspective real (FINOS). El componente pip es opcional / frágil en Streamlit 1.61.
    _render_perspective_cdn(marco, height=740)
