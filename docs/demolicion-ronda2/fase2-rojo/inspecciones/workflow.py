"""Flujo de revisión Fase II — transiciones de estado y validaciones."""
from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError

from inspecciones import choices as ch

GRUPO_INSPECTOR = "cpeh_inspector"
GRUPO_REVISOR = "cpeh_revisor"
GRUPO_COORDINADOR = "cpeh_coordinador"

TRANSICIONES: dict[str, set[str]] = {
    ch.Estado2daRonda.PENDIENTE: {ch.Estado2daRonda.EN_VISITA},
    ch.Estado2daRonda.EN_VISITA: {ch.Estado2daRonda.BORRADOR, ch.Estado2daRonda.PENDIENTE},
    ch.Estado2daRonda.BORRADOR: {ch.Estado2daRonda.REVISADO, ch.Estado2daRonda.EN_VISITA},
    ch.Estado2daRonda.REVISADO: {ch.Estado2daRonda.APROBADO, ch.Estado2daRonda.BORRADOR},
    ch.Estado2daRonda.APROBADO: {ch.Estado2daRonda.PUBLICADO, ch.Estado2daRonda.REVISADO},
    ch.Estado2daRonda.PUBLICADO: set(),
}

TRANSICIONES_POR_ROL: dict[str, set[tuple[str, str]]] = {
    GRUPO_INSPECTOR: {
        (ch.Estado2daRonda.PENDIENTE, ch.Estado2daRonda.EN_VISITA),
        (ch.Estado2daRonda.EN_VISITA, ch.Estado2daRonda.BORRADOR),
        (ch.Estado2daRonda.BORRADOR, ch.Estado2daRonda.REVISADO),
        (ch.Estado2daRonda.REVISADO, ch.Estado2daRonda.BORRADOR),
        (ch.Estado2daRonda.EN_VISITA, ch.Estado2daRonda.PENDIENTE),
        (ch.Estado2daRonda.BORRADOR, ch.Estado2daRonda.EN_VISITA),
    },
    GRUPO_REVISOR: {
        (ch.Estado2daRonda.REVISADO, ch.Estado2daRonda.APROBADO),
        (ch.Estado2daRonda.REVISADO, ch.Estado2daRonda.BORRADOR),
        (ch.Estado2daRonda.APROBADO, ch.Estado2daRonda.REVISADO),
    },
    GRUPO_COORDINADOR: set(),
}


@dataclass(frozen=True)
class FlujoRevision:
    """Descripción legible del flujo operativo."""

    pasos: tuple[str, ...] = (
        "1. Pendiente verificación — caso precargado, sin visita detallada.",
        "2. En visita — inspector en campo levantando datos (secc. 4–10).",
        "3. Borrador — informe completo pendiente de revisión técnica.",
        "4. Revisado — revisor validó contenido y dictamen.",
        "5. Aprobado — coordinación confirma decisión D/M y prioridad.",
        "6. Publicado — caso cerrado para tablero operativo y reportes.",
    )


def grupos_usuario(user: User) -> set[str]:
    if user.is_superuser:
        return {GRUPO_COORDINADOR, GRUPO_REVISOR, GRUPO_INSPECTOR}
    return set(user.groups.values_list("name", flat=True))


def es_coordinador(user: User) -> bool:
    return user.is_superuser or GRUPO_COORDINADOR in grupos_usuario(user)


def es_revisor(user: User) -> bool:
    return es_coordinador(user) or GRUPO_REVISOR in grupos_usuario(user)


def es_inspector(user: User) -> bool:
    return es_revisor(user) or GRUPO_INSPECTOR in grupos_usuario(user)


def puede_transicionar(user: User, anterior: str, nuevo: str) -> bool:
    if anterior == nuevo:
        return True
    if nuevo not in TRANSICIONES.get(anterior, set()):
        return False
    if es_coordinador(user):
        return True
    g = grupos_usuario(user)
    for nombre_grupo in g:
        permitidas = TRANSICIONES_POR_ROL.get(nombre_grupo, set())
        if (anterior, nuevo) in permitidas:
            return True
    return False


def validar_transicion_estado(user: User, anterior: str, nuevo: str) -> None:
    if anterior == nuevo:
        return
    if nuevo not in TRANSICIONES.get(anterior, set()):
        raise ValidationError(
            f"Transición no permitida: «{anterior}» → «{nuevo}». "
            f"Siguientes válidos: {', '.join(sorted(TRANSICIONES.get(anterior, set())) or ['(ninguno)'])}."
        )
    if not puede_transicionar(user, anterior, nuevo):
        raise ValidationError(
            f"Su rol no puede mover el caso de «{anterior}» a «{nuevo}». "
            "Contacte al revisor o coordinador."
        )


def validar_complementos_d(caso) -> None:
    """D1 exige complementos explícitos, plazo, medidas y detalle — cierre provisional."""
    if not ch.DecisionD.requiere_complementos(caso.decision_D):
        return

    codes = ch.parse_complementos(caso.complementos_D)
    valid = {c.value for c in ch.ComplementoD}
    invalid = [c for c in codes if c not in valid]
    if invalid:
        raise ValidationError(
            f"Códigos de complemento no válidos: {', '.join(invalid)}. "
            f"Use: {', '.join(sorted(valid))}."
        )
    if not codes:
        raise ValidationError(
            "Si la decisión es D1 (Complementos requeridos), indique al menos un código "
            "(GEO, ENS, MOD, MON, INV, REI, ALE, OTR) separados por coma."
        )
    if not caso.complemento_plazo:
        raise ValidationError(
            "D1: indique la fecha plazo / objetivo del complemento o reinspección."
        )
    if not (caso.medidas or "").strip():
        raise ValidationError(
            "D1: indique medidas inmediatas (desalojo, perímetro, prohibición de ocupación)."
        )
    detalle = (caso.complemento_detalle or "").strip()
    if len(detalle) < 15:
        raise ValidationError(
            "D1: describa qué falta, quién lo ejecuta y qué entregable cierra el complemento "
            "(mínimo 15 caracteres)."
        )
    if "OTR" in codes and len(detalle) < 40:
        raise ValidationError(
            "D1 con código OTR: amplíe el detalle del complemento (mínimo 40 caracteres)."
        )


_ESTADOS_CIERRE = (
    ch.Estado2daRonda.REVISADO,
    ch.Estado2daRonda.APROBADO,
    ch.Estado2daRonda.PUBLICADO,
)


def validar_dictamen(caso, *, cerrar: bool = False) -> None:
    """Reglas de negocio al guardar decisión."""
    exigir = cerrar or caso.estado_2da in _ESTADOS_CIERRE

    if exigir and ch.DecisionD.requiere_magnitud(caso.decision_D):
        if caso.magnitud_M in (ch.MagnitudM.PENDIENTE, ch.MagnitudM.NA, ""):
            raise ValidationError(
                "Si la decisión es D2 (Reparar / reconstruir), debe indicar magnitud M1–M4."
            )
    elif caso.decision_D and caso.decision_D != ch.DecisionD.PENDIENTE:
        if caso.magnitud_M == ch.MagnitudM.PENDIENTE:
            caso.magnitud_M = ch.MagnitudM.NA

    if exigir:
        validar_complementos_d(caso)

    if exigir:
        if caso.decision_D in ("", ch.DecisionD.PENDIENTE):
            raise ValidationError(
                f"Para cerrar el informe debe registrar decisión D1–D4."
            )
        if not (caso.resumen_ejecutivo or "").strip():
            raise ValidationError(
                "Para cerrar el informe debe completar el resumen ejecutivo (secc. 11)."
            )


def asegurar_grupos() -> dict[str, Group]:
    grupos = {}
    for nombre in (GRUPO_INSPECTOR, GRUPO_REVISOR, GRUPO_COORDINADOR):
        grupos[nombre], _ = Group.objects.get_or_create(name=nombre)
    return grupos
