"""Confirmación de asociación NEGRO × banda ordenada (complementa V de Cramer)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm


def cochran_armitage_trend(
    n_evento: np.ndarray | list[float],
    n_total: np.ndarray | list[float],
    scores: np.ndarray | list[float] | None = None,
) -> tuple[float, float]:
    """
    Tendencia lineal en proporciones a lo largo de categorías ordenadas.
    Retorna (z, p bilateral). Scores por defecto 0..k-1.
    """
    x = np.asarray(n_evento, dtype=float)
    n = np.asarray(n_total, dtype=float)
    if x.size < 2 or n.size != x.size:
        return 0.0, 1.0
    mask = n > 0
    x, n = x[mask], n[mask]
    if x.size < 2:
        return 0.0, 1.0
    t = np.arange(x.size, dtype=float) if scores is None else np.asarray(scores, dtype=float)[mask]
    N = float(n.sum())
    r = float(x.sum())
    if N <= 0 or r <= 0 or r >= N:
        return 0.0, 1.0
    p_hat = r / N
    num = float(np.sum(t * (x - n * p_hat)))
    den = p_hat * (1.0 - p_hat) * (float(np.sum(n * t * t)) - (float(np.sum(n * t)) ** 2) / N)
    if den <= 0:
        return 0.0, 1.0
    z = num / float(np.sqrt(den))
    p = float(2.0 * (1.0 - norm.cdf(abs(z))))
    return float(z), p


def odds_ratio_wald(a: float, b: float, c: float, d: float) -> tuple[float, float, float]:
    """
    OR = (a/b)/(c/d) con corrección +0.5 si alguna celda es 0.
    a=casos expuestos, b=no casos expuestos, c=casos ref, d=no casos ref.
    Retorna (OR, IC95_lo, IC95_hi).
    """
    aa, bb, cc, dd = float(a), float(b), float(c), float(d)
    if min(aa, bb, cc, dd) == 0:
        aa, bb, cc, dd = aa + 0.5, bb + 0.5, cc + 0.5, dd + 0.5
    or_ = (aa / bb) / (cc / dd)
    se = float(np.sqrt(1 / aa + 1 / bb + 1 / cc + 1 / dd))
    log_or = float(np.log(or_))
    lo = float(np.exp(log_or - 1.96 * se))
    hi = float(np.exp(log_or + 1.96 * se))
    return float(or_), lo, hi


def tabla_or_vs_referencia(
    tab: pd.DataFrame,
    *,
    col_banda: str,
    col_n: str = "Inspecciones",
    col_neg: str = "NEGRO",
) -> pd.DataFrame:
    """OR de NEGRO por banda vs la primera fila (referencia)."""
    if tab.empty or col_banda not in tab.columns:
        return pd.DataFrame()
    ref = tab.iloc[0]
    c = float(ref[col_neg])
    d = float(ref[col_n] - ref[col_neg])
    rows: list[dict[str, Any]] = []
    for i, r in tab.iterrows():
        banda = str(r[col_banda])
        n = float(r[col_n])
        neg = float(r[col_neg])
        a, b = neg, n - neg
        if i == tab.index[0]:
            rows.append(
                {
                    "Banda": banda,
                    "n": int(n),
                    "NEGRO": int(neg),
                    "% NEGRO": round(100.0 * neg / max(n, 1), 1),
                    "OR vs ref.": 1.0,
                    "IC95 lo": 1.0,
                    "IC95 hi": 1.0,
                    "nota": "Referencia",
                }
            )
            continue
        or_, lo, hi = odds_ratio_wald(a, b, c, d)
        rows.append(
            {
                "Banda": banda,
                "n": int(n),
                "NEGRO": int(neg),
                "% NEGRO": round(100.0 * neg / max(n, 1), 1),
                "OR vs ref.": round(or_, 2),
                "IC95 lo": round(lo, 2),
                "IC95 hi": round(hi, 2),
                "nota": "Mayor que ref." if or_ > 1 else ("Menor que ref." if or_ < 1 else "Similar"),
            }
        )
    return pd.DataFrame(rows)


def texto_confirmacion(
    *,
    z_trend: float,
    p_trend: float,
    or_tab: pd.DataFrame,
    nombre_eje: str,
) -> str:
    """Texto didáctico adaptativo para tendencia + OR."""
    if p_trend < 0.01 and abs(z_trend) >= 1.96:
        sentido = "creciente" if z_trend > 0 else "decreciente"
        tend = (
            f"La prueba de **tendencia (Cochran–Armitage)** detecta una pauta **{sentido}** "
            f"del % con pérdida total a lo largo de {nombre_eje} (z={z_trend:.2f}, p={p_trend:.4g}). "
            "Eso refuerza que el orden de las bandas importa, no solo que las categorías difieren."
        )
    elif p_trend < 0.05:
        sentido = "creciente" if z_trend > 0 else "decreciente"
        tend = (
            f"Hay indicios de tendencia **{sentido}** (z={z_trend:.2f}, p={p_trend:.4g}), "
            "aunque el señalamiento es más suave."
        )
    else:
        tend = (
            f"La tendencia ordenada **no es concluyente** (z={z_trend:.2f}, p={p_trend:.4g}): "
            "puede haber diferencias entre bandas sin un aumento/descenso sistemático."
        )

    if or_tab.empty or len(or_tab) < 2:
        ors = "No hay bandas suficientes para razones de momios."
    else:
        ref = str(or_tab.iloc[0]["Banda"])
        sub = or_tab.iloc[1:].copy()
        if sub.empty:
            ors = f"Referencia: **{ref}**."
        else:
            top = sub.sort_values("OR vs ref.", ascending=False).iloc[0]
            ors = (
                f"Tomando **{ref}** como referencia, el OR más alto está en **{top['Banda']}** "
                f"(OR={top['OR vs ref.']:.2f}, IC95 {top['IC95 lo']:.2f}–{top['IC95 hi']:.2f}). "
                "OR>1 = más chance de pérdida total que la referencia; el IC que no cruza 1 sugiere diferencia estable."
            )

    return (
        f"**Pruebas de confirmación** (complementan la V de Cramer)\n\n"
        f"1. {tend}\n\n"
        f"2. {ors}\n\n"
        "Ninguna de estas pruebas demuestra causalidad; describen asociación en el corte filtrado."
    )


def _nivel_v(v: float) -> str:
    if v < 0.05:
        return "muy débil"
    if v < 0.15:
        return "débil"
    if v < 0.25:
        return "moderada"
    return "notable"


def lectura_didactica_cramer(*, v: float, p: float, n_neg: int, n: int) -> str:
    """Respuesta de analista bajo V de Cramer (no explica la escala)."""
    nivel = _nivel_v(v)
    pct = 100.0 * n_neg / max(n, 1)
    n_neg_fmt = f"{n_neg:,}".replace(",", ".")
    n_fmt = f"{n:,}".replace(",", ".")
    hay = p < 0.05 and v >= 0.05
    if hay:
        cabeza = (
            f"**En resumen:** sí hay relación, pero es **{nivel}**. "
            "Conocer la banda nos da una pista sobre si habrá "
            "**pérdida total**, pero **no es el único factor** en juego."
        )
    elif p < 0.05:
        cabeza = (
            f"**En resumen:** el vínculo es **{nivel}** (casi nulo en la práctica). "
            "Conviene no priorizar solo por esta dimensión."
        )
    else:
        cabeza = (
            "**En resumen:** **no hay evidencia clara** de relación en este corte. "
            "No use esta dimensión sola para priorizar."
        )
    if p < 0.01:
        detalle = (
            "*(Detalle técnico: la prueba indica que este vínculo no es casualidad "
            f"matemática. Base: **{pct:.1f} %** de la muestra tiene pérdida total "
            f"— {n_neg_fmt} de {n_fmt}).*"
        )
    else:
        detalle = (
            f"*(Detalle técnico: la evidencia estadística es frágil. Base: **{pct:.1f} %** "
            f"con pérdida total — {n_neg_fmt} de {n_fmt}).*"
        )
    return f"{cabeza}\n\n{detalle}"


def lectura_didactica_tendencia(*, z: float, p: float) -> str:
    """Respuesta de analista sobre si el orden de bandas importa."""
    if p < 0.05 and abs(z) >= 1.64:
        if z > 0:
            return (
                "**En resumen:** sí. A medida que avanzamos en el orden de las bandas, "
                "la proporción de **pérdida total** **sube de forma constante**. "
                "Eso confirma una **tendencia clara**, no solo un pico aislado al azar."
            )
        return (
            "**En resumen:** sí. A medida que avanzamos en el orden de las bandas, "
            "la proporción de **pérdida total** **baja de forma constante**. "
            "Hay una **tendencia clara** (descendente), no solo un pico aislado."
        )
    return (
        "**En resumen:** el orden **no muestra una tendencia clara**. "
        "Puede haber diferencias entre bandas, pero no una subida o bajada sistemática."
    )


def lectura_didactica_or(or_tab: pd.DataFrame) -> str:
    """Respuesta de analista: dónde está el mayor contraste vs referencia."""
    if or_tab.empty or len(or_tab) < 2:
        return (
            "**En resumen:** no hay bandas suficientes para señalar un punto de mayor contraste."
        )
    ref = str(or_tab.iloc[0]["Banda"])
    top = or_tab.iloc[1:].sort_values("OR vs ref.", ascending=False).iloc[0]
    or_v = float(top["OR vs ref."])
    lo, hi = float(top["IC95 lo"]), float(top["IC95 hi"])
    estable = lo > 1.0 or hi < 1.0
    banda = str(top["Banda"])
    if or_v >= 1:
        estable_txt = (
            "La diferencia es **altamente estable**."
            if estable
            else "La diferencia existe, pero el intervalo es frágil: léala con cautela."
        )
        return (
            f"**En resumen:** el momento (o banda) de mayor contraste es **{banda}**. "
            f"Ahí, la probabilidad de **pérdida total** es unas **{or_v:.1f} veces mayor** "
            f"si lo comparamos con **{ref}**. {estable_txt}"
        )
    estable_txt = (
        "La diferencia es **estable**."
        if estable
        else "El contraste es frágil: léalo con cautela."
    )
    return (
        f"**En resumen:** el contraste más marcado frente a **{ref}** está en **{banda}**, "
        f"con **menos** chance de pérdida total (razón de momios {or_v:.2f}). {estable_txt}"
    )


def markdown_guia_pruebas(*, nombre_eje: str = "la banda") -> str:
    """Guía didáctica fija para el menú desplegable final."""
    return f"""
### ¿Para qué sirven estas pruebas?

Trabajan en equipo. Ninguna sustituye a las otras y **ninguna demuestra causalidad**.

---

#### 1. V de Cramer (asociación categórica)

- **Pregunta que responde:** ¿{nombre_eje.capitalize()} y el **pérdida total** están ligados, sin importar el *orden* de las bandas?
- **Escala:** 0 = sin asociación · cerca de 1 = asociación muy fuerte.
- **Guía práctica:** &lt;0,05 muy débil · 0,05–0,15 débil · 0,15–0,25 moderada · &gt;0,25 notable.
- **χ² y p:** la p dice si el patrón podría ser casualidad. Con *n* grande, p suele ser muy pequeña aunque V sea baja: **fuerza (V) ≠ significación (p)**.
- **Límite:** no usa el orden temporal/altura; solo “las categorías difieren”.

#### 2. Tendencia Cochran–Armitage

- **Pregunta que responde:** ¿el % con **pérdida total** **sube o baja** de forma sistemática al recorrer {nombre_eje} en orden?
- **z:** positivo → tendencia ascendente; negativo → descendente. |z| grande y p pequeña → tendencia creíble.
- **Por qué importa:** complementa a Cramer. Puede haber asociación (bandas distintas) **sin** tendencia, o una tendencia clara que el gráfico ya sugiere.
- **Límite:** asume un orden razonable de bandas; no prueba *por qué* ocurre el patrón.

#### 3. Razón de momios vs banda de referencia

- **Pregunta que responde:** respecto a la **primera banda** (referencia), ¿cuánto cambia la chance de **pérdida total** en cada otra banda?
- **Razón = 1:** igual que la referencia · **&gt; 1:** más chance de pérdida total · **&lt; 1:** menos chance.
- **IC95:** si el intervalo no incluye 1, la diferencia es más estable; si lo cruza, es frágil.
- **Límite:** depende de la banda elegida como referencia; un valor alto en una banda con pocas inspecciones debe leerse con cuidado.

#### 4. Cómo leerlas juntas

1. Mire el **gráfico** (patrón visual).
2. Mire **V de Cramer** (¿hay vínculo en general?).
3. Mire la **tendencia** (¿el orden importa?).
4. Mire la **razón de momios** (¿qué banda se separa más de la referencia?).
5. Recuerde: uso, material, municipio u otras variables pueden **confundir** el patrón. Asociación ≠ causa.
""".strip()


def texto_conclusion_asociacion(
    *,
    v: float,
    p_cramer: float,
    n: int,
    n_neg: int,
    z_trend: float,
    p_trend: float,
    or_tab: pd.DataFrame,
    tab: pd.DataFrame,
    filtros_txt: str,
    nombre_eje: str,
) -> str:
    """Conclusión didáctica en bloques (panorama · tendencia · foco · práctica · veredicto)."""
    nivel = _nivel_v(v)
    pct_neg = 100.0 * n_neg / max(n, 1)
    n_fmt = f"{n:,}".replace(",", ".")
    n_neg_fmt = f"{n_neg:,}".replace(",", ".")

    viejo = reciente = None
    pico_banda = ""
    pico_pct = None
    n_pico = ""
    if not tab.empty and len(tab) >= 2 and "Banda" in tab.columns and "% NEGRO" in tab.columns:
        mitad = max(1, len(tab) // 3)
        viejo = float(tab.head(mitad)["% NEGRO"].mean())
        reciente = float(tab.tail(mitad)["% NEGRO"].mean())
        pico = tab.loc[tab["% NEGRO"].idxmax()]
        pico_banda = str(pico["Banda"])
        pico_pct = float(pico["% NEGRO"])
        n_pico = f"{int(pico['Inspecciones']):,}".replace(",", ".")

    hay_tend = p_trend < 0.05 and abs(z_trend) >= 1.64
    sentido = "ascendente" if z_trend > 0 else "descendente"
    hay_asoc = p_cramer < 0.05 and v >= 0.05

    or_banda = ""
    or_v = None
    ref = ""
    or_estable = False
    if not or_tab.empty and len(or_tab) > 1:
        ref = str(or_tab.iloc[0]["Banda"])
        top = or_tab.iloc[1:].sort_values("OR vs ref.", ascending=False).iloc[0]
        or_banda = str(top["Banda"])
        or_v = float(top["OR vs ref."])
        lo, hi = float(top["IC95 lo"]), float(top["IC95 hi"])
        or_estable = lo > 1.0 or hi < 1.0

    # Panorama
    if hay_asoc:
        panorama = (
            f"Existe una relación **real**, aunque **{nivel}**, entre {nombre_eje} "
            "y la aparición del **pérdida total**."
        )
    else:
        panorama = (
            f"En este corte **no hay una relación útil** clara entre {nombre_eje} "
            "y el **pérdida total**."
        )

    # Tendencia
    if hay_tend and viejo is not None and reciente is not None:
        if z_trend > 0:
            tendencia = (
                f"El gráfico muestra un patrón **ascendente** claro. "
                f"Los casos con pérdida total son menos frecuentes en las bandas iniciales "
                f"({viejo:.1f} %) y suben en las posteriores (promedio {reciente:.1f} %)."
            )
        else:
            tendencia = (
                f"El gráfico muestra un patrón **descendente**. "
                f"Las bandas iniciales promedian {viejo:.1f} % con pérdida total y las posteriores "
                f"{reciente:.1f} %."
            )
    elif viejo is not None and reciente is not None:
        tendencia = (
            f"Las bandas iniciales promedian {viejo:.1f} % con pérdida total y las posteriores "
            f"{reciente:.1f} %, pero **sin una tendencia ordenada concluyente**."
        )
    else:
        tendencia = "No hay bandas suficientes para describir un patrón temporal o de orden."

    # Foco
    if or_v is not None and or_v >= 1 and or_banda:
        foco = (
            f"El pico / contraste máximo se ubica en **{or_banda}**"
            + (f" ({pico_pct:.1f} %, n={n_pico})" if pico_pct is not None else "")
            + f". Frente a **{ref}**, la probabilidad de pérdida total es unas "
            f"**{or_v:.1f} veces mayor**"
            + ("." if or_estable else " (intervalo frágil: leer con cautela).")
        )
    elif pico_banda:
        foco = (
            f"El máximo observado está en **{pico_banda}** "
            f"({pico_pct:.1f} %, n={n_pico})."
        )
    else:
        foco = "No hay un foco de contraste claro en este corte."

    # Veredicto
    if hay_asoc and hay_tend and z_trend > 0:
        veredicto = (
            f"**Sí hay relación.** El porcentaje con pérdida total sube de forma sistemática "
            f"a lo largo de {nombre_eje}. Úselo como guía de priorización, "
            "pero analícelo junto con otras variables."
        )
    elif hay_asoc and hay_tend and z_trend < 0:
        veredicto = (
            f"**Sí hay relación**, con pauta **descendente** a lo largo de {nombre_eje}. "
            "Úselo como guía, junto con uso, material y territorio."
        )
    elif hay_asoc:
        veredicto = (
            f"**Sí hay relación** ({nivel}), pero **sin una sola tendencia de orden**. "
            "Sirve para matizar; no alcanza sola para priorizar por rampa."
        )
    else:
        veredicto = (
            f"**No hay evidencia suficiente** de una relación útil entre {nombre_eje} "
            "y el pérdida total en este corte. Evite conclusiones fuertes solo con estos números."
        )

    return "\n\n".join(
        [
            f"**Conclusión del análisis** · corte: {filtros_txt}",
            (
                f"En este segmento se analizaron **{n_fmt}** inspecciones, de las cuales "
                f"un **{pct_neg:.1f} %** ({n_neg_fmt}) recibieron **pérdida total**. "
                "¿Qué nos dicen los datos?"
            ),
            f"**El panorama general:** {panorama}",
            f"**La tendencia:** {tendencia}",
            f"**El foco de atención:** {foco}",
            (
                "**En la práctica:** use esta lectura como **señal de alerta** para priorizar. "
                "Recuerde: **correlación no es causalidad** — el año o la altura por sí solos "
                "no «causan» el pérdida total; uso, material o territorio pueden estar detrás de los números."
            ),
            f"**Veredicto:** {veredicto}",
        ]
    )

