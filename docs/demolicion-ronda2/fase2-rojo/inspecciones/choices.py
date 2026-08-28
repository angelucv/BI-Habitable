"""Listas desplegables — escala D1–D4 por gravedad ascendente.

D1 = complementos requeridos (cierre provisional explícito).
D2 = reparar (+ M1–M4). D3 = demoler. D4 = escombros (mayor gravedad).
"""
from django.db import models


class SiNoParcial(models.TextChoices):
    SI = "Sí", "Sí"
    NO = "No", "No"
    PARCIAL = "Parcial / corregir", "Parcial / corregir"
    PENDIENTE = "Pendiente", "Pendiente"


class SiNoInsuf(models.TextChoices):
    SI = "Sí", "Sí"
    NO = "No", "No"
    INSUF = "Insuficiente evidencia", "Insuficiente evidencia"
    PENDIENTE = "Pendiente", "Pendiente"


class Estado2daRonda(models.TextChoices):
    PENDIENTE = "Pendiente verificación", "Pendiente verificación"
    EN_VISITA = "En visita", "En visita"
    BORRADOR = "Borrador", "Borrador"
    REVISADO = "Revisado", "Revisado"
    APROBADO = "Aprobado", "Aprobado"
    PUBLICADO = "Publicado", "Publicado"


class ComplementoD(models.TextChoices):
    """Tipos de complemento obligatorios cuando decision_D = D1."""

    GEO = "GEO", "GEO — Estudio geotécnico"
    ENS = "ENS", "ENS — Ensayos de materiales (testigos / esclerómetro)"
    MOD = "MOD", "MOD — Modelo o análisis estructural"
    MON = "MON", "MON — Monitoreo instrumentado (inclinómetro / fisurómetro)"
    INV = "INV", "INV — Investigación de elementos ocultos"
    REI = "REI", "REI — Reinspección en fecha programada"
    ALE = "ALE", "ALE — Evaluación de riesgo a edificios aledaños"
    OTR = "OTR", "OTR — Otro complemento (detallar abajo)"


class DecisionD(models.TextChoices):
    """Decisión de control — gravedad ascendente D1 (menor) → D4 (mayor)."""

    D1 = (
        "D1 — Complementos requeridos",
        "D1 — Complementos requeridos",
    )
    D2 = "D2 — Reparar / reconstruir", "D2 — Reparar / reconstruir"
    D3 = "D3 — Demoler", "D3 — Demoler"
    D4 = "D4 — Escombros / ya colapsado", "D4 — Escombros / ya colapsado"
    PENDIENTE = "Pendiente", "Pendiente"

    @classmethod
    def requiere_complementos(cls, valor: str) -> bool:
        return valor == cls.D1

    @classmethod
    def requiere_magnitud(cls, valor: str) -> bool:
        return valor == cls.D2


# Remapeos históricos (migraciones de datos)
DECISION_D_FROM_V2: dict[str, str] = {
    "D1 — Inhabitabilidad + monitoreo": DecisionD.D1,
    "D2 — Estudios complementarios": DecisionD.D1,
    "D3 — Reparar / reconstruir": DecisionD.D2,
    "D4 — Demoler": DecisionD.D3,
    "D5 — Escombros / ya colapsado": DecisionD.D4,
}

DECISION_D_FROM_V1: dict[str, str] = {
    "D1 — Demoler": DecisionD.D3,
    "D2 — Reparar / reconstruir": DecisionD.D2,
    "D3 — Estudios complementarios": DecisionD.D1,
    "D4 — Escombros / ya colapsado": DecisionD.D4,
    "D5 — Inhabitabilidad + monitoreo": DecisionD.D1,
}


class MagnitudM(models.TextChoices):
    NA = "N/A (no es D2)", "N/A (no es D2)"
    M1 = "M1 — Reparación local (menor intervención)", "M1 — Reparación local (menor intervención)"
    M2 = "M2 — Reparación importante", "M2 — Reparación importante"
    M3 = "M3 — Reconstrucción parcial", "M3 — Reconstrucción parcial"
    M4 = "M4 — Reconstrucción / refuerzo mayor (mayor intervención)", "M4 — Reconstrucción / refuerzo mayor (mayor intervención)"
    PENDIENTE = "Pendiente", "Pendiente"


MAGNITUD_M_LEGACY_MAP: dict[str, str] = {
    "N/A (no es D2)": MagnitudM.NA,
    "N/A (no es D3)": MagnitudM.NA,
    "M1 — Reparación pequeña / local": MagnitudM.M1,
    "M1 — Reparación local (menor intervención)": MagnitudM.M1,
}


COMPLEMENTO_LABELS: dict[str, str] = {c.value: c.label for c in ComplementoD}


def parse_complementos(raw: str) -> list[str]:
    return [p.strip().upper() for p in (raw or "").split(",") if p.strip()]


def complementos_display(raw: str) -> str:
    codes = parse_complementos(raw)
    if not codes:
        return ""
    parts = []
    for code in codes:
        parts.append(COMPLEMENTO_LABELS.get(code, code))
    return "; ".join(parts)


class PrioridadOperativa(models.TextChoices):
    INMEDIATA = "Inmediata", "Inmediata"
    ALTA = "Alta", "Alta"
    PROGRAMABLE = "Programable", "Programable"
    PENDIENTE = "Pendiente", "Pendiente"


class NivelABC(models.TextChoices):
    A = "A", "A"
    B = "B", "B"
    C = "C", "C"
    NO_OBS = "No observable", "No observable"
    PENDIENTE = "Pendiente", "Pendiente"


class SistemaEstructural(models.TextChoices):
    PORTICOS = "Pórticos concreto armado", "Pórticos concreto armado"
    MUROS = "Muros de concreto", "Muros de concreto"
    MIXTO = "Mixto", "Mixto"
    ACERO = "Acero", "Acero"
    MAMPOSTERIA = "Mampostería", "Mampostería"
    OTRO = "Otro", "Otro"
    PENDIENTE = "Pendiente", "Pendiente"


class Ocupacion(models.TextChoices):
    DESALOJADO = "Desalojado", "Desalojado"
    PARCIAL = "Ocupación parcial", "Ocupación parcial"
    IRREGULAR = "Habitado irregularmente", "Habitado irregularmente"
    ESCOMBROS = "Escombros", "Escombros"
    PENDIENTE = "Pendiente", "Pendiente"


class PctColumnas(models.TextChoices):
    NO_OBS = "No observable", "No observable"
    LT10 = "<10%", "<10%"
    R10_30 = "10–30%", "10–30%"
    GT30 = ">30%", ">30%"
    GT50 = ">50%", ">50%"
    PENDIENTE = "Pendiente", "Pendiente"


class Inclinacion(models.TextChoices):
    NO = "No", "No"
    SI_CUAL = "Sí — cualitativa", "Sí — cualitativa"
    SI_DELTA = "Sí — con medición Δ", "Sí — con medición Δ"
    NO_OBS = "No observable", "No observable"
    PENDIENTE = "Pendiente", "Pendiente"


class PeligroAledanos(models.TextChoices):
    SI = "Sí", "Sí"
    NO = "No", "No"
    NO_OBS = "No observable", "No observable"
    PENDIENTE = "Pendiente", "Pendiente"
