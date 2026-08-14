"""Análisis temporal continuo (año a año) + detección de quiebre · Habitable."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import norm
from sklearn.linear_model import LogisticRegression


@dataclass(frozen=True)
class ResultadoLogisticaAnio:
    beta: float
    se: float
    z: float
    p: float
    or_anual: float
    pct_odds_anual: float  # 100*(OR-1)
    n: int
    n_neg: int
    anio_min: float
    anio_max: float


@dataclass(frozen=True)
class ResultadoPettitt:
    anio_quiebre: int | None
    k_stat: float
    p: float
    significativo: bool
    pct_antes: float
    pct_despues: float
    n_anios: int


def serie_anual_negro(df: pd.DataFrame, *, col_anio: str = "anio_n") -> pd.DataFrame:
    """Serie año → n, NEGRO, % NEGRO (solo años tipificados)."""
    if col_anio not in df.columns or "etiqueta_n" not in df.columns:
        return pd.DataFrame(columns=["Año", "Inspecciones", "NEGRO", "% NEGRO"])
    an = pd.to_numeric(df[col_anio], errors="coerce")
    work = df.loc[an.notna()].copy()
    work["_anio"] = an.loc[work.index].astype(int)
    work = work.loc[(work["_anio"] >= 1900) & (work["_anio"] <= 2030)]
    if work.empty:
        return pd.DataFrame(columns=["Año", "Inspecciones", "NEGRO", "% NEGRO"])
    g = (
        work.groupby("_anio", dropna=False)
        .agg(
            Inspecciones=("etiqueta_n", "size"),
            NEGRO=("etiqueta_n", lambda s: int((s == "NEGRO").sum())),
        )
        .reset_index()
        .rename(columns={"_anio": "Año"})
    )
    g["% NEGRO"] = (100.0 * g["NEGRO"] / g["Inspecciones"].clip(lower=1)).round(2)
    return g.sort_values("Año").reset_index(drop=True)


def regresion_logistica_anio(
    df: pd.DataFrame,
    *,
    col_anio: str = "anio_n",
) -> ResultadoLogisticaAnio | None:
    """
    Regresión logística: P(NEGRO) ~ año continuo.
    Beta = cambio en log-odds por cada año adicional.
    """
    if col_anio not in df.columns or "etiqueta_n" not in df.columns:
        return None
    an = pd.to_numeric(df[col_anio], errors="coerce")
    mask = an.notna() & an.between(1900, 2030)
    y = (df.loc[mask, "etiqueta_n"] == "NEGRO").astype(int).to_numpy()
    x_raw = an.loc[mask].to_numpy(dtype=float)
    if y.size < 50 or y.sum() < 5 or y.sum() >= y.size - 5:
        return None
    if np.nanstd(x_raw) < 1e-9:
        return None

    mu = float(np.mean(x_raw))
    sd = float(np.std(x_raw))
    x = ((x_raw - mu) / sd).reshape(-1, 1)
    clf = LogisticRegression(C=np.inf, solver="lbfgs", max_iter=2000)
    clf.fit(x, y)
    b_std = float(clf.coef_[0, 0])
    intercept = float(clf.intercept_[0])
    beta = b_std / sd

    X = np.column_stack([np.ones(len(x)), x.ravel()])
    eta = intercept + b_std * x.ravel()
    p_hat = expit(eta)
    w = p_hat * (1.0 - p_hat)
    try:
        xtwx = X.T @ (X * w[:, None])
        cov = np.linalg.inv(xtwx)
        se_std = float(np.sqrt(max(cov[1, 1], 0.0)))
        se = se_std / sd
    except np.linalg.LinAlgError:
        se = float("nan")
    if not np.isfinite(se) or se <= 0:
        z = 0.0
        p = 1.0
    else:
        z = beta / se
        p = float(2.0 * (1.0 - norm.cdf(abs(z))))
    or_anual = float(np.exp(beta))
    pct_odds = 100.0 * (or_anual - 1.0)
    return ResultadoLogisticaAnio(
        beta=float(beta),
        se=float(se) if np.isfinite(se) else float("nan"),
        z=float(z),
        p=float(p),
        or_anual=or_anual,
        pct_odds_anual=float(pct_odds),
        n=int(y.size),
        n_neg=int(y.sum()),
        anio_min=float(np.min(x_raw)),
        anio_max=float(np.max(x_raw)),
    )


def pettitt_cambio(
    serie: pd.DataFrame,
    *,
    col_anio: str = "Año",
    col_pct: str = "% NEGRO",
    col_n: str = "Inspecciones",
    min_n_anio: int = 30,
    alpha: float = 0.05,
) -> ResultadoPettitt | None:
    """Prueba de Pettitt sobre la serie anual de % NEGRO."""
    if serie.empty or col_anio not in serie.columns or col_pct not in serie.columns:
        return None
    s = serie.copy()
    if col_n in s.columns:
        s = s.loc[s[col_n] >= min_n_anio]
    s = s.sort_values(col_anio)
    if len(s) < 8:
        return None
    x = s[col_pct].to_numpy(dtype=float)
    anios = s[col_anio].to_numpy(dtype=int)
    n = len(x)
    u = np.zeros(n - 1, dtype=float)
    for t in range(1, n):
        left = x[:t]
        right = x[t:]
        diff = left[:, None] - right[None, :]
        u[t - 1] = float(np.sign(diff).sum())
    abs_u = np.abs(u)
    k_idx = int(np.argmax(abs_u))
    k_stat = float(abs_u[k_idx])
    p = float(2.0 * np.exp((-6.0 * k_stat**2) / (n**3 + n**2)))
    p = min(max(p, 0.0), 1.0)
    anio_q = int(anios[k_idx + 1])
    pct_antes = float(np.mean(x[: k_idx + 1]))
    pct_despues = float(np.mean(x[k_idx + 1 :]))
    return ResultadoPettitt(
        anio_quiebre=anio_q,
        k_stat=k_stat,
        p=p,
        significativo=p < alpha,
        pct_antes=pct_antes,
        pct_despues=pct_despues,
        n_anios=n,
    )


def lectura_logistica(r: ResultadoLogisticaAnio | None) -> str:
    if r is None:
        return (
            "**En resumen:** no hay datos suficientes de año continuo "
            "para estimar una tendencia año a año."
        )
    if r.p < 0.05 and abs(r.pct_odds_anual) >= 0.05:
        sentido = "aumenta" if r.beta > 0 else "disminuye"
        return (
            f"**En resumen:** por cada año adicional de construcción, "
            f"la chance (odds) de **pérdida total** **{sentido}** en torno a un "
            f"**{abs(r.pct_odds_anual):.1f} %** "
            f"(razón de momios anual ≈ {r.or_anual:.3f}). "
            "Con la pérdida total poco frecuente, eso se interpreta como un cambio anual "
            "del riesgo relativo en la misma dirección."
        )
    return (
        "**En resumen:** el año continuo **no muestra** un efecto anual claro "
        f"(p = {r.p:.4g}). No fuerce una lectura de «X % por año» en este corte."
    )


def lectura_pettitt(r: ResultadoPettitt | None) -> str:
    if r is None:
        return (
            "**En resumen:** no hay serie anual suficientemente densa "
            "para detectar un punto de quiebre."
        )
    if r.significativo and r.anio_quiebre is not None:
        return (
            f"**En resumen:** el algoritmo detectó un **cambio estructural** "
            f"a partir de **{r.anio_quiebre}**. "
            f"Antes, el % con pérdida total promedio era **{r.pct_antes:.1f} %**; "
            f"después, **{r.pct_despues:.1f} %**. "
            "El salto no parece un pico aislado de un solo año."
        )
    return (
        "**En resumen:** **no** se detectó un quiebre estructural claro "
        f"en la serie anual (p = {r.p:.4g}). La variación puede ser más gradual "
        "o estar dominada por ruido en años con poca muestra."
    )


def texto_sintesis_periodo(
    *,
    v: float,
    nivel_v: str,
    log_r: ResultadoLogisticaAnio | None,
    pet_r: ResultadoPettitt | None,
    z_trend: float,
    p_trend: float,
    or_tab: pd.DataFrame,
    filtros_txt: str,
) -> str:
    """Resumen ejecutivo de riesgo temporal (pirámide invertida, accionable)."""
    _ = nivel_v  # reservado; la fuerza global se comunica con V en la recomendación
    _ = p_trend
    _ = z_trend

    hay_quiebre = (
        pet_r is not None
        and pet_r.significativo
        and pet_r.anio_quiebre is not None
    )
    anio_quiebre = str(pet_r.anio_quiebre) if hay_quiebre else None

    if log_r is not None and log_r.p < 0.05 and abs(log_r.pct_odds_anual) >= 0.05:
        cambio_anual = f"{abs(log_r.pct_odds_anual):.1f}"
        sentido_anual = "aumenta" if log_r.beta > 0 else "disminuye"
        evol_txt = (
            f"Evaluando el progreso año a año, la probabilidad (odds) de que una "
            f"inspección resulte en **pérdida total** **{sentido_anual}** sostenidamente un "
            f"**{cambio_anual} %** por cada año que avanza la fecha de construcción."
        )
    elif log_r is not None:
        evol_txt = (
            "Evaluando el progreso año a año, el cambio anual del riesgo **no es "
            "contundente** en este corte; priorice el foco por épocas y el punto "
            "de quiebre (si aparece)."
        )
    else:
        evol_txt = (
            "No hay suficiente dato continuo de año para cuantificar un cambio "
            "anual del riesgo en este corte."
        )

    banda_max = None
    or_max = None
    banda_base = None
    if not or_tab.empty and len(or_tab) > 1:
        banda_base = str(or_tab.iloc[0]["Banda"])
        top = or_tab.iloc[1:].sort_values("OR vs ref.", ascending=False).iloc[0]
        banda_max = str(top["Banda"])
        or_max = f"{float(top['OR vs ref.']):.1f}"

    if hay_quiebre:
        alerta = (
            "El riesgo de **pérdida total** **no es constante** a lo largo "
            f"del tiempo. Se detectó un **cambio estructural a partir de {anio_quiebre}**, "
            "momento en el cual la proporción de pérdidas totales comienza a escalar "
            f"({pet_r.pct_antes:.1f} % → {pet_r.pct_despues:.1f} % en promedio)."
        )
        filtro_prio = anio_quiebre
    else:
        alerta = (
            "El riesgo de **pérdida total** **varía en el tiempo**, pero "
            "en este corte **no se aisló un único año de ruptura**. El patrón puede "
            "ser más gradual: apoye la lectura en la evolución anual y en el foco por épocas."
        )
        filtro_prio = banda_max or "las épocas de mayor contraste"

    if banda_max and or_max and banda_base:
        foco_txt = (
            f"Al consolidar los datos por épocas, la tendencia alcanza su punto más "
            f"crítico en el periodo **{banda_max}**. En esta franja, la probabilidad "
            f"de **pérdida total** es **{or_max} veces mayor** si lo comparamos "
            f"con las edificaciones más antiguas (**{banda_base}**)."
        )
    else:
        foco_txt = (
            "Al consolidar por épocas, **no hay un contraste estable** frente a la "
            "banda de referencia en este corte."
        )

    return "\n".join(
        [
            "### Evaluación de Riesgo Temporal",
            f"*Corte activo:* {filtros_txt}",
            "",
            f"🚨 **Alerta Principal:** {alerta}",
            "",
            f"* **📈 Evolución Continua:** {evol_txt}",
            f"* **🎯 Foco de Mayor Riesgo:** {foco_txt}",
            "",
            "**⚠️ Recomendación de Uso:**",
            (
                f"Utilice el punto de quiebre (**{filtro_prio}**) como filtro primario "
                "para priorizar las inspecciones. Tenga en cuenta que, aunque la relación "
                "cronológica es relevante, la época de construcción determina solo una "
                f"parte del riesgo global (V de Cramer: **{v:.2f}**); factores subyacentes "
                "como los materiales utilizados o la normativa de esos años específicos "
                "suelen ser los verdaderos detonantes."
            ),
        ]
    )


def prediccion_logistica_por_anio(
    r: ResultadoLogisticaAnio,
    anios: list[int] | np.ndarray,
) -> list[float]:
    """Curva P(NEGRO)×100 predicha por la logística (overlay)."""
    xs = np.asarray(anios, dtype=float)
    p_bar = r.n_neg / max(r.n, 1)
    anio_medio = 0.5 * (r.anio_min + r.anio_max)
    logit_bar = float(np.log(p_bar / max(1.0 - p_bar, 1e-9)))
    a = logit_bar - r.beta * anio_medio
    return [round(100.0 * float(expit(a + r.beta * x)), 2) for x in xs]
