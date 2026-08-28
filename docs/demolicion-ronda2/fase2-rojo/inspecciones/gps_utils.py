"""Utilidades para extraer lat/lng desde campos GPS texto o columnas numéricas."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from inspecciones.models import CasoRojo

# Bounding box aproximado Venezuela continental + La Guaira
_LAT_MIN, _LAT_MAX = 0.5, 13.5
_LNG_MIN, _LNG_MAX = -74.5, -59.0


def parse_gps(text: str | None) -> tuple[float, float] | None:
    """Parsea 'lat, lng' desde texto libre."""
    if not text:
        return None
    cleaned = text.strip().replace(";", ",")
    parts = [p.strip() for p in cleaned.split(",") if p.strip()]
    if len(parts) < 2:
        return None
    try:
        lat = float(parts[0])
        lng = float(parts[1])
    except ValueError:
        return None
    if _LAT_MIN <= lat <= _LAT_MAX and _LNG_MIN <= lng <= _LNG_MAX:
        return lat, lng
    return None


def coordenadas_caso(caso: CasoRojo) -> tuple[float, float] | None:
    """Obtiene coordenadas del caso: columnas lat/lng si existen, si no gps_v2/gps_hab."""
    lat_val = getattr(caso, "lat", None)
    lng_val = getattr(caso, "lng", None)
    if lat_val is not None and lng_val is not None:
        try:
            return float(lat_val), float(lng_val)
        except (TypeError, ValueError):
            pass
    for gps_text in (getattr(caso, "gps_v2", ""), getattr(caso, "gps_hab", "")):
        parsed = parse_gps(gps_text)
        if parsed:
            return parsed
    return None


def caso_tiene_gps(caso: CasoRojo) -> bool:
    return coordenadas_caso(caso) is not None


def filtrar_casos_con_gps(queryset):
    """Evalúa en Python (compatible con o sin columnas lat/lng en BD)."""
    if hasattr(queryset, "iterator"):
        iterable = queryset.iterator()
    else:
        iterable = queryset
    return [c for c in iterable if caso_tiene_gps(c)]
