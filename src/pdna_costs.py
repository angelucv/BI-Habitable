"""Estimación PDNA — efectos en activos físicos (vivienda + contenidos).

Alineado a PDNA Volume A (efectos en infraestructura/activos → valoración
a costo de reposición) y a la matriz tipología × semáforo del formato sector vivienda.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from process_habitable import ETIQUETAS, TIPOS_PDNA_ORDEN

# Fracción del valor de reposición de la vivienda atribuible a daño
# (estructural + no estructural) por semáforo. NEGRO > 1 = Build Back Better.
FACTORES_VIVIENDA_DEFAULT: dict[str, float] = {
    "VERDE": 0.02,
    "AMARILLO": 0.25,
    "ROJO": 0.65,
    "NEGRO": 1.15,
}

# Inventario de contenidos como % del valor de reposición de la vivienda.
RATIO_CONTENIDOS_DEFAULT = 0.20

# Fracción del inventario de contenidos dañado/perdido por semáforo.
FACTORES_CONTENIDOS_DEFAULT: dict[str, float] = {
    "VERDE": 0.05,
    "AMARILLO": 0.35,
    "ROJO": 0.80,
    "NEGRO": 1.00,
}

# USD/m² por familia material (supuesto analítico editable).
COSTO_M2_DEFAULT: dict[str, float] = {
    "concreto": 450.0,
    "acero": 520.0,
    "mampostería formal": 320.0,
    "mampostería informal": 220.0,
    "otro": 300.0,
}

M2_POR_PISO_DEFAULT = 80.0
AREA_MINIMA_DEFAULT = 40.0

# Alias históricos (páginas previas)
FACTORES_DEFAULT = FACTORES_VIVIENDA_DEFAULT


def _familia_material(material: Any) -> str:
    n = str(material or "").strip().lower()
    if "informal" in n:
        return "mampostería informal"
    if "formal" in n or "mamposter" in n:
        return "mampostería formal"
    if "acero" in n:
        return "acero"
    if "concreto" in n or "hormigon" in n or "hormigón" in n or "mixto" in n:
        return "concreto"
    return "otro"


def _familia_desde_tipologia(tipologia: Any) -> str:
    n = str(tipologia or "").strip().lower()
    if n.startswith("mampostería informal") or n.startswith("mamposteria informal"):
        return "mampostería informal"
    if n.startswith("mampostería formal") or n.startswith("mamposteria formal"):
        return "mampostería formal"
    if n.startswith("acero"):
        return "acero"
    if n.startswith("concreto"):
        return "concreto"
    return "otro"


COLS_PDNA_BASE: tuple[str, ...] = (
    "id",
    "etiqueta_n",
    "estado_n",
    "municipio_n",
    "parroquia_n",
    "tipologia_pdna",
    "material_n",
    "num_pisos",
    "uso_n",
    "uso_raw_n",
    "uso_grupo",
    "nombre_edificacion",
    "observaciones",
    "direccion",
)


def marco_pdna_ligero(df: pd.DataFrame) -> pd.DataFrame:
    """Copia solo columnas necesarias para PDNA (evita duplicar el mart completo)."""
    cols = [c for c in COLS_PDNA_BASE if c in df.columns]
    if not cols:
        return pd.DataFrame(index=df.index)
    return df.loc[:, cols].copy()


def proyectar_pdna(
    df: pd.DataFrame,
    *,
    costo_m2: dict[str, float] | None = None,
    factores: dict[str, float] | None = None,
    factores_vivienda: dict[str, float] | None = None,
    factores_contenidos: dict[str, float] | None = None,
    ratio_contenidos: float = RATIO_CONTENIDOS_DEFAULT,
    m2_por_piso: float = M2_POR_PISO_DEFAULT,
    area_minima: float = AREA_MINIMA_DEFAULT,
    slim: bool = True,
) -> pd.DataFrame:
    """Añade valoración de reposición y daños PDNA por inspección.

    Columnas clave:
    - valor_reposicion_usd: costo de reposición de la vivienda (baseline)
    - dano_vivienda_usd: daño estructural + no estructural
    - dano_contenidos_usd: daño en contenidos
    - costo_pdna_usd: suma de ambos (efecto monetario total estimado)

    Con ``slim=True`` (default) no duplica las ~80 columnas del mart: trabaja sobre
    un marco reducido. Use ``slim=False`` solo si necesita conservar todo el ancho.
    """
    costos = {**COSTO_M2_DEFAULT, **(costo_m2 or {})}
    fac_viv = {
        **FACTORES_VIVIENDA_DEFAULT,
        **(factores or {}),
        **(factores_vivienda or {}),
    }
    fac_cont = {**FACTORES_CONTENIDOS_DEFAULT, **(factores_contenidos or {})}
    ratio = max(float(ratio_contenidos), 0.0)

    out = marco_pdna_ligero(df) if slim else df.copy()
    if out.empty and len(df) > 0:
        out = df.iloc[:, :0].copy()
        out["etiqueta_n"] = df["etiqueta_n"] if "etiqueta_n" in df.columns else "OTRO"

    if "tipologia_pdna" in out.columns:
        tip = out["tipologia_pdna"]
        fam_tip = tip.map(_familia_desde_tipologia)
    else:
        tip = None
        fam_tip = None

    if "material_n" in out.columns:
        fam_mat = out["material_n"].map(_familia_material)
    else:
        fam_mat = pd.Series(["otro"] * len(out), index=out.index)

    if fam_tip is not None and tip is not None:
        tip_ok = tip.notna() & tip.astype(str).str.strip().ne("") & tip.astype(str).ne("None")
        out["familia_material"] = fam_mat.where(~tip_ok, fam_tip)
    else:
        out["familia_material"] = fam_mat

    out["usd_m2"] = out["familia_material"].map(lambda x: float(costos.get(x, costos["otro"]))).astype("float64")
    if "num_pisos" in out.columns:
        pisos = pd.to_numeric(out["num_pisos"], errors="coerce")
    else:
        pisos = pd.Series(np.nan, index=out.index)
    pisos = pisos.fillna(1.0).clip(lower=1.0)
    out["area_m2_est"] = (pisos * float(m2_por_piso)).clip(lower=float(area_minima)).astype("float64")
    out["valor_reposicion_usd"] = (out["usd_m2"] * out["area_m2_est"]).astype("float64")
    out["valor_contenidos_usd"] = (out["valor_reposicion_usd"] * ratio).astype("float64")

    if "etiqueta_n" in out.columns:
        et = out["etiqueta_n"].astype(str).str.upper()
    else:
        et = pd.Series(["OTRO"] * len(out), index=out.index)
    out["factor_vivienda"] = et.map(lambda e: float(fac_viv.get(e, 0.0))).astype("float64")
    out["factor_contenidos"] = et.map(lambda e: float(fac_cont.get(e, 0.0))).astype("float64")
    out["factor_pdna"] = out["factor_vivienda"]

    fac_dir = out["factor_vivienda"].clip(upper=1.0)
    out["dano_vivienda_directo_usd"] = (out["valor_reposicion_usd"] * fac_dir).astype("float64")
    out["premium_bbb_usd"] = (
        out["valor_reposicion_usd"] * (out["factor_vivienda"] - fac_dir).clip(lower=0.0)
    ).astype("float64")
    out["dano_vivienda_usd"] = (out["valor_reposicion_usd"] * out["factor_vivienda"]).astype("float64")
    out["dano_contenidos_usd"] = (out["valor_contenidos_usd"] * out["factor_contenidos"]).astype("float64")
    out["costo_pdna_usd"] = (out["dano_vivienda_usd"] + out["dano_contenidos_usd"]).astype("float64")
    out["dano_fisico_directo_usd"] = (
        out["dano_vivienda_directo_usd"] + out["dano_contenidos_usd"]
    ).astype("float64")
    return out


def matriz_pdna_completa(
    df_pdna: pd.DataFrame,
    *,
    incluir_sin_tipologia: bool = False,
    orden_tipologias: tuple[str, ...] | None = None,
    solo_observadas: bool = False,
    incluir_filas_vacias: bool = False,
) -> pd.DataFrame:
    """Matriz tipología × semáforo + costos (estilo hoja «Por estado» / Resumen daños)."""
    if df_pdna is None or df_pdna.empty:
        cols = [
            "tipologia",
            *[e.lower() for e in ETIQUETAS],
            "total",
            "dano_vivienda_usd",
            "dano_contenidos_usd",
            "costo_total_usd",
        ]
        return pd.DataFrame(columns=cols)

    if "tipologia_pdna" not in df_pdna.columns or "etiqueta_n" not in df_pdna.columns:
        return pd.DataFrame()

    mask = df_pdna["etiqueta_n"].isin(ETIQUETAS)
    if not incluir_sin_tipologia:
        mask = mask & df_pdna["tipologia_pdna"].notna()

    need = [
        c
        for c in (
            "tipologia_pdna",
            "etiqueta_n",
            "dano_vivienda_usd",
            "dano_contenidos_usd",
            "costo_pdna_usd",
            "dano_vivienda_directo_usd",
        )
        if c in df_pdna.columns
    ]
    # Una sola selección estrecha (sin .copy() del mart completo)
    sub = df_pdna.loc[mask, need]
    if sub.empty:
        return pd.DataFrame()

    tip = sub["tipologia_pdna"].fillna("Sin tipología").astype(str)
    etiq = sub["etiqueta_n"]

    ct = pd.crosstab(tip, etiq)
    for e in ETIQUETAS:
        if e not in ct.columns:
            ct[e] = 0
    ct = ct.reindex(columns=list(ETIQUETAS), fill_value=0)

    cost_src = {
        "dano_vivienda_usd": "dano_vivienda_usd",
        "dano_contenidos_usd": "dano_contenidos_usd",
        "costo_total_usd": "costo_pdna_usd",
    }
    if "dano_vivienda_directo_usd" in sub.columns:
        cost_src["dano_vivienda_directo_usd"] = "dano_vivienda_directo_usd"

    tmp = sub.assign(tipologia_pdna=tip)
    costs = (
        tmp.groupby("tipologia_pdna", dropna=False)
        .agg(**{alias: (src, "sum") for alias, src in cost_src.items()})
        .reindex(ct.index)
        .fillna(0.0)
    )

    out = ct.join(costs)
    out["total"] = out[list(ETIQUETAS)].sum(axis=1)
    if "dano_vivienda_directo_usd" in out.columns:
        out["dano_vivienda_usd"] = out["dano_vivienda_directo_usd"]
        out = out.drop(columns=["dano_vivienda_directo_usd"])

    presentes = set(out.index.astype(str))
    canon = tuple(orden_tipologias) if orden_tipologias is not None else TIPOS_PDNA_ORDEN

    if solo_observadas:
        orden = [t for t in canon if t in presentes] + sorted(presentes - set(canon))
        orden = [t for t in orden if int(out.loc[t, "total"]) > 0]
        out = out.reindex(orden).fillna(0)
    elif incluir_filas_vacias:
        missing = [t for t in canon if t not in out.index]
        if missing:
            empty = pd.DataFrame(0, index=missing, columns=out.columns)
            out = pd.concat([out, empty])
        extras = sorted(presentes - set(canon))
        orden = list(canon) + extras
        out = out.reindex(orden).fillna(0)
    else:
        orden = [t for t in canon if t in presentes] + sorted(presentes - set(canon))
        out = out.reindex(orden).fillna(0)

    for e in ETIQUETAS:
        out[e] = out[e].astype(int)
    out["total"] = out["total"].astype(int)

    out = out.reset_index()
    if out.columns[0] != "tipologia":
        out = out.rename(columns={out.columns[0]: "tipologia"})
    rename_sem = {e: e.lower() for e in ETIQUETAS}
    out = out.rename(columns=rename_sem)
    return out[
        [
            "tipologia",
            "verde",
            "amarillo",
            "rojo",
            "negro",
            "total",
            "dano_vivienda_usd",
            "dano_contenidos_usd",
            "costo_total_usd",
        ]
    ]


def resumen_pdna_territorio(df_pdna: pd.DataFrame, *, nivel: str = "municipio_n") -> pd.DataFrame:
    if nivel not in df_pdna.columns:
        return pd.DataFrame()
    g = (
        df_pdna.groupby(nivel, dropna=False)
        .agg(
            inspecciones=("costo_pdna_usd", "size"),
            dano_vivienda_usd=("dano_vivienda_usd", "sum"),
            dano_contenidos_usd=("dano_contenidos_usd", "sum"),
            costo_pdna_usd=("costo_pdna_usd", "sum"),
            valor_reposicion_usd=("valor_reposicion_usd", "sum"),
        )
        .reset_index()
        .sort_values("costo_pdna_usd", ascending=False)
    )
    return g


def kpis_pdna(df_pdna: pd.DataFrame) -> dict[str, float | int]:
    if df_pdna is None or df_pdna.empty:
        return {
            "n": 0,
            "n_con_tipologia": 0,
            "dano_vivienda": 0.0,
            "dano_vivienda_directo": 0.0,
            "dano_contenidos": 0.0,
            "dano_fisico_directo": 0.0,
            "necesidades_recuperacion": 0.0,
            "costo_total": 0.0,
            "valor_reposicion": 0.0,
            "premium_bbb": 0.0,
        }
    tip = (
        df_pdna["tipologia_pdna"].notna()
        if "tipologia_pdna" in df_pdna.columns
        else pd.Series(False, index=df_pdna.index)
    )
    viv = float(df_pdna["dano_vivienda_usd"].sum())
    cont = float(df_pdna["dano_contenidos_usd"].sum())
    viv_dir = float(
        df_pdna["dano_vivienda_directo_usd"].sum()
        if "dano_vivienda_directo_usd" in df_pdna.columns
        else viv
    )
    bbb = float(df_pdna["premium_bbb_usd"].sum()) if "premium_bbb_usd" in df_pdna.columns else 0.0
    total = float(df_pdna["costo_pdna_usd"].sum())
    return {
        "n": int(len(df_pdna)),
        "n_con_tipologia": int(tip.sum()),
        "dano_vivienda": viv,
        "dano_vivienda_directo": viv_dir,
        "dano_contenidos": cont,
        "dano_fisico_directo": viv_dir + cont,
        "necesidades_recuperacion": total,
        "costo_total": total,
        "valor_reposicion": float(df_pdna["valor_reposicion_usd"].sum()),
        "premium_bbb": bbb,
    }
