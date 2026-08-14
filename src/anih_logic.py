"""Lógica ANIH / Planilla V.8: riesgos A/B/C → etiqueta de acceso (vectorizado)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

RANK = {"A": 1, "B": 2, "C": 3, "": 0}
RANK_TO_ETIQUETA = {"A": "VERDE", "B": "AMARILLO", "C": "ROJO"}

RESUMEN_METODO = """
**Regla de decisión (Punto 6 · Planilla V.8):** se toma el **riesgo más desfavorable**
entre los puntos 2–5 y se asigna la etiqueta de acceso:

| Riesgo global | Etiqueta | Acceso |
|---|---|---|
| **A** Bajo | **VERDE** | Permitido |
| **B** Medio | **AMARILLO** | Restringido |
| **C** Alto | **ROJO** | No permitido |

**Atajos a ROJO:** si *Riesgo externo* = C o *Daño severo/completo* (N≥1) → etiqueta roja
sin continuar la inspección interna.

**NEGRO** (en pantalla: **Pérdida total**): extensión operativa Habitable
(pérdida total / colapso extremo); no forma parte de las tres tarjetas clásicas ANIH,
pero se conserva en el mart.
"""


def _series_abc(s: pd.Series) -> pd.Series:
    x = s.astype(str).str.strip().str.lower()
    out = pd.Series("", index=s.index, dtype=object)
    out = out.mask(x.isin(["a", "bajo"]), "A")
    out = out.mask(x.isin(["b", "medio"]), "B")
    out = out.mask(x.isin(["c", "alto"]), "C")
    return out


def _worst_abc(frames: list[pd.Series]) -> pd.Series:
    rank = pd.DataFrame({i: f.map(RANK).fillna(0) for i, f in enumerate(frames)})
    mx = rank.max(axis=1)
    inv = {1: "A", 2: "B", 3: "C", 0: ""}
    return mx.map(inv)


def riesgo_externo_series(df: pd.DataFrame) -> pd.Series:
    cols = [
        c
        for c in (
            "ext_colapso_estructura",
            "ext_peligro_aledanos",
            "ext_peligro_geologico",
            "ext_asentamiento",
            "ext_inclinacion",
        )
        if c in df.columns
    ]
    if not cols:
        return pd.Series("", index=df.index)
    abcs = [_series_abc(df[c]) for c in cols]
    return _worst_abc(abcs)


def riesgo_severo_series(df: pd.DataFrame) -> pd.Series:
    cols = [c for c in ("sev_columna", "sev_muro_concreto", "sev_muro_mamposteria", "sev_viga") if c in df.columns]
    if not cols:
        return pd.Series("", index=df.index)
    nums = pd.DataFrame({c: pd.to_numeric(df[c], errors="coerce") for c in cols})
    has_damage = (nums > 0).any(axis=1)
    evaluated = nums.notna().any(axis=1)
    out = pd.Series("", index=df.index, dtype=object)
    out = out.mask(evaluated & ~has_damage, "A")
    out = out.mask(has_damage, "C")
    return out


def riesgo_moderado_series(df: pd.DataFrame) -> pd.Series:
    pares = [
        ("mod_columna_mod", "mod_columna_exam"),
        ("mod_muro_concreto_mod", "mod_muro_concreto_exam"),
        ("mod_muro_mamposteria_mod", "mod_muro_mamposteria_exam"),
        ("mod_viga_mod", "mod_viga_exam"),
    ]
    pcts = []
    for c_mod, c_ex in pares:
        if c_mod not in df.columns or c_ex not in df.columns:
            continue
        mod = pd.to_numeric(df[c_mod], errors="coerce")
        ex = pd.to_numeric(df[c_ex], errors="coerce")
        pct = np.where((ex > 0) & mod.notna(), 100.0 * mod / ex, np.nan)
        pcts.append(pd.Series(pct, index=df.index))
    if not pcts:
        return pd.Series("", index=df.index)
    pmax = pd.concat(pcts, axis=1).max(axis=1, skipna=True)
    out = pd.Series("", index=df.index, dtype=object)
    out = out.mask(pmax.notna() & (pmax < 10), "A")
    out = out.mask(pmax.notna() & (pmax >= 10) & (pmax <= 30), "B")
    out = out.mask(pmax.notna() & (pmax > 30), "C")
    return out


def riesgo_componentes_series(df: pd.DataFrame) -> pd.Series:
    cols = [
        c
        for c in (
            "comp_losa",
            "comp_paredes",
            "comp_tanques",
            "comp_gas_agua_electricidad",
            "comp_ascensores",
        )
        if c in df.columns
    ]
    if not cols:
        return pd.Series("", index=df.index)
    mat = pd.DataFrame({c: _series_abc(df[c]) for c in cols})
    n_c = (mat == "C").sum(axis=1)
    n_b = (mat == "B").sum(axis=1)
    has = (mat.isin(["A", "B", "C"])).any(axis=1)
    out = pd.Series("", index=df.index, dtype=object)
    out = out.mask(has, "A")
    out = out.mask(has & (n_b >= 2) & (n_c == 0), "B")
    out = out.mask(n_c >= 1, "C")
    return out


def enriquecer_riesgos_anih(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["anih_ext"] = riesgo_externo_series(out)
    out["anih_sev"] = riesgo_severo_series(out)
    out["anih_mod"] = riesgo_moderado_series(out)
    out["anih_comp"] = riesgo_componentes_series(out)
    out["anih_global"] = _worst_abc(
        [out["anih_ext"], out["anih_sev"], out["anih_mod"], out["anih_comp"]]
    )
    out["anih_etiqueta_esperada"] = out["anih_global"].map(RANK_TO_ETIQUETA).fillna("")
    et = out.get("etiqueta_n", pd.Series("", index=out.index)).astype(str).str.upper()
    et_cmp = et.replace({"NEGRO": "ROJO"})
    out["anih_concordante"] = (out["anih_etiqueta_esperada"] != "") & (
        out["anih_etiqueta_esperada"] == et_cmp
    )
    return out


def resumen_elementos_abc(df: pd.DataFrame) -> pd.DataFrame:
    if "anih_ext" not in df.columns:
        df = enriquecer_riesgos_anih(df)
    rows = []
    for col, lab in [
        ("anih_ext", "2 · Riesgo externo"),
        ("anih_sev", "3 · Daño severo/completo"),
        ("anih_mod", "4 · Daño moderado"),
        ("anih_comp", "5 · Componentes"),
        ("anih_global", "6 · Riesgo global (máx.)"),
    ]:
        vc = df[col].replace("", "Sin dato").value_counts()
        row: dict[str, Any] = {"Bloque planilla": lab}
        for k in ("A", "B", "C", "Sin dato"):
            row[k] = int(vc.get(k, 0))
        rows.append(row)
    return pd.DataFrame(rows)


def clasificar_flujo_inspeccion(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clasifica cada inspección según el protocolo secuencial ANIH V.8.

    - Descarte temprano legítimo: Riesgo externo = C y sin evaluación interna
      (Pasos 3–4 vacíos). No es «dato faltante», sino salida por seguridad.
    - Paso 3: continúan a daño severo/completo.
    - Descarte en Paso 3: daño severo = C y sin Paso 4.
    - Paso 4: hay evaluación de daño moderado.
    """
    if "anih_ext" not in df.columns:
        df = enriquecer_riesgos_anih(df)
    out = df.copy()
    ext = out["anih_ext"].astype(str)
    sev = out["anih_sev"].astype(str)
    mod = out["anih_mod"].astype(str)

    descarte_ext = (ext == "C") & (sev == "") & (mod == "")
    paso3 = ~descarte_ext
    descarte_sev = paso3 & (sev == "C") & (mod == "")
    paso4 = paso3 & (mod != "")
    sin_avance = paso3 & ~descarte_sev & ~paso4

    out["flujo_descarte_ext"] = descarte_ext
    out["flujo_paso3"] = paso3
    out["flujo_descarte_sev"] = descarte_sev
    out["flujo_paso4"] = paso4
    out["flujo_sin_avance"] = sin_avance
    return out


def metricas_flujo_inspeccion(df: pd.DataFrame) -> dict[str, Any]:
    """Agregados para embudo, KPIs y síntesis narrativa."""
    f = clasificar_flujo_inspeccion(df)
    n = len(f)
    n_ext = int(f["flujo_descarte_ext"].sum())
    n_paso3 = int(f["flujo_paso3"].sum())
    n_sev = int(f["flujo_descarte_sev"].sum())
    n_paso4 = int(f["flujo_paso4"].sum())
    n_sin = int(f["flujo_sin_avance"].sum())

    # Principal causa de C interno entre quienes entraron a evaluación interna
    internos = f.loc[f["flujo_paso3"]]
    causas = {
        "daño severo/completo (Paso 3)": int((internos["anih_sev"] == "C").sum())
        if len(internos)
        else 0,
        "daño moderado (Paso 4)": int((internos["anih_mod"] == "C").sum())
        if len(internos)
        else 0,
        "componentes no estructurales (Paso 5)": int((internos["anih_comp"] == "C").sum())
        if len(internos)
        else 0,
    }
    causa_top = max(causas, key=causas.get) if any(causas.values()) else "sin señal C interna dominante"

    pct = lambda x: round(100.0 * x / max(n, 1), 1)
    return {
        "n": n,
        "n_descarte_ext": n_ext,
        "n_paso3": n_paso3,
        "n_descarte_sev": n_sev,
        "n_paso4": n_paso4,
        "n_sin_avance": n_sin,
        "pct_descarte_ext": pct(n_ext),
        "pct_paso3": pct(n_paso3),
        "pct_descarte_sev": pct(n_sev),
        "pct_paso4": pct(n_paso4),
        "pct_sin_ingresar": pct(n_ext),  # resueltas sin entrar al inmueble
        "causa_c_interna": causa_top,
        "causas_c": causas,
        "df": f,
    }


def texto_sintesis_flujo(m: dict[str, Any]) -> str:
    """Narrativa automática del embudo de decisión."""
    return (
        f"De las {m['n']:,} evaluadas".replace(",", ".")
        + f", el {m['pct_descarte_ext']}% evidenció un riesgo externo crítico, "
        "obligando a detener la inspección por protocolo de seguridad. "
        "Del grupo que requirió evaluación interna detallada, "
        f"la principal causa de asignación de etiqueta roja fue {m['causa_c_interna']}."
    )
