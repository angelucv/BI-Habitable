"""Tema visual ejecutivo del BI (CSS + bloques de cabecera/KPI)."""

from __future__ import annotations

import streamlit as st

# Paleta institucional + acentos bandera VE (discreto)
NAVY = "#0C2340"
STEEL = "#1F4E79"
ACCENT = "#2A6F97"
INK = "#0F172A"
MUTED = "#334155"
LINE = "#CBD5E1"
SURFACE = "#FFFFFF"
PAGE = "#F4F6F9"
SUCCESS = "#166534"
WARN = "#9A3412"
# Bandera Venezuela
VE_YELLOW = "#FCD116"
VE_BLUE = "#0033A0"
VE_RED = "#CF142B"
SIDEBAR_TEXT = "#F1F5F9"
SIDEBAR_MUTED = "#CBD5E1"


def inject_executive_css() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&family=Source+Sans+3:wght@400;500;600;700&display=swap');

        html, body, [class*="css"], .stApp {{
            font-family: 'Source Sans 3', 'Segoe UI', sans-serif;
            color: {INK};
        }}
        .stApp {{
            background: {PAGE};
        }}
        [data-testid="stHeader"] {{
            background: rgba(244, 246, 249, 0.92);
            border-bottom: 1px solid {LINE};
        }}

        /* —— Cinta bandera VE (discreta) —— */
        .ve-ribbon {{
            display: flex;
            flex-direction: column;
            border-radius: 8px 8px 0 0;
            overflow: hidden;
            margin: 0 0 0.55rem 0;
            box-shadow: 0 1px 2px rgba(12, 35, 64, 0.08);
        }}
        .ve-stripe {{
            height: 7px;
            width: 100%;
        }}
        .ve-stripe-y {{ background: {VE_YELLOW}; }}
        .ve-stripe-b {{
            background: {VE_BLUE};
            height: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 7px;
        }}
        .ve-stripe-r {{ background: {VE_RED}; }}
        .ve-star {{
            width: 9px;
            height: 9px;
            display: inline-block;
            background: #FFFFFF;
            clip-path: polygon(
                50% 0%, 61% 35%, 98% 35%, 68% 57%,
                79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%
            );
            opacity: 1;
        }}

        /* —— Sidebar navy —— */
        [data-testid="stSidebar"] {{
            background: {NAVY} !important;
            border-right: none;
        }}
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3,
        section[data-testid="stSidebar"] .stMarkdown,
        section[data-testid="stSidebar"] .stMarkdown p,
        section[data-testid="stSidebar"] .stMarkdown strong,
        section[data-testid="stSidebar"] .stCaption,
        section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
        section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {{
            color: {SIDEBAR_TEXT} !important;
        }}
        section[data-testid="stSidebar"] hr {{
            border-color: rgba(255,255,255,0.22);
        }}
        section[data-testid="stSidebar"] div[data-testid="stMetric"] {{
            background: rgba(255,255,255,0.10) !important;
            border: 1px solid rgba(255,255,255,0.22) !important;
            border-top: 3px solid {VE_YELLOW} !important;
            border-radius: 8px;
            padding: 0.75rem 0.9rem;
        }}
        section[data-testid="stSidebar"] div[data-testid="stMetric"] label,
        section[data-testid="stSidebar"] div[data-testid="stMetric"] p,
        section[data-testid="stSidebar"] div[data-testid="stMetric"] span,
        section[data-testid="stSidebar"] div[data-testid="stMetric"] div {{
            color: #F8FAFC !important;
            opacity: 1 !important;
        }}
        section[data-testid="stSidebar"] div[data-testid="stMetricValue"],
        section[data-testid="stSidebar"] div[data-testid="stMetricValue"] * {{
            color: #FFFFFF !important;
            font-family: 'Source Serif 4', Georgia, serif !important;
            font-size: 1.45rem !important;
            font-weight: 700 !important;
            opacity: 1 !important;
        }}
        section[data-testid="stSidebar"] div[data-testid="stMetricLabel"],
        section[data-testid="stSidebar"] div[data-testid="stMetricLabel"] *,
        section[data-testid="stSidebar"] div[data-testid="stMetricLabel"] label,
        section[data-testid="stSidebar"] div[data-testid="stMetricLabel"] p {{
            color: #E2E8F0 !important;
            font-weight: 700 !important;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            font-size: 0.72rem !important;
            opacity: 1 !important;
        }}
        section[data-testid="stSidebar"] .stButton > button {{
            background: #FFFFFF !important;
            color: {NAVY} !important;
            border: 1px solid #FFFFFF !important;
            font-weight: 700 !important;
        }}
        section[data-testid="stSidebar"] .stButton > button:hover {{
            background: #E2E8F0 !important;
            color: {NAVY} !important;
        }}
        section[data-testid="stSidebar"] .stButton > button p,
        section[data-testid="stSidebar"] .stButton > button span {{
            color: {NAVY} !important;
        }}

        /* —— Menú lateral: botones compactos —— */
        section[data-testid="stSidebar"] div[class*="st-key-nav_"] button {{
            min-height: 2.05rem !important;
            padding: 0.28rem 0.45rem !important;
            border-radius: 8px !important;
            font-size: 0.78rem !important;
            font-weight: 700 !important;
            justify-content: center !important;
            text-align: center !important;
            margin-bottom: 0.28rem !important;
            line-height: 1.15 !important;
            white-space: normal !important;
        }}
        section[data-testid="stSidebar"] div[class*="st-key-nav_home"] button[kind="secondary"],
        section[data-testid="stSidebar"] div[class*="st-key-nav_sec_"] button[kind="secondary"],
        section[data-testid="stSidebar"] div[class*="st-key-nav_item_"] button[kind="secondary"] {{
            background: rgba(255,255,255,0.14) !important;
            border: 1px solid rgba(255,255,255,0.45) !important;
            color: #FFFFFF !important;
        }}
        section[data-testid="stSidebar"] div[class*="st-key-nav_home"] button[kind="secondary"] p,
        section[data-testid="stSidebar"] div[class*="st-key-nav_home"] button[kind="secondary"] span,
        section[data-testid="stSidebar"] div[class*="st-key-nav_sec_"] button[kind="secondary"] p,
        section[data-testid="stSidebar"] div[class*="st-key-nav_sec_"] button[kind="secondary"] span,
        section[data-testid="stSidebar"] div[class*="st-key-nav_item_"] button[kind="secondary"] p,
        section[data-testid="stSidebar"] div[class*="st-key-nav_item_"] button[kind="secondary"] span {{
            color: #FFFFFF !important;
            font-weight: 700 !important;
            opacity: 1 !important;
        }}
        section[data-testid="stSidebar"] div[class*="st-key-nav_home"] button[kind="primary"],
        section[data-testid="stSidebar"] div[class*="st-key-nav_sec_"] button[kind="primary"],
        section[data-testid="stSidebar"] div[class*="st-key-nav_item_"] button[kind="primary"] {{
            background: #FFFFFF !important;
            border: 1px solid {VE_YELLOW} !important;
            box-shadow: inset 3px 0 0 0 {VE_YELLOW} !important;
            color: {NAVY} !important;
        }}
        section[data-testid="stSidebar"] div[class*="st-key-nav_home"] button[kind="primary"] p,
        section[data-testid="stSidebar"] div[class*="st-key-nav_home"] button[kind="primary"] span,
        section[data-testid="stSidebar"] div[class*="st-key-nav_sec_"] button[kind="primary"] p,
        section[data-testid="stSidebar"] div[class*="st-key-nav_sec_"] button[kind="primary"] span,
        section[data-testid="stSidebar"] div[class*="st-key-nav_item_"] button[kind="primary"] p,
        section[data-testid="stSidebar"] div[class*="st-key-nav_item_"] button[kind="primary"] span {{
            color: {NAVY} !important;
            font-weight: 700 !important;
            opacity: 1 !important;
        }}
        /* Subítems del análisis dimensional: alineados a la izquierda */
        section[data-testid="stSidebar"] div[class*="st-key-nav_item_"] button {{
            justify-content: flex-start !important;
            text-align: left !important;
            font-size: 0.74rem !important;
            min-height: 1.85rem !important;
        }}
        section[data-testid="stSidebar"] h3 {{
            color: #FFFFFF !important;
            font-weight: 700 !important;
        }}

        /* —— Menú principal (atajo 2×2 compacto) —— */
        div[class*="st-key-main_nav_"] button {{
            min-height: 2.15rem !important;
            padding: 0.3rem 0.5rem !important;
            border-radius: 8px !important;
            font-size: 0.82rem !important;
            font-weight: 700 !important;
            margin-bottom: 0.35rem !important;
            line-height: 1.15 !important;
            white-space: normal !important;
        }}
        section[data-testid="stSidebar"] .stCaption,
        section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {{
            color: #E2E8F0 !important;
            opacity: 1 !important;
        }}

        /* —— Etiquetas de widgets (legibles sobre navy) —— */
        section[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
        section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
        section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] label,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] .stMultiSelect label,
        section[data-testid="stSidebar"] .stSlider label,
        section[data-testid="stSidebar"] .stCheckbox label,
        section[data-testid="stSidebar"] .stCheckbox p {{
            color: #F8FAFC !important;
            font-weight: 600 !important;
            opacity: 1 !important;
        }}
        section[data-testid="stSidebar"] {{
            padding-top: 0.35rem !important;
        }}
        section[data-testid="stSidebar"] > div:first-child {{
            padding: 0.6rem 0.85rem 1.2rem 0.85rem !important;
        }}

        /* —— st.metric como tarjeta analítica —— */
        div[data-testid="stMetric"] {{
            background: {SURFACE};
            border: 1px solid {LINE};
            border-radius: 10px;
            padding: 0.85rem 1rem 0.75rem;
            border-top: 3px solid {STEEL};
            box-shadow: 0 1px 2px rgba(12, 35, 64, 0.06);
        }}
        div[data-testid="stMetricLabel"] {{
            color: {MUTED} !important;
            font-weight: 600 !important;
        }}
        div[data-testid="stMetricValue"] {{
            font-family: 'Source Serif 4', Georgia, serif !important;
            color: {NAVY} !important;
        }}

        .filtro-pie {{
            margin-top: 0.75rem;
            padding: 0.65rem 0.75rem;
            border-radius: 8px;
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.18);
            border-top: 3px solid {VE_YELLOW};
            color: #F8FAFC;
            font-size: 0.82rem;
            line-height: 1.35;
        }}
        .filtro-pie strong {{
            color: #FFFFFF;
            font-size: 1.05rem;
        }}

        /* —— Índice inicio —— */
        .nav-index {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.85rem;
            margin: 0.5rem 0 1.2rem 0;
        }}
        @media (max-width: 900px) {{
            .nav-index {{ grid-template-columns: 1fr; }}
        }}
        .nav-index-card {{
            background: {SURFACE};
            border: 1px solid {LINE};
            border-radius: 10px;
            padding: 0.95rem 1.05rem 0.85rem;
            border-top: 3px solid {STEEL};
        }}
        .nav-index-card h3 {{
            font-family: 'Source Serif 4', Georgia, serif;
            font-size: 1.1rem;
            color: {NAVY};
            margin: 0 0 0.35rem 0;
        }}
        .nav-index-card p {{
            color: {MUTED};
            font-size: 0.88rem;
            margin: 0 0 0.55rem 0;
            line-height: 1.4;
        }}
        .nav-index-card ul {{
            margin: 0;
            padding-left: 1.1rem;
            color: {INK};
            font-size: 0.86rem;
        }}
        .nav-index-card li {{
            margin: 0.15rem 0;
        }}
        .nav-crumb {{
            color: {MUTED};
            font-size: 0.78rem;
            font-weight: 600;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            margin: 0 0 0.35rem 0;
        }}

        /* —— Hero —— */
        .bi-hero {{
            background: linear-gradient(105deg, {NAVY} 0%, {STEEL} 52%, {ACCENT} 100%);
            color: #F8FAFC;
            padding: 1.25rem 1.5rem 1.15rem;
            border-radius: 0 0 10px 10px;
            margin-bottom: 1rem;
            border-left: 4px solid {VE_YELLOW};
            border-right: 4px solid {VE_RED};
        }}
        .bi-hero-kicker {{
            font-size: 0.72rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #E2E8F0 !important;
            font-weight: 600;
            margin: 0 0 0.35rem 0;
        }}
        .bi-hero h1 {{
            font-family: 'Source Serif 4', Georgia, serif;
            font-size: 1.75rem;
            font-weight: 700;
            margin: 0 0 0.4rem 0;
            line-height: 1.2;
            color: #FFFFFF !important;
        }}
        .bi-hero p {{
            margin: 0;
            font-size: 0.95rem;
            color: #F1F5F9 !important;
            max-width: 52rem;
            line-height: 1.45;
            opacity: 1 !important;
        }}

        /* —— KPI strip —— */
        .kpi-strip {{
            display: grid;
            grid-template-columns: repeat(var(--kpi-cols, 5), minmax(0, 1fr));
            gap: 0.75rem;
            margin: 0.4rem 0 1rem 0;
        }}
        @media (max-width: 1100px) {{
            .kpi-strip {{ grid-template-columns: repeat(min(3, var(--kpi-cols, 3)), minmax(0, 1fr)); }}
        }}
        @media (max-width: 700px) {{
            .kpi-strip {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
        }}
        .kpi-card {{
            background: {SURFACE};
            border: 1px solid {LINE};
            border-radius: 8px;
            padding: 0.85rem 1rem 0.75rem;
            border-top: 3px solid {STEEL};
            min-width: 0;
        }}
        .kpi-card.tone-success {{ border-top-color: {SUCCESS}; }}
        .kpi-card.tone-info {{ border-top-color: {ACCENT}; }}
        .kpi-card.tone-warning {{ border-top-color: {VE_RED}; }}
        .kpi-card.tone-muted {{ border-top-color: #64748B; }}
        .kpi-card.tone-flag {{ border-top-color: {VE_YELLOW}; }}
        .kpi-card.tone-hero {{
            border-top-color: {ACCENT};
            border-color: {ACCENT};
            background: linear-gradient(180deg, #EEF5FB 0%, {SURFACE} 55%);
            box-shadow: 0 1px 0 rgba(15, 41, 66, 0.04);
        }}
        .kpi-card.tone-hero .kpi-label {{ color: {ACCENT}; }}
        .kpi-card.tone-hero .kpi-value {{
            color: {NAVY};
            font-size: 1.15rem;
            white-space: normal;
            line-height: 1.2;
        }}
        .pdna-exec-summary {{
            background: {SURFACE};
            border: 1px solid {LINE};
            border-left: 4px solid {ACCENT};
            border-radius: 8px;
            padding: 1rem 1.15rem 0.95rem;
            margin: 0.75rem 0 1rem 0;
        }}
        .pdna-exec-summary h3 {{
            margin: 0 0 0.65rem 0;
            font-size: 1.05rem;
            color: {NAVY};
            font-family: 'Source Serif 4', Georgia, serif;
        }}
        .pdna-exec-summary p {{
            margin: 0 0 0.55rem 0;
            color: {INK};
            line-height: 1.45;
            font-size: 0.95rem;
        }}
        .pdna-exec-summary ul {{
            margin: 0.35rem 0 0 1.1rem;
            padding: 0;
            color: {INK};
            font-size: 0.95rem;
            line-height: 1.45;
        }}
        div[data-testid="stDataFrame"] thead th {{
            white-space: normal !important;
            word-break: break-word;
            line-height: 1.2;
            vertical-align: bottom;
        }}
        .pdna-guide-grid {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.75rem;
            margin: 0.75rem 0 1rem 0;
        }}
        @media (max-width: 900px) {{
            .pdna-guide-grid {{ grid-template-columns: 1fr; }}
        }}
        .pdna-guide-card {{
            background: {SURFACE};
            border: 1px solid {LINE};
            border-radius: 8px;
            padding: 0.9rem 1rem;
            border-top: 3px solid {STEEL};
        }}
        .pdna-guide-card.calibrar {{ border-top-color: {ACCENT}; }}
        .pdna-guide-card.fijo {{ border-top-color: #64748B; }}
        .pdna-guide-card h4 {{
            margin: 0 0 0.4rem 0;
            font-size: 0.95rem;
            color: {NAVY};
            font-family: 'Source Serif 4', Georgia, serif;
        }}
        .pdna-guide-card p, .pdna-guide-card li {{
            margin: 0;
            font-size: 0.88rem;
            line-height: 1.4;
            color: {INK};
        }}
        .pdna-guide-card ul {{ margin: 0.35rem 0 0 1rem; padding: 0; }}
        .pdna-guide-tag {{
            display: inline-block;
            font-size: 0.68rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            padding: 0.15rem 0.45rem;
            border-radius: 4px;
            margin-bottom: 0.45rem;
        }}
        .pdna-guide-tag.calibrar {{ background: #E8F1F8; color: {ACCENT}; }}
        .pdna-guide-tag.fijo {{ background: #F1F5F9; color: #64748B; }}
        .pdna-flow {{
            background: {SURFACE};
            border: 1px solid {LINE};
            border-radius: 8px;
            padding: 1rem 1.1rem;
            margin: 0.5rem 0 1rem 0;
            font-family: ui-monospace, Consolas, monospace;
            font-size: 0.82rem;
            line-height: 1.55;
            color: {NAVY};
            white-space: pre-wrap;
        }}
        .kpi-label {{
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            color: {MUTED};
            margin-bottom: 0.35rem;
        }}
        .kpi-value {{
            font-family: 'Source Serif 4', Georgia, serif;
            font-size: 1.55rem;
            font-weight: 700;
            color: {NAVY};
            line-height: 1.1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .kpi-hint {{
            font-size: 0.78rem;
            color: {MUTED};
            margin-top: 0.25rem;
            font-weight: 500;
            white-space: normal;
            line-height: 1.25;
        }}

        /* Filas KPI (paneles estrechos / inicio) */
        .kpi-rows {{
            display: flex;
            flex-direction: column;
            gap: 0.45rem;
            margin: 0.55rem 0 0.35rem 0;
        }}
        .kpi-row {{
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            gap: 0.75rem;
            background: {SURFACE};
            border: 1px solid {LINE};
            border-radius: 8px;
            padding: 0.55rem 0.85rem;
            border-left: 3px solid {STEEL};
        }}
        .kpi-row.tone-success {{ border-left-color: {SUCCESS}; }}
        .kpi-row.tone-info {{ border-left-color: {ACCENT}; }}
        .kpi-row.tone-warning {{ border-left-color: {VE_RED}; }}
        .kpi-row.tone-muted {{ border-left-color: #64748B; }}
        .kpi-row.tone-flag {{ border-left-color: {VE_YELLOW}; }}
        .kpi-row-label {{
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.03em;
            text-transform: uppercase;
            color: {MUTED};
            flex: 1 1 auto;
            min-width: 0;
        }}
        .kpi-row-right {{
            text-align: right;
            flex: 0 0 auto;
        }}
        .kpi-row-value {{
            font-family: 'Source Serif 4', Georgia, serif;
            font-size: 1.35rem;
            font-weight: 700;
            color: {NAVY};
            white-space: nowrap;
            line-height: 1.1;
        }}
        .kpi-row-hint {{
            font-size: 0.72rem;
            color: {MUTED};
            margin-top: 0.1rem;
            white-space: nowrap;
        }}

        /* —— Paneles KPI por fuente (inicio) —— */
        .kpi-fuentes {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
            margin: 0.35rem 0 1.1rem 0;
        }}
        @media (max-width: 900px) {{
            .kpi-fuentes {{ grid-template-columns: 1fr; }}
        }}
        .kpi-fuente {{
            background: {SURFACE};
            border: 1px solid {LINE};
            border-radius: 10px;
            padding: 0.85rem 1rem 0.95rem;
            border-left: 4px solid {ACCENT};
        }}
        .kpi-fuente.fuente-hab {{
            border-left-color: {SUCCESS};
        }}
        .kpi-fuente-head {{
            margin-bottom: 0.65rem;
            padding-bottom: 0.55rem;
            border-bottom: 1px solid {LINE};
        }}
        .kpi-fuente-tag {{
            font-size: 0.68rem;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: {ACCENT};
            margin-bottom: 0.2rem;
        }}
        .kpi-fuente.fuente-hab .kpi-fuente-tag {{
            color: {SUCCESS};
        }}
        .kpi-fuente-title {{
            font-family: 'Source Serif 4', Georgia, serif;
            font-size: 1.15rem;
            font-weight: 700;
            color: {NAVY};
            margin: 0 0 0.25rem 0;
            line-height: 1.2;
        }}
        .kpi-fuente-corte {{
            font-size: 0.78rem;
            color: {MUTED};
            line-height: 1.35;
        }}
        .kpi-fuente-corte strong {{
            color: {NAVY};
            font-weight: 600;
        }}
        .kpi-fuente .kpi-strip {{
            margin: 0.15rem 0 0 0;
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }}
        .kpi-fuente .kpi-strip.kpi-strip-4 {{
            grid-template-columns: repeat(4, minmax(0, 1fr));
        }}
        @media (max-width: 700px) {{
            .kpi-fuente .kpi-strip.kpi-strip-4 {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}
        }}
        .kpi-fuente .kpi-card {{
            padding: 0.65rem 0.75rem 0.55rem;
        }}
        .kpi-fuente .kpi-value {{
            font-size: 1.35rem;
        }}

        .bi-section {{
            margin: 1.25rem 0 0.65rem 0;
            padding-bottom: 0.4rem;
            border-bottom: 1px solid {LINE};
        }}
        .bi-section h2 {{
            font-family: 'Source Serif 4', Georgia, serif;
            font-size: 1.25rem;
            font-weight: 700;
            color: {NAVY};
            margin: 0;
        }}
        .bi-section p {{
            margin: 0.25rem 0 0 0;
            color: {MUTED};
            font-size: 0.9rem;
            font-weight: 500;
        }}

        [data-testid="stMain"] .stCaption,
        [data-testid="stMain"] [data-testid="stCaptionContainer"],
        [data-testid="stMain"] [data-testid="stCaptionContainer"] p {{
            color: {MUTED} !important;
            opacity: 1 !important;
            font-weight: 500 !important;
        }}
        [data-testid="stMain"] label,
        [data-testid="stMain"] [data-testid="stWidgetLabel"] p {{
            color: {INK} !important;
            font-weight: 600 !important;
        }}

        /* —— Pestañas = botones de sección —— */
        div[data-testid="stMain"] div[data-baseweb="tab-list"],
        div[data-testid="stMain"] .stTabs [data-baseweb="tab-list"],
        div[data-testid="stTabs"] [data-baseweb="tab-list"],
        .stTabs [data-baseweb="tab-list"] {{
            display: flex !important;
            flex-wrap: wrap !important;
            gap: 0.75rem !important;
            background: transparent !important;
            border: none !important;
            border-bottom: none !important;
            padding: 0.25rem 0 0.95rem 0 !important;
            margin-bottom: 0.4rem !important;
        }}
        div[data-testid="stMain"] .stTabs [data-baseweb="tab"],
        div[data-testid="stTabs"] [data-baseweb="tab"],
        .stTabs [data-baseweb="tab"],
        button[data-baseweb="tab"],
        [role="tablist"] [role="tab"] {{
            flex: 1 1 auto !important;
            height: auto !important;
            min-height: 2.85rem !important;
            margin: 0 !important;
            padding: 0.7rem 1.15rem !important;
            background: #FFFFFF !important;
            color: {NAVY} !important;
            font-weight: 700 !important;
            font-size: 0.92rem !important;
            border: 1.5px solid #CBD5E1 !important;
            border-radius: 18px !important;
            overflow: hidden !important;
            box-shadow: 0 1px 3px rgba(12, 35, 64, 0.07) !important;
            opacity: 1 !important;
            white-space: normal !important;
            line-height: 1.25 !important;
            transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease,
                box-shadow 0.15s ease !important;
        }}
        div[data-testid="stMain"] .stTabs [data-baseweb="tab"]:hover,
        .stTabs [data-baseweb="tab"]:hover,
        button[data-baseweb="tab"]:hover,
        [role="tablist"] [role="tab"]:hover {{
            border-color: {STEEL} !important;
            background: #F1F5F9 !important;
            box-shadow: 0 2px 8px rgba(12, 35, 64, 0.12) !important;
        }}
        div[data-testid="stMain"] .stTabs [data-baseweb="tab"] p,
        div[data-testid="stMain"] .stTabs [data-baseweb="tab"] span,
        div[data-testid="stMain"] .stTabs [data-baseweb="tab"] div,
        .stTabs [data-baseweb="tab"] p,
        .stTabs [data-baseweb="tab"] span,
        .stTabs [data-baseweb="tab"] div,
        button[data-baseweb="tab"] p,
        button[data-baseweb="tab"] span,
        [role="tablist"] [role="tab"] p,
        [role="tablist"] [role="tab"] span {{
            color: inherit !important;
            font-weight: 700 !important;
            opacity: 1 !important;
        }}
        div[data-testid="stMain"] .stTabs [aria-selected="true"],
        .stTabs [aria-selected="true"],
        button[data-baseweb="tab"][aria-selected="true"],
        [role="tablist"] [role="tab"][aria-selected="true"] {{
            background: {NAVY} !important;
            color: #FFFFFF !important;
            border-color: {NAVY} !important;
            border-radius: 18px !important;
            box-shadow: 0 4px 12px rgba(12, 35, 64, 0.24) !important;
            position: relative;
            z-index: 2;
            margin-bottom: 0 !important;
            padding-bottom: 0.7rem !important;
            border-top: 1.5px solid {NAVY} !important;
        }}
        div[data-testid="stMain"] .stTabs [aria-selected="true"] p,
        div[data-testid="stMain"] .stTabs [aria-selected="true"] span,
        div[data-testid="stMain"] .stTabs [aria-selected="true"] div,
        .stTabs [aria-selected="true"] p,
        .stTabs [aria-selected="true"] span,
        .stTabs [aria-selected="true"] div,
        button[data-baseweb="tab"][aria-selected="true"] p,
        button[data-baseweb="tab"][aria-selected="true"] span,
        [role="tablist"] [role="tab"][aria-selected="true"] p,
        [role="tablist"] [role="tab"][aria-selected="true"] span {{
            color: #FFFFFF !important;
        }}
        div[data-testid="stMain"] .stTabs [data-baseweb="tab-highlight"],
        div[data-testid="stMain"] .stTabs [data-baseweb="tab-border"],
        .stTabs [data-baseweb="tab-highlight"],
        .stTabs [data-baseweb="tab-border"] {{
            display: none !important;
            height: 0 !important;
            visibility: hidden !important;
        }}
        div[data-testid="stMain"] .stTabs [data-baseweb="tab-panel"],
        div[data-testid="stMain"] .stTabs > div > div[data-baseweb="tab-panel"],
        .stTabs [data-baseweb="tab-panel"] {{
            background: #FFFFFF !important;
            border: 1px solid {LINE} !important;
            border-radius: 12px !important;
            padding: 1rem 1.1rem 1.2rem 1.1rem !important;
            margin-top: 0.15rem !important;
            box-shadow: 0 1px 3px rgba(12, 35, 64, 0.05) !important;
        }}
        /* —— Fin pestañas —— */

        /* Navegación radio → pastillas redondeadas */
        div[data-testid="stMain"] div[role="radiogroup"] {{
            display: flex !important;
            flex-wrap: wrap !important;
            gap: 0.65rem !important;
        }}
        div[data-testid="stMain"] div[role="radiogroup"] label {{
            background: #FFFFFF !important;
            border: 1.5px solid #CBD5E1 !important;
            border-radius: 18px !important;
            padding: 0.55rem 1.05rem !important;
            margin: 0 !important;
            font-weight: 700 !important;
            color: {NAVY} !important;
            box-shadow: 0 1px 3px rgba(12, 35, 64, 0.07) !important;
        }}
        div[data-testid="stMain"] div[role="radiogroup"] label:has(input:checked) {{
            background: {NAVY} !important;
            color: #FFFFFF !important;
            border-color: {NAVY} !important;
            box-shadow: 0 4px 12px rgba(12, 35, 64, 0.24) !important;
        }}
        div[data-testid="stMain"] div[role="radiogroup"] label:has(input:checked) p,
        div[data-testid="stMain"] div[role="radiogroup"] label:has(input:checked) span {{
            color: #FFFFFF !important;
        }}
        div[data-testid="stMain"] div[role="radiogroup"] label > div:first-child {{
            display: none !important;
        }}
        /* Botones pastilla (selector dimensional) */
        div[data-testid="stMain"] div[class*="st-key-ad_pill_"] button {{
            border-radius: 18px !important;
            min-height: 2.85rem !important;
            font-weight: 700 !important;
        }}


        /* Métricas área principal */
        [data-testid="stMain"] div[data-testid="stMetric"] {{
            background: {SURFACE};
            border: 1px solid {LINE};
            border-radius: 8px;
            padding: 0.75rem 0.9rem;
            border-top: 3px solid {STEEL};
        }}
        [data-testid="stMain"] div[data-testid="stMetricValue"],
        [data-testid="stMain"] div[data-testid="stMetricValue"] * {{
            font-family: 'Source Serif 4', Georgia, serif;
            font-size: 1.45rem;
            color: {NAVY} !important;
            opacity: 1 !important;
        }}
        [data-testid="stMain"] div[data-testid="stMetricLabel"],
        [data-testid="stMain"] div[data-testid="stMetricLabel"] * {{
            color: {MUTED} !important;
            font-weight: 700 !important;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            font-size: 0.72rem;
            opacity: 1 !important;
        }}

        .stExpander {{
            border: 1px solid {LINE};
            border-radius: 8px;
            background: {SURFACE};
        }}
        [data-testid="stDataFrame"] {{
            border: 1px solid {LINE};
            border-radius: 8px;
            overflow: hidden;
        }}

        #MainMenu {{ visibility: hidden; }}
        footer {{ visibility: hidden; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_flag_ribbon() -> None:
    stars = "".join('<span class="ve-star" aria-hidden="true"></span>' for _ in range(8))
    st.markdown(
        f"""
        <div class="ve-ribbon" role="img" aria-label="Cinta con colores de la bandera de Venezuela">
          <div class="ve-stripe ve-stripe-y"></div>
          <div class="ve-stripe ve-stripe-b">{stars}</div>
          <div class="ve-stripe ve-stripe-r"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_hero(
    title: str,
    subtitle: str,
    kicker: str = "Comisión Presidencial · Habitabilidad",
) -> None:
    render_flag_ribbon()
    st.markdown(
        f"""
        <div class="bi-hero">
          <div class="bi-hero-kicker">{kicker}</div>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section(title: str, subtitle: str | None = None) -> None:
    sub = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div class="bi-section">
          <h2>{title}</h2>
          {sub}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_tabs(
    options: list[tuple[str, str]],
    *,
    state_key: str,
    heading: str = "Secciones",
) -> str:
    """
    Pestañas/secciones con borde y selección clara.
    options: [(id, etiqueta), ...]
    """
    valid = {k for k, _ in options}
    if state_key not in st.session_state or st.session_state[state_key] not in valid:
        st.session_state[state_key] = options[0][0]

    # CSS scoped por prefijo de key de Streamlit (st-key-<state_key>_…)
    prefix = state_key
    selectors = ",\n        ".join(
        f'div[class*="st-key-{prefix}_{k}"] button' for k, _ in options
    )
    sel_sec = ",\n        ".join(
        f'div[class*="st-key-{prefix}_{k}"] button[kind="secondary"]' for k, _ in options
    )
    sel_pri = ",\n        ".join(
        f'div[class*="st-key-{prefix}_{k}"] button[kind="primary"]' for k, _ in options
    )
    sel_sec_txt = ",\n        ".join(
        f'div[class*="st-key-{prefix}_{k}"] button[kind="secondary"] p,\n'
        f'        div[class*="st-key-{prefix}_{k}"] button[kind="secondary"] span'
        for k, _ in options
    )
    sel_pri_txt = ",\n        ".join(
        f'div[class*="st-key-{prefix}_{k}"] button[kind="primary"] p,\n'
        f'        div[class*="st-key-{prefix}_{k}"] button[kind="primary"] span'
        for k, _ in options
    )

    st.markdown(
        f"""
        <style>
        {selectors} {{
          min-height: 3rem !important;
          border-radius: 8px !important;
          font-weight: 700 !important;
          font-size: 0.92rem !important;
          border-width: 2px !important;
        }}
        {sel_sec} {{
          background: #F1F5F9 !important;
          border-color: #64748B !important;
          color: #0C2340 !important;
        }}
        {sel_sec_txt} {{
          color: #0C2340 !important;
          font-weight: 700 !important;
        }}
        {sel_pri} {{
          background: #1F4E79 !important;
          border-color: #0C2340 !important;
          color: #FFFFFF !important;
          box-shadow: inset 0 4px 0 0 #FCD116 !important;
        }}
        {sel_pri_txt} {{
          color: #FFFFFF !important;
          font-weight: 700 !important;
        }}
        </style>
        <div style="
          background:#E2E8F0;border:2px solid #94A3B8;border-bottom:3px solid #1F4E79;
          border-radius:10px;padding:0.55rem 0.55rem 0.2rem 0.55rem;margin:0.35rem 0 0.35rem 0;
        ">
          <div style="color:#334155;font-size:0.7rem;font-weight:700;letter-spacing:0.06em;
                      text-transform:uppercase;margin:0 0 0.4rem 0.2rem;">{heading}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(len(options))
    for col, (key, label) in zip(cols, options):
        with col:
            active = st.session_state[state_key] == key
            if st.button(
                label,
                key=f"{prefix}_{key}",
                use_container_width=True,
                type="primary" if active else "secondary",
            ):
                st.session_state[state_key] = key
                st.rerun()
    return st.session_state[state_key]


def render_kpi_strip(items: list[dict]) -> None:
    """items: [{label, value, tone?, hint?}]. Columnas = nº de ítems (máx. 5)."""
    cards = []
    for it in items:
        tone = it.get("tone", "")
        cls = f"kpi-card tone-{tone}" if tone else "kpi-card"
        hint = f'<div class="kpi-hint">{it["hint"]}</div>' if it.get("hint") else ""
        cards.append(
            f'<div class="{cls}">'
            f'<div class="kpi-label">{it["label"]}</div>'
            f'<div class="kpi-value">{it["value"]}</div>'
            f"{hint}</div>"
        )
    n = max(1, min(len(items), 6))
    st.markdown(
        f'<div class="kpi-strip" style="--kpi-cols:{n}">{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )


def render_kpi_rows(items: list[dict]) -> None:
    """KPI en filas horizontales (legibles en columnas estrechas)."""
    rows = []
    for it in items:
        tone = it.get("tone", "")
        cls = f"kpi-row tone-{tone}" if tone else "kpi-row"
        hint = (
            f'<div class="kpi-row-hint">{it["hint"]}</div>'
            if it.get("hint")
            else ""
        )
        rows.append(
            f'<div class="{cls}">'
            f'<div class="kpi-row-label">{it["label"]}</div>'
            f'<div class="kpi-row-right">'
            f'<div class="kpi-row-value">{it["value"]}</div>'
            f"{hint}</div></div>"
        )
    st.markdown(
        f'<div class="kpi-rows">{"".join(rows)}</div>',
        unsafe_allow_html=True,
    )


def _nav_top_entries() -> list[tuple[str, str, str, str]]:
    """(key_suffix, label, target_nav_item, help)."""
    from nav_schema import HOME_ID, NAV_SECTIONS

    out: list[tuple[str, str, str, str]] = [
        ("home", "Inicio", HOME_ID, "Panorama nacional"),
    ]
    for sec in NAV_SECTIONS:
        out.append((f"sec_{sec.id}", sec.label, sec.items[0].id, sec.blurb))
    return out


def _render_nav_grid(
    active_item: str,
    *,
    key_prefix: str,
    short_labels: bool = False,
) -> None:
    """Botones de sección en rejilla de 2 columnas."""
    from nav_schema import HOME_ID, resolve_nav

    sec_id, _ = resolve_nav(active_item)
    entries = _nav_top_entries()

    short = {
        "home": "Inicio",
        "sec_analisis_dimensional": "Análisis dim.",
        "sec_explorar": "Explorar",
        "sec_depuracion": "Depuración",
        "sec_carga": "Cargar",
    }

    # Sub-ítems del análisis dimensional en sidebar: ya se listan debajo;
    # con 5 capas el grid superior sigue siendo de secciones.

    for i in range(0, len(entries), 2):
        cols = st.columns(2, gap="small")
        chunk = entries[i : i + 2]
        for col, (suffix, label, target, help_txt) in zip(cols, chunk):
            with col:
                if target == HOME_ID:
                    on = active_item == HOME_ID
                else:
                    # sección activa si el ítem pertenece a esa sección
                    from nav_schema import NAV_SECTIONS

                    this_sec = next(
                        (s for s in NAV_SECTIONS if s.items and s.items[0].id == target),
                        None,
                    )
                    on = bool(
                        this_sec
                        and active_item != HOME_ID
                        and sec_id == this_sec.id
                    )
                shown = short.get(suffix, label) if short_labels else label
                if st.button(
                    shown,
                    key=f"{key_prefix}_{suffix}",
                    use_container_width=True,
                    type="primary" if on else "secondary",
                    help=help_txt,
                ):
                    if on and target != HOME_ID and active_item != HOME_ID:
                        # ya en la sección: conservar subpestaña
                        st.session_state["nav_item"] = active_item
                    else:
                        st.session_state["nav_item"] = target
                    st.rerun()


def render_sidebar_nav(active_item: str) -> str:
    """
    Menú izquierdo (sidebar): rejilla 2×2 + subpestañas de la sección activa.
    Devuelve el id de ítem activo (o 'home').
    """
    from nav_schema import HOME_ID, NAV_SECTIONS, resolve_nav

    with st.sidebar:
        st.markdown("### Menú")
        st.caption("Elija una sección. Las subpestañas salen abajo o en pantalla.")
        _render_nav_grid(active_item, key_prefix="nav", short_labels=True)

        sec_id, _ = resolve_nav(active_item)
        for sec in NAV_SECTIONS:
            on = sec_id == sec.id and active_item != HOME_ID
            if on and len(sec.items) > 1:
                st.caption(f"Pestañas · {sec.label}")
                for it in sec.items:
                    item_on = active_item == it.id
                    if st.button(
                        it.label,
                        key=f"nav_item_{it.id}",
                        use_container_width=True,
                        type="primary" if item_on else "secondary",
                        help=it.blurb,
                    ):
                        st.session_state["nav_item"] = it.id
                        st.rerun()

    return st.session_state.get("nav_item", HOME_ID)


def render_main_nav_grid(active_item: str) -> None:
    """Atajo compacto 2×2 en el área principal."""
    st.markdown("##### Navegación")
    st.caption("Atajo · el mismo menú está a la izquierda.")
    _render_nav_grid(active_item, key_prefix="main_nav", short_labels=False)


def render_home_index(
    summary: dict | None = None,
    hab=None,
) -> None:
    """Índice de secciones del BI Habitable."""
    from nav_schema import NAV_SECTIONS

    _ = summary, hab  # API compatible; el panorama vive en page_inicio

    render_section(
        "Índice del tablero",
        "Elige una sección en el menú izquierdo. Dentro de cada sección "
        "verás sus pestañas en la pantalla principal.",
    )

    cards = []
    for sec in NAV_SECTIONS:
        lis = "".join(f"<li><strong>{it.label}</strong> — {it.blurb}</li>" for it in sec.items)
        cards.append(
            f'<div class="nav-index-card">'
            f"<h3>{sec.label}</h3>"
            f"<p>{sec.blurb}</p>"
            f"<ul>{lis}</ul>"
            f"</div>"
        )
    st.markdown(f'<div class="nav-index">{"".join(cards)}</div>', unsafe_allow_html=True)

    st.caption("Atajo: entra directo a una sección.")
    cols = st.columns(2)
    for i, sec in enumerate(NAV_SECTIONS):
        with cols[i % 2]:
            if st.button(
                f"Abrir · {sec.label}",
                key=f"home_go_sec_{sec.id}",
                use_container_width=True,
            ):
                st.session_state["nav_item"] = sec.items[0].id
                st.rerun()


def render_page_crumb(section_label: str, item_label: str) -> None:
    st.markdown(
        f'<div class="nav-crumb">{section_label} · {item_label}</div>',
        unsafe_allow_html=True,
    )


def render_section_subtabs(section) -> str:
    """Pestañas internas de una sección (en el área principal)."""
    options = [(it.id, it.label) for it in section.items]
    return render_section_tabs(
        options,
        state_key="nav_item",
        heading=f"Pestañas · {section.label}",
    )
