"""Dimensiones nominales: Uso agrupado (capa 4) y Material agrupado (capa 5)."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from streamlit_echarts import st_echarts

from analisis_nominal import (
    asociacion_nominal,
    opts_barras_riesgo_horizontal,
    sintesis_ejecutiva_nominal,
    tabla_or_vs_base,
    tabla_riesgo_por_categoria,
)
from clean_catalog import (
    MATERIAL_CAPA_GRUPOS,
    USO_CAPA_GRUPOS,
    clasificar_material_capa,
    clasificar_uso_ampliado,
    clasificar_uso_capa,
    tipificar_uso_con_pisos,
)
from export_utils import fmt_es_int
from filters_analisis import aplicar_filtros_analisis, render_filtros_analisis
from ui_theme import render_kpi_strip, render_section


def _prep_uso(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # Preferir texto crudo + nombre/obs para reclasificar Turismo en vivo
    uso_src = (
        out["uso"]
        if "uso" in out.columns
        else out["uso_raw_n"]
        if "uso_raw_n" in out.columns
        else out.get("uso_n")
    )
    if uso_src is not None:
        nom = out["nombre_edificacion"] if "nombre_edificacion" in out.columns else None
        obs = out["observaciones"] if "observaciones" in out.columns else None
        dire = out["direccion"] if "direccion" in out.columns else None
        grupos = []
        for i, u in enumerate(uso_src):
            idx = uso_src.index[i] if hasattr(uso_src, "index") else i
            n = nom.loc[idx] if nom is not None else None
            o = obs.loc[idx] if obs is not None else None
            d = dire.loc[idx] if dire is not None else None
            grupos.append(clasificar_uso_ampliado(u, nombre=n, observaciones=o, direccion=d))
        out["uso_grupo"] = grupos
        pisos = out.get("num_pisos", pd.Series(index=out.index))
        out["uso_grupo"] = [
            tipificar_uso_con_pisos(g, p) for g, p in zip(out["uso_grupo"], pisos, strict=False)
        ]
        out["uso_n"] = out["uso_grupo"]
        out["uso_capa"] = out["uso_grupo"].map(clasificar_uso_capa)
    else:
        out["uso_capa"] = "Otros"
    return out


def _prep_material(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    src = out["material_n"] if "material_n" in out.columns else out.get("material")
    if src is not None:
        out["material_capa"] = [clasificar_material_capa(x) for x in src]
    else:
        out["material_capa"] = "Otros / Mixto"
    return out


def _render_capa_nominal(
    df: pd.DataFrame,
    *,
    col_cat: str,
    titulo: str,
    subtitulo: str,
    titulo_sintesis: str,
    eje_nombre: str,
    categoria_base: str,
    orden_grupos: tuple[str, ...],
    key_prefix: str,
    filtro_cruzado: str = "uso",
) -> None:
    render_section(titulo, subtitulo)

    filtros = render_filtros_analisis(
        df,
        titulo="Filtros de este análisis",
        filtro_cruzado=filtro_cruzado,
        key_prefix=key_prefix,
    )
    dff = aplicar_filtros_analisis(df, filtros)
    st.caption(
        f"Corte activo: **{fmt_es_int(len(dff))}** de **{fmt_es_int(len(df))}** · "
        "variable nominal (sin orden temporal)."
    )
    if dff.empty:
        st.warning("El filtro no deja filas. Amplíe la selección.")
        return

    tab = tabla_riesgo_por_categoria(dff, col_cat=col_cat, orden_pref=orden_grupos)
    if tab.empty:
        st.info("Sin categorías con muestra suficiente.")
        return

    v, chi2, p, n_asoc = asociacion_nominal(dff, col_cat=col_cat)
    or_tab = tabla_or_vs_base(tab, categoria_base=categoria_base)

    n_total = len(dff)
    tasa_global = round(
        100.0 * float(dff["etiqueta_n"].isin(["ROJO", "NEGRO"]).mean()),
        1,
    )
    peor = tab.iloc[0]
    mejor = tab.iloc[-1]
    cat_peor = str(peor["Categoria"])
    cat_mejor = str(mejor["Categoria"])
    pct_peor = float(peor["pct_riesgo"])
    pct_mejor = float(mejor["pct_riesgo"])
    n_peor = int(peor["n"])
    n_mejor = int(mejor["n"])
    brecha = pct_peor / max(pct_mejor, 0.05)
    if cat_peor != cat_mejor:
        brecha_valor = f"{brecha:.1f}×"
        brecha_hint = (
            f"{cat_peor} presenta {brecha:.1f} veces más daño que {cat_mejor}"
        )
    else:
        brecha_valor = "—"
        brecha_hint = "Sin contraste entre grupos en este corte"

    render_kpi_strip(
        [
            {
                "label": "Inspecciones analizadas",
                "value": fmt_es_int(n_total),
                "hint": "Registros del corte activo",
            },
            {
                "label": "Tasa de falla general",
                "value": f"{tasa_global:.1f}%",
                "tone": "warning" if tasa_global >= 15 else "muted",
                "hint": "Rojo + pérdida total en el corte",
            },
            {
                "label": "Grupo más vulnerable",
                "value": f"{pct_peor:.1f}%",
                "tone": "warning",
                "hint": f"{cat_peor} · n={fmt_es_int(n_peor)}",
            },
            {
                "label": "Grupo más seguro",
                "value": f"{pct_mejor:.1f}%",
                "tone": "success",
                "hint": f"{cat_mejor} · n={fmt_es_int(n_mejor)}",
            },
            {
                "label": "Factor de riesgo (brecha)",
                "value": brecha_valor,
                "tone": "flag",
                "hint": brecha_hint,
            },
        ]
    )

    st.markdown(f"##### % Rojo + pérdida total por {eje_nombre}")
    st.caption(
        "Barras ordenadas de mayor a menor riesgo. "
        "Cada etiqueta muestra el % crítico y el tamaño de muestra (N)."
    )
    opts = opts_barras_riesgo_horizontal(tab)
    if opts:
        st_echarts(opts, height="420px", key=f"{key_prefix}-barras")

    st.markdown(
        sintesis_ejecutiva_nominal(
            titulo=titulo_sintesis,
            eje_nombre=eje_nombre,
            tab=tab,
            or_tab=or_tab,
            v=v,
            categoria_base=categoria_base,
        )
    )

    with st.expander("Detalle técnico (auditoría estadística)", expanded=False):
        st.caption(
            "Reservado para revisión analítica. No forma parte de la lectura operativa."
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("V de Cramer", f"{v:.3f}")
            st.caption("Fuerza de asociación (0–1)")
        with c2:
            st.metric("χ² (p)", f"{p:.3g}")
            st.caption(f"χ²={chi2:.1f} · n={fmt_es_int(n_asoc)}")
        with c3:
            st.metric("Referencia relativa", categoria_base)
            st.caption("Categoría ancla del contraste")
        if or_tab.empty:
            st.info("Sin tabla de contraste relativa en este corte.")
        else:
            show = or_tab.rename(
                columns={
                    "Categoria": "Categoría",
                    "criticos": "Rojo+pérdida total",
                    "pct_riesgo": "% crítico",
                    "OR vs base": "Multiplicador vs referencia",
                }
            )
            # Evitar jerga OR en encabezados visibles al negocio dentro del expander está OK
            # pero el usuario pidió no mencionar OR en vista principal; expander es auditoría.
            st.dataframe(show, use_container_width=True, hide_index=True)
            st.caption(
                f"Referencia: **{categoria_base}** (multiplicador = 1). "
                "Valores >1 = más daño crítico que la referencia."
            )
        st.markdown(
            f"**{eje_nombre.capitalize()}** es una variable **nominal** (sin orden natural). "
            "Por eso el contraste se hace entre categorías, no con tendencia temporal."
        )


def render_dimension_uso(df: pd.DataFrame) -> None:
    work = _prep_material(_prep_uso(df))
    _render_capa_nominal(
        work,
        col_cat="uso_capa",
        titulo="3 · Uso agrupado",
        subtitulo=(
            "Asociación nominal entre uso de la edificación y daño crítico "
            "(incluye establecimientos turísticos y comercio como categorías propias)."
        ),
        titulo_sintesis="📝 Resumen del Perfil de Riesgo",
        eje_nombre="uso de la edificación",
        categoria_base="Casa",
        orden_grupos=USO_CAPA_GRUPOS,
        key_prefix="dim-uso-capa",
        filtro_cruzado="material",
    )


def render_dimension_material(df: pd.DataFrame) -> None:
    work = _prep_uso(_prep_material(df))
    _render_capa_nominal(
        work,
        col_cat="material_capa",
        titulo="4 · Material agrupado",
        subtitulo="Asociación nominal entre tipología constructiva y daño crítico (Rojo + pérdida total).",
        titulo_sintesis="📝 Resumen del Perfil de Riesgo",
        eje_nombre="material estructural",
        categoria_base="Concreto",
        orden_grupos=MATERIAL_CAPA_GRUPOS,
        key_prefix="dim-mat-capa",
        filtro_cruzado="uso",
    )
