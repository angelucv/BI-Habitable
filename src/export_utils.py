"""Utilidades de exportación CSV (UTF-8 sin índice)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


def download_csv_button(
    df: pd.DataFrame,
    *,
    filename: str,
    label: str = "Descargar CSV",
    key: str,
) -> None:
    """Botón de descarga ubicuo para tablas enriquecidas."""
    if df is None or df.empty:
        return
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=label,
        data=csv,
        file_name=filename,
        mime="text/csv",
        key=key,
    )


def fmt_es_int(n: float | int) -> str:
    return f"{int(round(float(n))):,}".replace(",", ".")


def fmt_es_money(n: float | int, *, decimales: int = 0) -> str:
    if decimales <= 0:
        return f"USD {fmt_es_int(n)}"
    s = f"{float(n):,.{decimales}f}"
    return "USD " + s.replace(",", "§").replace(".", ",").replace("§", ".")
