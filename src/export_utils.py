"""Utilidades de exportación CSV / Excel (UTF-8 sin índice)."""

from __future__ import annotations

from io import BytesIO

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


def download_excel_button(
    sheets: dict[str, pd.DataFrame] | pd.DataFrame,
    *,
    filename: str,
    label: str = "Descargar Excel",
    key: str,
) -> None:
    """Descarga .xlsx; ``sheets`` puede ser un DataFrame o {nombre_hoja: df}."""
    if isinstance(sheets, pd.DataFrame):
        if sheets is None or sheets.empty:
            return
        book: dict[str, pd.DataFrame] = {"Datos": sheets}
    else:
        book = {k: v for k, v in sheets.items() if v is not None and not v.empty}
        if not book:
            return

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, df in book.items():
            safe = str(name).replace("/", "-")[:31] or "Hoja"
            df.to_excel(writer, sheet_name=safe, index=False)
    st.download_button(
        label=label,
        data=buf.getvalue(),
        file_name=filename if filename.lower().endswith(".xlsx") else f"{filename}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=key,
    )


def fmt_es_int(n: float | int) -> str:
    return f"{int(round(float(n))):,}".replace(",", ".")


def fmt_es_money(n: float | int, *, decimales: int = 0) -> str:
    if decimales <= 0:
        return f"USD {fmt_es_int(n)}"
    s = f"{float(n):,.{decimales}f}"
    return "USD " + s.replace(",", "§").replace(".", ",").replace("§", ".")
