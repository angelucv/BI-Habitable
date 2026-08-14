"""Detección de multiplicidad / conflictos para depuración del mart Habitable."""

from __future__ import annotations

from typing import Any, Literal

import numpy as np
import pandas as pd

CriterioDup = Literal["gps", "nombre_mun", "direccion_mun"]

_NOMBRE_GENERICO = {
    "",
    "S/N",
    "SN",
    "SIN NOMBRE",
    "SIN NOMBRE.",
    "CASA",
    "CASA S/N",
    "CASA SN",
    "CASA SIN NUMERO",
    "CASA SIN NÚMERO",
    "SIN NUMERO",
    "SIN NÚMERO",
    "VIVIENDA",
    "VIVIENDA UNIFAMILIAR",
    "VIVIENDA MULTIFAMILIAR",
    "EDIFICIO",
    "N/A",
    "NA",
    "-",
    ".",
    "0",
    "NULL",
    "NONE",
    "NAN",
}

_DIR_GENERICA = {
    "",
    "S/N",
    "SN",
    "SIN DIRECCION",
    "SIN DIRECCIÓN",
    "N/A",
    "NA",
    "-",
    ".",
    "0",
    "NULL",
    "NONE",
    "NAN",
}


def _norm_txt(s: pd.Series) -> pd.Series:
    return (
        s.fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
        .str.replace(r"\s+", " ", regex=True)
    )


def enriquecer_claves_lugar(df: pd.DataFrame, *, gps_decimals: int = 5) -> pd.DataFrame:
    """Añade claves de lugar para auditoría (no muta el mart en disco)."""
    out = df.copy()
    lat = pd.to_numeric(out.get("lat"), errors="coerce")
    lng = pd.to_numeric(out.get("lng"), errors="coerce")
    nd = int(np.clip(gps_decimals, 3, 5))
    out["_lat_r"] = lat.round(nd)
    out["_lng_r"] = lng.round(nd)
    out["_gps_ok"] = lat.notna() & lng.notna()
    if "geo_valida" in out.columns:
        out["_gps_ok"] = out["_gps_ok"] & out["geo_valida"].fillna(False).astype(bool)

    out["_nombre_n"] = _norm_txt(out["nombre_edificacion"]) if "nombre_edificacion" in out.columns else ""
    out["_dir_n"] = _norm_txt(out["direccion"]) if "direccion" in out.columns else ""
    out["_mun_n"] = _norm_txt(out["municipio_n"]) if "municipio_n" in out.columns else ""
    out["_est_n"] = _norm_txt(out["estado_n"]) if "estado_n" in out.columns else ""

    out["_nombre_util"] = ~out["_nombre_n"].isin(_NOMBRE_GENERICO)
    out["_dir_util"] = ~out["_dir_n"].isin(_DIR_GENERICA) & (out["_dir_n"].str.len() >= 8)

    out["_key_gps"] = np.where(
        out["_gps_ok"],
        out["_lat_r"].astype(str) + "|" + out["_lng_r"].astype(str),
        "",
    )
    # Nombre / dirección solo alertan si además caen en la misma celda GPS
    # (precisión elegida). Sin GPS válido no forman grupo.
    out["_key_nombre"] = np.where(
        out["_nombre_util"] & out["_mun_n"].ne("") & out["_gps_ok"],
        out["_nombre_n"] + "||" + out["_mun_n"] + "||" + out["_key_gps"],
        "",
    )
    out["_key_dir"] = np.where(
        out["_dir_util"] & out["_mun_n"].ne("") & out["_gps_ok"],
        out["_dir_n"] + "||" + out["_mun_n"] + "||" + out["_key_gps"],
        "",
    )
    return out


def _grupos_dup(df: pd.DataFrame, key_col: str) -> pd.DataFrame:
    """Resumen por clave: tamaño, semáforos distintos, muestra de ids."""
    sub = df.loc[df[key_col].astype(str).str.len() > 0].copy()
    if sub.empty:
        return pd.DataFrame()
    g = (
        sub.groupby(key_col, dropna=False)
        .agg(
            n_insp=("id", "size") if "id" in sub.columns else (key_col, "size"),
            n_etiquetas=("etiqueta_n", "nunique"),
            etiquetas=("etiqueta_n", lambda s: " · ".join(sorted({str(x) for x in s.dropna()}))),
            estados=("_est_n", lambda s: " · ".join(sorted({str(x) for x in s.dropna() if x}))[:80]),
            municipios=("_mun_n", lambda s: " · ".join(sorted({str(x) for x in s.dropna() if x}))[:80]),
            nombre_ej=("_nombre_n", "first"),
            dir_ej=("_dir_n", "first"),
            lat_ej=("_lat_r", "first"),
            lng_ej=("_lng_r", "first"),
        )
        .reset_index()
        .rename(columns={key_col: "clave"})
    )
    if "id" not in sub.columns:
        g = g.rename(columns={key_col: "n_insp"}) if "n_insp" not in g.columns else g
    g = g.loc[g["n_insp"] > 1].sort_values(["n_insp", "n_etiquetas"], ascending=False)
    g["conflicto_semaforo"] = g["n_etiquetas"] > 1
    return g


def resumen_depuracion(df: pd.DataFrame, *, gps_decimals: int = 5) -> dict[str, Any]:
    work = enriquecer_claves_lugar(df, gps_decimals=gps_decimals)
    gps = _grupos_dup(work, "_key_gps")
    nom = _grupos_dup(work, "_key_nombre")
    dire = _grupos_dup(work, "_key_dir")

    def _peso(g: pd.DataFrame) -> tuple[int, int, int]:
        if g.empty:
            return 0, 0, 0
        return int(len(g)), int(g["n_insp"].sum()), int(g["conflicto_semaforo"].sum())

    ng, rg, cg = _peso(gps)
    nn, rn, cn = _peso(nom)
    nd, rd, cd = _peso(dire)
    return {
        "n_total": len(work),
        "gps_decimals": gps_decimals,
        "gps_grupos": ng,
        "gps_filas": rg,
        "gps_conflictos": cg,
        "nombre_grupos": nn,
        "nombre_filas": rn,
        "nombre_conflictos": cn,
        "dir_grupos": nd,
        "dir_filas": rd,
        "dir_conflictos": cd,
        "gps_ok": int(work["_gps_ok"].sum()),
        "nombre_util": int(work["_nombre_util"].sum()),
        "dir_util": int(work["_dir_util"].sum()),
    }


def tabla_grupos(
    df: pd.DataFrame,
    *,
    criterio: CriterioDup,
    gps_decimals: int = 5,
    solo_conflicto: bool = False,
    min_n: int = 2,
) -> pd.DataFrame:
    work = enriquecer_claves_lugar(df, gps_decimals=gps_decimals)
    key = {"gps": "_key_gps", "nombre_mun": "_key_nombre", "direccion_mun": "_key_dir"}[criterio]
    g = _grupos_dup(work, key)
    if g.empty:
        return g
    g = g.loc[g["n_insp"] >= min_n]
    if solo_conflicto:
        g = g.loc[g["conflicto_semaforo"]]
    return g.reset_index(drop=True)


def filas_de_grupo(
    df: pd.DataFrame,
    *,
    criterio: CriterioDup,
    clave: str,
    gps_decimals: int = 5,
) -> pd.DataFrame:
    work = enriquecer_claves_lugar(df, gps_decimals=gps_decimals)
    key = {"gps": "_key_gps", "nombre_mun": "_key_nombre", "direccion_mun": "_key_dir"}[criterio]
    sub = work.loc[work[key] == clave].copy()
    cols = [
        c
        for c in (
            "id",
            "etiqueta_n",
            "estado_n",
            "municipio_n",
            "nombre_edificacion",
            "direccion",
            "lat",
            "lng",
            "anio_construccion_n",
            "num_pisos",
            "uso_n",
            "material_n",
            "fecha_evento",
            "inspector_nombre",
        )
        if c in sub.columns
    ]
    return sub[cols].sort_values([c for c in ("etiqueta_n", "id") if c in cols])
