"""Ingesta y enriquecimiento del CSV Habitable → mart analítico."""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from clean_catalog import (  # noqa: E402
    aplicar_limpieza_categorica,
    clasificar_uso_ampliado,
    diagnostico_uso,
    normalizar_municipio,
    tipificar_uso_con_pisos,
    _USO_VIVIENDA_PENDIENTE,
)
from stats_asociacion import PISOS_HASTA_INDIVIDUAL, PISOS_MAX_PLAUSIBLE, banda_pisos  # noqa: E402

TZ = ZoneInfo("America/Caracas")
ETIQUETAS = ("VERDE", "AMARILLO", "ROJO", "NEGRO")

# Etiqueta canónica (mart) → etiqueta didáctica en UI
ETIQUETA_DISPLAY: dict[str, str] = {
    "VERDE": "Verde",
    "AMARILLO": "Amarillo",
    "ROJO": "Rojo",
    "NEGRO": "Pérdida total",
    "OTRO": "Otro",
}


def etiqueta_display(val: Any) -> str:
    """Nombre legible del semáforo; NEGRO → «Pérdida total»."""
    x = str(val or "").strip().upper()
    return ETIQUETA_DISPLAY.get(x, str(val or "").strip() or "—")

_CAT_FILL = "Sin Evaluar"
_COLS_CRITICAS = (
    "id",
    "etiqueta",
    "material",
    "anio_construccion",
    "uso",
    "num_pisos",
    "nombre_edificacion",
    "riesgo_externo",
    "riesgo_severo",
    "riesgo_moderado",
    "riesgo_componentes",
    "emergencia_gas",
    "lat",
    "lng",
    "inspector_nombre",
    "estado",
    "municipio",
    "parroquia",
    "sev_columna",
    "sev_muro_mamposteria",
    "mod_muro_mamposteria",
    "comp_losa",
    "comp_paredes",
    "ext_colapso_estructura",
    "num_personas",
    "validated",
    "created_at",
)


def _fold(s: str) -> str:
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return ""
    t = unicodedata.normalize("NFKD", str(s))
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", t).strip().lower()


def normalizar_etiqueta(val: Any) -> str:
    x = str(val or "").strip().upper()
    if x in ETIQUETAS:
        return x
    return "OTRO"


def normalizar_estado(val: Any) -> str:
    n = _fold(val)
    aliases = {
        "distrito capital": "DISTRITO CAPITAL",
        "dc": "DISTRITO CAPITAL",
        "la guaira": "LA GUAIRA",
        "vargas": "LA GUAIRA",
        "miranda": "MIRANDA",
        "carabobo": "CARABOBO",
        "aragua": "ARAGUA",
        "falcon": "FALCON",
        "lara": "LARA",
        "zulia": "ZULIA",
        "yaracuy": "YARACUY",
    }
    if n in aliases:
        return aliases[n]
    raw = str(val or "").strip()
    return raw.upper() if raw else "(sin estado)"


def _material_pdna(material: Any) -> str | None:
    n = _fold(material)
    if not n or n in {"sin evaluar", "desconocido"}:
        return None
    if "informal" in n:
        return "mampostería informal"
    if "formal" in n or n in {"mamposteria", "mampostería"}:
        return "mampostería formal"
    if "acero" in n:
        return "acero"
    if "concreto" in n or "hormigon" in n or "hormigón" in n:
        return "concreto"
    if "mixto" in n:
        return "concreto"
    return None


def _uso_pdna(
    uso: Any,
    num_pisos: Any = None,
    *,
    nombre: Any = None,
    observaciones: Any = None,
    direccion: Any = None,
) -> str | None:
    """Uso PDNA: casa · edificio · turismo · comercio."""
    g = clasificar_uso_ampliado(
        uso, nombre=nombre, observaciones=observaciones, direccion=direccion
    )
    if g == _USO_VIVIENDA_PENDIENTE:
        g = tipificar_uso_con_pisos(g, num_pisos)
    # Compatibilidad marts viejos
    if g in {"Comercio / oficina", "Oficina"}:
        g = "Comercio"
    mapeo = {
        "Casa": "casa",
        "Edificio": "edificio",
        "Establecimientos turísticos": "turismo",
        "Comercio": "comercio",
    }
    return mapeo.get(g)


# Esquemas de tipología PDNA (ejes fijos; bandas / piso a piso configurables).
ESQUEMA_PDNA_EXCEL = "excel_plantilla"
ESQUEMA_PDNA_DETALLADO = "altura_detallada"
ESQUEMA_PDNA_PISO_A_PISO = "piso_a_piso"
ESQUEMA_PDNA_OBSERVADO = "solo_observadas"

ESQUEMAS_PDNA_LABELS: dict[str, str] = {
    ESQUEMA_PDNA_PISO_A_PISO: "Piso a piso (1–20 + 21 o más) · recomendado",
    ESQUEMA_PDNA_DETALLADO: "Ampliado: bandas de pisos",
    ESQUEMA_PDNA_EXCEL: "Plantilla sectorial (12 tipologías)",
    ESQUEMA_PDNA_OBSERVADO: "Dinámico: solo combinaciones del corte",
}

MATERIALES_PDNA: tuple[str, ...] = (
    "concreto",
    "acero",
    "mampostería formal",
    "mampostería informal",
)

USOS_PDNA: tuple[str, ...] = (
    "casa",
    "edificio",
    "turismo",
    "comercio",
)

USO_PDNA_LABEL: dict[str, str] = {
    "casa": "casa",
    "edificio": "edificio",
    "turismo": "turismo",
    "comercio": "comercio",
}


def _banda_pisos_pdna(tipo: str, pisos: float, *, esquema: str) -> str | None:
    """Banda / piso individual según el esquema de tipologías activo."""
    if esquema == ESQUEMA_PDNA_PISO_A_PISO:
        # Misma lógica para todos los usos: 1…20 + cola 21+; >60 → s/d
        return banda_pisos(pisos).replace("Sin dato", "pisos s/d")

    if tipo == "casa":
        if esquema == ESQUEMA_PDNA_EXCEL:
            return "1-2 pisos"
        if pisos != pisos:  # NaN
            return "pisos s/d"
        if pisos <= 1:
            return "1 piso"
        if pisos <= 2:
            return "2 pisos"
        return "3 o más pisos"

    # edificio / no vivienda en esquemas antiguos de bandas
    if esquema == ESQUEMA_PDNA_EXCEL:
        if pisos == pisos and pisos >= 5:
            return ">= 5 pisos"
        return "< 5 pisos"
    if pisos != pisos:
        return "pisos s/d"
    try:
        ni = int(float(pisos))
    except (TypeError, ValueError):
        return "pisos s/d"
    if ni > PISOS_MAX_PLAUSIBLE:
        return "pisos s/d"
    if pisos < 5:
        return "< 5 pisos"
    if pisos <= 8:
        return "5 a 8 pisos"
    if pisos <= 12:
        return "9 a 12 pisos"
    return "13 o más pisos"


def tipologia_pdna(
    uso: Any,
    material: Any,
    num_pisos: Any,
    *,
    esquema: str = ESQUEMA_PDNA_EXCEL,
    nombre: Any = None,
    observaciones: Any = None,
    direccion: Any = None,
) -> str | None:
    """Etiqueta tipológica PDNA: material × uso × pisos (banda o piso a piso)."""
    mat = _material_pdna(material)
    tipo = _uso_pdna(
        uso,
        num_pisos,
        nombre=nombre,
        observaciones=observaciones,
        direccion=direccion,
    )
    if mat is None or tipo is None:
        return None
    try:
        pisos = float(num_pisos)
    except (TypeError, ValueError):
        pisos = np.nan
    banda = _banda_pisos_pdna(tipo, pisos, esquema=esquema)
    if banda is None:
        return None
    return f"{mat} ({tipo}), {banda}"


_TIP_RE = re.compile(
    r"^(?P<material>.+?) \((?P<uso>casa|edificio|turismo|comercio|oficina)\), (?P<banda>.+)$",
    re.IGNORECASE,
)


def desglosar_tipologia_pdna(tipologia: Any) -> tuple[str | None, str | None, str | None]:
    """Separa «material (uso), banda» en tres campos (no concatenados)."""
    m = _TIP_RE.match(str(tipologia or "").strip())
    if not m:
        return None, None, None
    uso = m.group("uso").strip().lower()
    if uso == "oficina":
        uso = "comercio"  # fusión operativa: oficinas → comercio
    return (
        m.group("material").strip(),
        uso,
        m.group("banda").strip(),
    )


def bandas_pisos_catalogo(esquema: str = ESQUEMA_PDNA_EXCEL) -> tuple[str, ...]:
    """Bandas / niveles de pisos posibles según esquema (orden de lectura)."""
    if esquema == ESQUEMA_PDNA_EXCEL:
        return ("1-2 pisos", "< 5 pisos", ">= 5 pisos")
    if esquema == ESQUEMA_PDNA_PISO_A_PISO:
        return tuple(
            ["1 piso", *[f"{i} pisos" for i in range(2, PISOS_HASTA_INDIVIDUAL + 1)],
             f"{PISOS_HASTA_INDIVIDUAL + 1} o más", "pisos s/d"]
        )
    return (
        "1 piso",
        "2 pisos",
        "3 o más pisos",
        "< 5 pisos",
        "5 a 8 pisos",
        "9 a 12 pisos",
        "13 o más pisos",
        "pisos s/d",
    )


def enriquecer_desglose_tipologia(df: pd.DataFrame) -> pd.DataFrame:
    """Añade material_pdna / uso_pdna / banda_pisos_pdna / tip_corta a partir de tipologia_pdna."""
    out = df
    if "tipologia_pdna" not in out.columns:
        out = out.copy()
        out["material_pdna"] = None
        out["uso_pdna"] = None
        out["banda_pisos_pdna"] = None
        out["tipologia_corta"] = None
        return out
    parts = out["tipologia_pdna"].map(desglosar_tipologia_pdna)
    out = out.copy()
    out["material_pdna"] = [p[0] for p in parts]
    out["uso_pdna"] = [p[1] for p in parts]
    out["banda_pisos_pdna"] = [p[2] for p in parts]
    out["tipologia_corta"] = [
        f"{m} ({u})" if m and u else None
        for m, u, _ in parts
    ]
    return out


def tipos_pdna_orden(esquema: str = ESQUEMA_PDNA_EXCEL) -> tuple[str, ...]:
    """Filas canónicas esperadas para un esquema (antes de filtrar por presencia)."""
    if esquema == ESQUEMA_PDNA_EXCEL:
        return TIPOS_PDNA_ORDEN
    if esquema == ESQUEMA_PDNA_PISO_A_PISO:
        bandas = bandas_pisos_catalogo(ESQUEMA_PDNA_PISO_A_PISO)
        filas: list[str] = []
        for mat in MATERIALES_PDNA:
            for uso in USOS_PDNA:
                for b in bandas:
                    filas.append(f"{mat} ({uso}), {b}")
        return tuple(filas)
    # Ampliado / dinámico: catálogo completo posible; el dinámico luego se recorta a observadas.
    bandas_casa = ("1 piso", "2 pisos", "3 o más pisos", "pisos s/d")
    bandas_edificio = (
        "< 5 pisos",
        "5 a 8 pisos",
        "9 a 12 pisos",
        "13 o más pisos",
        "pisos s/d",
    )
    filas = []
    for mat in MATERIALES_PDNA:
        for b in bandas_casa:
            filas.append(f"{mat} (casa), {b}")
        for b in bandas_edificio:
            filas.append(f"{mat} (edificio), {b}")
    return tuple(filas)


def aplicar_tipologia_pdna(
    df: pd.DataFrame,
    *,
    esquema: str = ESQUEMA_PDNA_EXCEL,
    copy: bool = True,
) -> pd.DataFrame:
    """Recalcula ``tipologia_pdna`` según esquema (sin rehacer el mart).

    Si ``copy=False``, muta el DataFrame recibido (usar solo sobre marcos ya ligeros).
    """
    out = df.copy() if copy else df
    uso_src = out["uso_raw_n"] if "uso_raw_n" in out.columns else out.get("uso_n", out.get("uso"))
    mat_src = out["material_n"] if "material_n" in out.columns else out.get("material")
    pisos_src = out.get("num_pisos")
    nom_src = out["nombre_edificacion"] if "nombre_edificacion" in out.columns else None
    obs_src = out["observaciones"] if "observaciones" in out.columns else None
    dir_src = out["direccion"] if "direccion" in out.columns else None
    if uso_src is None or mat_src is None:
        out["tipologia_pdna"] = None
        return out
    if pisos_src is None:
        pisos_src = pd.Series(np.nan, index=out.index)
    tips = []
    for idx in out.index:
        tips.append(
            tipologia_pdna(
                uso_src.loc[idx],
                mat_src.loc[idx],
                pisos_src.loc[idx],
                esquema=esquema,
                nombre=nom_src.loc[idx] if nom_src is not None else None,
                observaciones=obs_src.loc[idx] if obs_src is not None else None,
                direccion=dir_src.loc[idx] if dir_src is not None else None,
            )
        )
    out["tipologia_pdna"] = tips
    return out


TIPOS_PDNA_ORDEN: tuple[str, ...] = (
    "concreto (casa), 1-2 pisos",
    "acero (casa), 1-2 pisos",
    "mampostería formal (casa), 1-2 pisos",
    "mampostería informal (casa), 1-2 pisos",
    "concreto (edificio), < 5 pisos",
    "acero (edificio), < 5 pisos",
    "mampostería formal (edificio), < 5 pisos",
    "mampostería informal (edificio), < 5 pisos",
    "concreto (edificio), >= 5 pisos",
    "acero (edificio), >= 5 pisos",
    "mampostería formal (edificio), >= 5 pisos",
    "mampostería informal (edificio), >= 5 pisos",
)


def _fillna_estrategia(work: pd.DataFrame) -> pd.DataFrame:
    """Nulos: categóricos → Sin Evaluar; numéricos de daño/conteo → 0; año → NaN (banda aparte)."""
    cat_cols = [
        "nombre_edificacion",
        "inspector_nombre",
        "uso",
        "material",
        "municipio",
        "parroquia",
        "sev_columna",
        "sev_muro_mamposteria",
        "mod_muro_mamposteria",
        "comp_losa",
        "comp_paredes",
        "ext_colapso_estructura",
    ]
    for c in cat_cols:
        if c in work.columns:
            work[c] = work[c].fillna(_CAT_FILL).astype(str).replace({"": _CAT_FILL, "nan": _CAT_FILL})

    for c in ("num_pisos", "num_personas"):
        if c in work.columns:
            work[c] = pd.to_numeric(work[c], errors="coerce")
            # ausencia de piso/personas: mediana del corte (no cero, para no sesgar PDNA)
            med = work[c].median(skipna=True)
            if med == med:
                work[c] = work[c].fillna(float(med))
            else:
                work[c] = work[c].fillna(0.0)

    if "anio_construccion" in work.columns:
        work["anio_construccion"] = pd.to_numeric(work["anio_construccion"], errors="coerce")
        work["anio_construccion_n"] = work["anio_construccion"]
    else:
        work["anio_construccion_n"] = np.nan

    return work


def procesar_dataframe(df: pd.DataFrame, *, fuente: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Normaliza semáforo, territorio, tipología PDNA y rellena nulos de forma tipada."""
    work = df.copy()
    work.columns = [str(c).strip() for c in work.columns]
    # Coercer pisos antes de tipificar uso (Casa/Edificio); el fill de mediana va después
    if "num_pisos" in work.columns:
        work["num_pisos"] = pd.to_numeric(work["num_pisos"], errors="coerce")
    if "num_personas" in work.columns:
        work["num_personas"] = pd.to_numeric(work["num_personas"], errors="coerce")
    uso_antes = work["uso"].copy() if "uso" in work.columns else pd.Series(dtype=object)

    work = aplicar_limpieza_categorica(work)
    work = _fillna_estrategia(work)
    work["etiqueta_n"] = work.get("etiqueta", pd.Series(dtype=object)).map(normalizar_etiqueta)
    # Alias de estado (fold) encima del lex_upper
    work["estado_n"] = work.get("estado", work["estado_n"]).map(normalizar_estado)
    work["municipio_n"] = [
        normalizar_municipio(m, e)
        for m, e in zip(
            work["municipio"] if "municipio" in work.columns else work["municipio_n"],
            work["estado_n"],
            strict=False,
        )
    ]

    for flag in (
        "riesgo_externo",
        "riesgo_severo",
        "riesgo_moderado",
        "riesgo_componentes",
        "emergencia_gas",
        "validated",
    ):
        if flag in work.columns:
            work[flag] = work[flag].fillna(False).astype(bool)
        else:
            work[flag] = False

    # Tipología PDNA (uso + nombre + observaciones + dirección para turismo)
    work = aplicar_tipologia_pdna(work, esquema=ESQUEMA_PDNA_PISO_A_PISO, copy=False)
    work["created_at"] = pd.to_datetime(work.get("created_at"), errors="coerce", format="mixed")

    counts = work["etiqueta_n"].value_counts()
    uso_diag = diagnostico_uso(uso_antes, work["uso_grupo"]) if len(uso_antes) else pd.DataFrame()
    summary: dict[str, Any] = {
        "fuente": fuente,
        "corte_generado_en": datetime.now(TZ).isoformat(timespec="seconds"),
        "n_inspecciones": int(len(work)),
        "n_con_gps": int(work["con_gps"].sum()),
        "n_geo_valida": int(work["geo_valida"].sum()),
        "n_sin_gps_o_fuera_ve": int((~work["geo_valida"]).sum()),
        "n_validadas": int(work["validated"].sum()) if "validated" in work.columns else 0,
        "semaforo": {e: int(counts.get(e, 0)) for e in ETIQUETAS},
        "n_tipologia_pdna": int(work["tipologia_pdna"].notna().sum()),
        "estados_top": work["estado_n"].value_counts().head(12).to_dict(),
        "uso_grupos": work["uso_grupo"].value_counts().to_dict(),
        "uso_cardinalidad_antes": int(uso_antes.nunique(dropna=True)) if len(uso_antes) else 0,
        "uso_cardinalidad_despues": int(work["uso_grupo"].nunique()),
        "uso_pareto": uso_diag.to_dict(orient="records"),
        "fase": "v2-catalogo-ux",
    }
    return work, summary


def resumen_danos_pdna(df: pd.DataFrame) -> pd.DataFrame:
    """Tabla estilo «Resumen daños»: tipología × conteos de semáforo."""
    sub = df.loc[df["tipologia_pdna"].notna() & df["etiqueta_n"].isin(ETIQUETAS)].copy()
    if sub.empty:
        return pd.DataFrame(columns=["tipologia", *ETIQUETAS, "total"])

    ct = pd.crosstab(sub["tipologia_pdna"], sub["etiqueta_n"])
    for e in ETIQUETAS:
        if e not in ct.columns:
            ct[e] = 0
    ct = ct.reindex(columns=list(ETIQUETAS), fill_value=0)
    ct["total"] = ct.sum(axis=1)
    orden = [t for t in TIPOS_PDNA_ORDEN if t in ct.index] + sorted(set(ct.index) - set(TIPOS_PDNA_ORDEN))
    ct = ct.reindex(orden).fillna(0).astype(int)
    return ct.reset_index().rename(columns={"tipologia_pdna": "tipologia"})


def guardar_mart(df: pd.DataFrame, summary: dict[str, Any], *, root: Path) -> Path:
    out_dir = root / "data" / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    pq = out_dir / "inspecciones_habitable.parquet"
    meta = out_dir / "summary.json"
    df.to_parquet(pq, index=False)
    meta.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return pq


def cargar_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8", low_memory=False)


def mart_paths(root: Path) -> tuple[Path, Path]:
    base = root / "data" / "processed"
    return base / "inspecciones_habitable.parquet", base / "summary.json"
