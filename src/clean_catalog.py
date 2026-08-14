"""Depuración léxica y reducción de cardinalidad (uso / territorio / GPS)."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

import numpy as np
import pandas as pd

# BBox operativo República Bolivariana de Venezuela (margenido)
VE_LAT_MIN, VE_LAT_MAX = 0.55, 12.85
VE_LNG_MIN, VE_LNG_MAX = -73.65, -59.45

# Supercategorías de uso (catálogo de decisión; no el texto libre de campo)
USO_GRUPOS: tuple[str, ...] = (
    "Casa",
    "Edificio",
    "Vivienda sin dato de pisos",
    "Mixto",
    "Comercio / oficina",
    "Salud",
    "Educativo",
    "Institucional",
    "Industrial",
    "Otros",
)

# Etiqueta léxica intermedia: se resuelve con num_pisos → Casa / Edificio
_USO_VIVIENDA_PENDIENTE = "Vivienda (revisar pisos)"

# Caracas es ciudad / área metropolitana, no municipio censal
_NO_MUNICIPIO = frozenset(
    {
        "CARACAS",
        "GRAN CARACAS",
        "AREA METROPOLITANA",
        "ÁREA METROPOLITANA",
        "AREA METROPOLITANA DE CARACAS",
    }
)


def fold_ascii(val: Any) -> str:
    """Minúsculas sin acentos, espacios colapsados (matching)."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return ""
    t = unicodedata.normalize("NFKD", str(val))
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    t = t.lower()
    t = re.sub(r"[|;,/]+", " ", t)
    t = re.sub(r"[^a-z0-9\s\-]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def lex_upper(val: Any, *, fill: str = "SIN EVALUAR") -> str:
    """Mayúsculas, trim, sin basura tipográfica; vacío → fill."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return fill
    t = unicodedata.normalize("NFKC", str(val)).strip()
    t = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", t)
    t = re.sub(r"\s+", " ", t)
    if not t or t.lower() in {"nan", "none", "null", "-", "n/a", "na"}:
        return fill
    return t.upper()


def clasificar_uso(val: Any) -> str:
    """Reduce entropía de uso libre → supercategoría léxica (vivienda genérica queda pendiente de pisos)."""
    n = fold_ascii(val)
    if not n or n in {"sin evaluar", "desconocido", "otro", "otros", "n a"}:
        return "Otros"

    if any(
        k in n
        for k in (
            "hosp",
            "clin",
            "medic",
            "asistencial",
            "ambulator",
            "dispens",
            "centro de salud",
        )
    ):
        return "Salud"

    if any(k in n for k in ("educ", "escuel", "coleg", "univers", "liceo", "preescolar", "bibliotec")):
        return "Educativo"

    if any(k in n for k in ("industr", "taller", "fabrica", "galpon", "deposito", "almacen")):
        return "Industrial"

    tiene_viv = any(k in n for k in ("vivienda", "resid", "apto", "apart", "casa"))
    tiene_com = any(k in n for k in ("comerc", "oficina", "local", "negocio", "peluquer", "tintorer", "gimnasi"))
    if tiene_viv and tiene_com:
        return "Mixto"
    if "mixto" in n:
        return "Mixto"

    if any(
        k in n
        for k in (
            "gubern",
            "militar",
            "seguridad",
            "religios",
            "iglesia",
            "templo",
            "cultural",
            "recreat",
            "policia",
            "bombero",
            "cuartel",
            "comando",
        )
    ):
        return "Institucional"

    if any(k in n for k in ("comerc", "oficina", "hotel", "estacionamiento", "posada", "hostal")):
        return "Comercio / oficina"

    # Edificio / multifamiliar (incluye typos frecuentes de campo)
    if any(
        k in n
        for k in (
            "apart",
            "apto",
            "edif",
            "multifam",
            "mulfifam",
            "mulifam",
            "residencia",
            "condomin",
            "torre",
            "vivienda edificio",
        )
    ):
        return "Edificio"
    if n in {"edificio", "residencial"} or n.startswith("edificio "):
        return "Edificio"

    # Casa / unifamiliar
    if any(k in n for k in ("casa", "quinta", "qta", "unif", "vivienda casa", "rancho", "bifam")):
        return "Casa"

    if n == "vivienda" or n.startswith("vivienda "):
        if "edificio" in n or "multifam" in n or "mulfifam" in n:
            return "Edificio"
        if "casa" in n:
            return "Casa"
        return _USO_VIVIENDA_PENDIENTE

    if any(k in n for k in ("abandon", "ruina", "demolic", "solar", "terreno", "baldio")):
        return "Otros"

    return "Otros"


def tipificar_uso_con_pisos(uso_grupo: Any, num_pisos: Any) -> str:
    """
    Resuelve vivienda genérica con altura:
    1–2 pisos → Casa · ≥3 → Edificio · sin dato → residual.
    """
    g = str(uso_grupo) if uso_grupo is not None else "Otros"
    if g == "Unifamiliar":
        return "Casa"
    if g == "Multifamiliar":
        return "Edificio"
    if g not in {_USO_VIVIENDA_PENDIENTE, "Vivienda (sin tipificar)"}:
        return g
    try:
        p = float(num_pisos)
    except (TypeError, ValueError):
        return "Vivienda sin dato de pisos"
    if p != p or p <= 0:
        return "Vivienda sin dato de pisos"
    if p <= 2:
        return "Casa"
    return "Edificio"


# Familias estructurales para filtros de análisis (reduce ~1.300 textos libres)
MATERIAL_GRUPOS: tuple[str, ...] = (
    "Concreto",
    "Mixto / compuesto",
    "Mampostería formal",
    "Mampostería informal",
    "Acero / metálico",
    "Sistema túnel",
    "Tradicional liviano",
    "Otro / sin dato",
)

_SIN_MATERIAL = frozenset(
    {
        "",
        "sin evaluar",
        "no especifica",
        "sin especificar",
        "desconocido",
        "n a",
        "na",
        "none",
        "nan",
        "null",
        "-",
    }
)


# —— Capas nominales de decisión (dashboard · Uso / Material) ——
USO_CAPA_GRUPOS: tuple[str, ...] = (
    "Casa",
    "Edificio/Multifamiliar",
    "Comercio/Oficina",
    "Educativo/Asistencial",
    "Otros",
)

MATERIAL_CAPA_GRUPOS: tuple[str, ...] = (
    "Concreto",
    "Acero",
    "Mampostería Formal",
    "Mampostería Informal / Bahareque",
    "Otros / Mixto",
)

_USO_CAPA_FROM_GRUPO: dict[str, str] = {
    "Casa": "Casa",
    "Edificio": "Edificio/Multifamiliar",
    "Comercio / oficina": "Comercio/Oficina",
    "Educativo": "Educativo/Asistencial",
    "Salud": "Educativo/Asistencial",
    "Institucional": "Otros",
    "Industrial": "Otros",
    "Mixto": "Otros",
    "Otros": "Otros",
    "Vivienda sin dato de pisos": "Otros",
    "Unifamiliar": "Casa",
    "Multifamiliar": "Edificio/Multifamiliar",
}

_MATERIAL_CAPA_FROM_GRUPO: dict[str, str] = {
    "Concreto": "Concreto",
    "Acero / metálico": "Acero",
    "Mampostería formal": "Mampostería Formal",
    "Mampostería informal": "Mampostería Informal / Bahareque",
    "Tradicional liviano": "Mampostería Informal / Bahareque",
    "Mixto / compuesto": "Otros / Mixto",
    "Sistema túnel": "Otros / Mixto",
    "Otro / sin dato": "Otros / Mixto",
}


def clasificar_uso_capa(val: Any) -> str:
    """Uso → 5 categorías nominales de decisión (capa 4)."""
    s = str(val or "").strip()
    if s in _USO_CAPA_FROM_GRUPO:
        return _USO_CAPA_FROM_GRUPO[s]
    # Texto libre / variantes
    g = clasificar_uso(val)
    if g == _USO_VIVIENDA_PENDIENTE:
        return "Otros"
    return _USO_CAPA_FROM_GRUPO.get(g, "Otros")


def clasificar_material_capa(val: Any) -> str:
    """
    Material → 5 tipologías de decisión (capa 5).
    Une variantes de campo (zinc/zing, aporticado metálico, casa blanda, bahareque…).
    """
    n = fold_ascii(val)
    if n in _SIN_MATERIAL:
        return "Otros / Mixto"

    # Informal / bahareque / liviano vulnerable
    if any(
        k in n
        for k in (
            "informal",
            "bahareque",
            "baharete",
            "bajareque",
            "bajarete",
            "adobe",
            "tapia",
            "barro",
            "paja",
            "zing",
            "zinc",
            "casa blanda",
            "blanda",
            "rancho",
            "madera",
        )
    ):
        return "Mampostería Informal / Bahareque"

    has_acero = any(
        k in n
        for k in (
            "acero",
            "metal",
            "aporticado",
            "perfil",
            "summa",
            "galvaniz",
            "estructur metal",
        )
    )
    has_concreto = any(k in n for k in ("concreto", "hormigon", "armado"))
    has_mamp = any(k in n for k in ("mamposter", "bloque", "ladrillo", "muros portantes"))
    compuesto = any(sep in n for sep in (" y ", " con ")) or "/" in n or "," in str(val or "")

    if n in {"mixto", "mixta"} or "mixto" in n or "mixta" in n or "estructura mixta" in n:
        return "Otros / Mixto"
    if has_acero and has_concreto:
        return "Otros / Mixto"
    if has_acero and has_mamp:
        return "Otros / Mixto"
    if has_concreto and has_mamp and compuesto:
        return "Otros / Mixto"
    if "tunel" in n:
        return "Otros / Mixto"

    if "formal" in n or (has_mamp and not has_acero and not has_concreto):
        return "Mampostería Formal"
    if n in {"mamposteria", "mamposter"}:
        return "Mampostería Formal"

    if has_acero:
        return "Acero"
    if has_concreto:
        return "Concreto"

    # Si ya viene tipificado por clasificar_material
    g = clasificar_material(val)
    return _MATERIAL_CAPA_FROM_GRUPO.get(g, "Otros / Mixto")


def clasificar_material(val: Any) -> str:
    """Agrupa material de campo en familias estructurales coherentes."""
    n = fold_ascii(val)
    if n in _SIN_MATERIAL or n in {"otro", "otros"}:
        return "Otro / sin dato"

    if "informal" in n:
        return "Mampostería informal"

    if "tunel" in n:
        return "Sistema túnel"

    if any(
        k in n
        for k in (
            "bahareque",
            "baharete",
            "bajareque",
            "bajarete",
            "bajareke",
            "baraheque",
            "bareque",
            "adobe",
            "tapia",
            "barro",
            "madera",
            "zinc",
            "paja",
        )
    ):
        return "Tradicional liviano"

    has_acero = any(
        k in n for k in ("acero", "metal", "perfil", "summa", "galvaniz")
    )
    has_concreto = any(k in n for k in ("concreto", "hormigon"))
    has_mamp = any(k in n for k in ("mamposter", "bloque", "ladrillo", "muros portantes"))
    compuesto = any(sep in n for sep in (" y ", " con ")) or "/" in n or "," in str(val or "")

    if n in {"mixto", "mixta"} or n.startswith("mixto ") or n.startswith("mixta ") or "estructura mixta" in n:
        return "Mixto / compuesto"
    if has_acero and has_concreto:
        return "Mixto / compuesto"
    if has_acero and has_mamp:
        return "Mixto / compuesto"
    if has_concreto and has_mamp and compuesto:
        return "Mixto / compuesto"

    if "formal" in n or n in {"mamposteria", "mamposter"}:
        return "Mampostería formal"
    if has_mamp and not has_acero and not has_concreto:
        return "Mampostería formal"

    if has_acero:
        return "Acero / metálico"
    if has_concreto:
        return "Concreto"

    return "Otro / sin dato"


def normalizar_municipio(municipio: Any, estado: Any) -> str:
    """Mayúsculas + Caracas no es municipio (DC → LIBERTADOR)."""
    mun = lex_upper(municipio)
    est = lex_upper(estado, fill="")
    if mun in _NO_MUNICIPIO or fold_ascii(mun) == "caracas":
        if "DISTRITO CAPITAL" in est or est in {"DC", "DISTRITO CAPITAL"}:
            return "LIBERTADOR"
        return "SIN EVALUAR"
    return mun


def geo_en_venezuela(lat: float, lng: float) -> bool:
    if lat != lat or lng != lng:
        return False
    return VE_LAT_MIN <= float(lat) <= VE_LAT_MAX and VE_LNG_MIN <= float(lng) <= VE_LNG_MAX


def _lexico_uso_para_tipificar(out: pd.DataFrame) -> pd.Series:
    """Fuente léxica: texto libre `uso`, o `uso_raw_n`, o etiquetas legacy de `uso_n`."""
    if "uso" in out.columns:
        return out["uso"].map(clasificar_uso)
    if "uso_raw_n" in out.columns:
        return out["uso_raw_n"].map(clasificar_uso)
    if "uso_n" in out.columns:
        legacy = {
            "Unifamiliar": "Casa",
            "Multifamiliar": "Edificio",
            "Vivienda (sin tipificar)": _USO_VIVIENDA_PENDIENTE,
        }
        return out["uso_n"].map(lambda x: legacy.get(str(x), str(x)))
    return pd.Series([_USO_VIVIENDA_PENDIENTE] * len(out), index=out.index)


def aplicar_limpieza_categorica(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza territorio, material, uso (raw + grupo) y flags GPS/VE."""
    out = df.copy()

    if "estado" in out.columns:
        out["estado_n"] = out["estado"].map(lambda x: lex_upper(x, fill="(SIN ESTADO)"))
        out["estado_n"] = out["estado_n"].replace({"VARGAS": "LA GUAIRA", "DC": "DISTRITO CAPITAL"})
    else:
        out["estado_n"] = "(SIN ESTADO)"

    if "municipio" in out.columns:
        out["municipio_n"] = [
            normalizar_municipio(m, e) for m, e in zip(out["municipio"], out["estado_n"], strict=False)
        ]
    else:
        out["municipio_n"] = "SIN EVALUAR"

    if "parroquia" in out.columns:
        out["parroquia_n"] = out["parroquia"].map(lex_upper)
    else:
        out["parroquia_n"] = "SIN EVALUAR"

    if "material" in out.columns:
        out["material_n"] = out["material"].map(lex_upper)
    else:
        out["material_n"] = "SIN EVALUAR"

    if "uso" in out.columns or "uso_raw_n" in out.columns or "uso_n" in out.columns:
        if "uso" in out.columns:
            out["uso_raw_n"] = out["uso"].map(lex_upper)
        elif "uso_raw_n" not in out.columns:
            out["uso_raw_n"] = out["uso_n"].map(lex_upper) if "uso_n" in out.columns else "SIN EVALUAR"
        lex = _lexico_uso_para_tipificar(out)
        pisos = (
            pd.to_numeric(out["num_pisos"], errors="coerce")
            if "num_pisos" in out.columns
            else pd.Series(np.nan, index=out.index)
        )
        out["uso_grupo"] = [
            tipificar_uso_con_pisos(g, p) for g, p in zip(lex, pisos, strict=False)
        ]
        out["uso_n"] = out["uso_grupo"]
    else:
        out["uso_raw_n"] = "SIN EVALUAR"
        out["uso_grupo"] = "Otros"
        out["uso_n"] = "Otros"

    out["lat"] = pd.to_numeric(out.get("lat"), errors="coerce")
    out["lng"] = pd.to_numeric(out.get("lng"), errors="coerce")
    out["con_gps"] = out["lat"].notna() & out["lng"].notna()
    out["geo_en_ve"] = [
        geo_en_venezuela(a, b) for a, b in zip(out["lat"], out["lng"], strict=False)
    ]
    out["geo_valida"] = out["con_gps"] & out["geo_en_ve"]

    return out


def diagnostico_uso(antes: pd.Series, despues: pd.Series) -> pd.DataFrame:
    """Tabla larga para barras antes/después de reducción de cardinalidad."""
    a = antes.fillna("").astype(str).map(lex_upper).value_counts().head(20)
    d = despues.fillna("Otros").astype(str).value_counts()
    rows = [{"categoria": i, "conteo": int(v), "fase": "Antes (texto libre)"} for i, v in a.items()]
    rows += [{"categoria": i, "conteo": int(v), "fase": "Después (grupo)"} for i, v in d.items()]
    return pd.DataFrame(rows)


def resumen_calidad(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    n = max(len(df), 1)
    for c in cols:
        if c not in df.columns:
            continue
        s = df[c]
        if s.dtype == object or pd.api.types.is_string_dtype(s):
            na = s.isna() | s.astype(str).str.strip().isin({"", "SIN EVALUAR", "Sin Evaluar", "nan"})
        else:
            na = s.isna()
        rows.append(
            {
                "columna": c,
                "nulos_o_sin_evaluar": int(na.sum()),
                "pct": round(100.0 * float(na.sum()) / n, 2),
            }
        )
    return pd.DataFrame(rows).sort_values("pct", ascending=False)
