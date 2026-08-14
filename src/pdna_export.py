"""Exportación Excel PDNA: dimensiones separadas + totales por semáforo."""

from __future__ import annotations

from typing import Any

import pandas as pd

from anih_logic import riesgo_componentes_series, riesgo_severo_series
from process_habitable import (
    ETIQUETAS,
    desglosar_tipologia_pdna,
    enriquecer_desglose_tipologia,
    etiqueta_display,
)


def clasificar_tipo_dano(df: pd.DataFrame) -> pd.Series:
    """Clasifica daño estructural vs no estructural (ANIH: severo vs componentes)."""
    sev = riesgo_severo_series(df)
    comp = riesgo_componentes_series(df)
    colapso = pd.Series(False, index=df.index)
    if "ext_colapso_estructura" in df.columns:
        colapso = (
            df["ext_colapso_estructura"]
            .astype(str)
            .str.strip()
            .str.lower()
            .isin(["b", "c", "medio", "alto"])
        )
    estructural = sev.isin(["B", "C"]) | colapso
    no_est = comp.isin(["B", "C"])
    out = pd.Series("Sin clasificar", index=df.index, dtype=object)
    out = out.mask(estructural & ~no_est, "Estructural")
    out = out.mask(~estructural & no_est, "No estructural")
    out = out.mask(estructural & no_est, "Estructural y no estructural")
    sin_dano = (~estructural) & (~no_est) & (sev.isin(["A"]) | comp.isin(["A"]))
    out = out.mask(sin_dano, "Sin daño relevante")
    return out


def _fill_geo(s: pd.Series, default: str) -> pd.Series:
    x = s.fillna(default).astype(str).str.strip()
    return x.mask(x.eq("") | x.str.lower().isin(["nan", "none", "(sin estado)"]), default)


def construir_export_pdna_fisico(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Hojas Excel: territorio desagregado, tipología y totales de semáforo (sin USD)."""
    if df is None or df.empty:
        vacio = pd.DataFrame()
        return {
            "Por_territorio": vacio,
            "Por_tipologia": vacio,
            "Totales_semaforo": vacio,
            "Totales_tipo_dano": vacio,
        }

    work = enriquecer_desglose_tipologia(df)
    mask = work["tipologia_pdna"].notna() & work["etiqueta_n"].isin(ETIQUETAS)
    sub = work.loc[mask].copy()
    if sub.empty:
        vacio = pd.DataFrame()
        return {
            "Por_territorio": vacio,
            "Por_tipologia": vacio,
            "Totales_semaforo": vacio,
            "Totales_tipo_dano": vacio,
        }

    sub["Estado"] = _fill_geo(sub.get("estado_n", pd.Series(index=sub.index)), "(Sin estado)")
    sub["Municipio"] = _fill_geo(
        sub.get("municipio_n", pd.Series(index=sub.index)), "(Sin municipio)"
    )
    sub["Parroquia"] = _fill_geo(
        sub.get("parroquia_n", pd.Series(index=sub.index)), "(Sin parroquia)"
    )
    sub["Material"] = sub["material_pdna"].fillna("(Sin material)").astype(str)
    sub["Uso"] = sub["uso_pdna"].fillna("(Sin uso)").astype(str)
    sub["Banda_pisos"] = sub["banda_pisos_pdna"].fillna("(Sin banda)").astype(str)
    sub["Tipo_dano"] = clasificar_tipo_dano(sub)
    sub["Semaforo"] = sub["etiqueta_n"].astype(str)

    dims_terr = ["Estado", "Municipio", "Parroquia", "Material", "Uso", "Banda_pisos", "Tipo_dano"]
    ct_terr = (
        pd.crosstab(
            index=[sub[c] for c in dims_terr],
            columns=sub["Semaforo"],
            rownames=dims_terr,
        )
        .reindex(columns=list(ETIQUETAS), fill_value=0)
        .reset_index()
    )
    for e in ETIQUETAS:
        if e not in ct_terr.columns:
            ct_terr[e] = 0
    ct_terr["Total"] = ct_terr[list(ETIQUETAS)].sum(axis=1).astype(int)
    for e in ETIQUETAS:
        ct_terr[e] = ct_terr[e].astype(int)
    por_territorio = ct_terr.rename(
        columns={
            "VERDE": "Verde",
            "AMARILLO": "Amarillo",
            "ROJO": "Rojo",
            "NEGRO": "Negro_perdida_total",
        }
    ).sort_values(
        ["Estado", "Municipio", "Parroquia", "Material", "Uso", "Banda_pisos", "Tipo_dano"],
        kind="mergesort",
    )
    por_territorio = por_territorio.reset_index(drop=True)
    por_territorio.index.name = None

    dims_tip = ["Material", "Uso", "Banda_pisos", "Tipo_dano"]
    ct_tip = (
        pd.crosstab(
            index=[sub[c] for c in dims_tip],
            columns=sub["Semaforo"],
            rownames=dims_tip,
        )
        .reindex(columns=list(ETIQUETAS), fill_value=0)
        .reset_index()
    )
    for e in ETIQUETAS:
        if e not in ct_tip.columns:
            ct_tip[e] = 0
    ct_tip["Total"] = ct_tip[list(ETIQUETAS)].sum(axis=1).astype(int)
    for e in ETIQUETAS:
        ct_tip[e] = ct_tip[e].astype(int)
    por_tipologia = ct_tip.rename(
        columns={
            "VERDE": "Verde",
            "AMARILLO": "Amarillo",
            "ROJO": "Rojo",
            "NEGRO": "Negro_perdida_total",
        }
    ).sort_values(["Material", "Uso", "Banda_pisos", "Tipo_dano"], kind="mergesort")
    por_tipologia = por_tipologia.reset_index(drop=True)
    por_tipologia.index.name = None

    vc = sub["etiqueta_n"].value_counts()
    totales = pd.DataFrame(
        [
            {
                "Semaforo": etiqueta_display(e),
                "Codigo": e,
                "Unidades": int(vc.get(e, 0)),
            }
            for e in ETIQUETAS
        ]
    )
    totales.loc[len(totales)] = {
        "Semaforo": "TOTAL",
        "Codigo": "",
        "Unidades": int(len(sub)),
    }

    tipo_vc = sub["Tipo_dano"].value_counts()
    por_tipo_dano = (
        pd.DataFrame(
            {"Tipo_dano": tipo_vc.index.astype(str), "Unidades": tipo_vc.values.astype(int)}
        )
        .sort_values("Unidades", ascending=False)
        .reset_index(drop=True)
    )

    return {
        "Por_territorio": por_territorio,
        "Por_tipologia": por_tipologia,
        "Totales_semaforo": totales,
        "Totales_tipo_dano": por_tipo_dano,
    }


def matriz_fisica_desglosada(mat: pd.DataFrame) -> pd.DataFrame:
    """Matriz tipología × semáforo con Material/Uso/Banda en columnas aparte (+ TOTAL)."""
    if mat is None or mat.empty or "tipologia" not in mat.columns:
        return pd.DataFrame(
            columns=[
                "Material",
                "Uso",
                "Banda_pisos",
                "Verde",
                "Amarillo",
                "Rojo",
                "Negro_perdida_total",
                "Total",
            ]
        )
    rows: list[dict[str, Any]] = []
    for _, r in mat.iterrows():
        mat_n, uso_n, banda_n = desglosar_tipologia_pdna(r["tipologia"])
        rows.append(
            {
                "Material": mat_n or "",
                "Uso": uso_n or "",
                "Banda_pisos": banda_n or "",
                "Verde": int(r.get("verde", 0)),
                "Amarillo": int(r.get("amarillo", 0)),
                "Rojo": int(r.get("rojo", 0)),
                "Negro_perdida_total": int(r.get("negro", 0)),
                "Total": int(r.get("total", 0)),
            }
        )
    out = pd.DataFrame(rows)
    pie = {
        "Material": "TOTAL",
        "Uso": "",
        "Banda_pisos": "",
        "Verde": int(out["Verde"].sum()),
        "Amarillo": int(out["Amarillo"].sum()),
        "Rojo": int(out["Rojo"].sum()),
        "Negro_perdida_total": int(out["Negro_perdida_total"].sum()),
        "Total": int(out["Total"].sum()),
    }
    return pd.concat([out, pd.DataFrame([pie])], ignore_index=True)
