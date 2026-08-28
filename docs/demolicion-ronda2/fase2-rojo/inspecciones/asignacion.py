"""Lógica de asignación inspector / revisor por caso."""
from __future__ import annotations

from django.contrib.auth.models import User
from django.db.models import Count, Q, QuerySet

from inspecciones.models import CasoRojo
from inspecciones.workflow import (
    GRUPO_COORDINADOR,
    GRUPO_INSPECTOR,
    GRUPO_REVISOR,
)


def usuarios_por_rol() -> dict[str, QuerySet]:
    """Usuarios activos agrupados por rol operativo."""
    base = User.objects.filter(is_active=True).order_by("first_name", "last_name", "username")
    return {
        "inspectores": base.filter(groups__name=GRUPO_INSPECTOR).distinct(),
        "revisores": base.filter(groups__name=GRUPO_REVISOR).distinct(),
        "coordinadores": base.filter(
            Q(groups__name=GRUPO_COORDINADOR) | Q(is_superuser=True)
        ).distinct(),
    }


def resumen_usuarios() -> list[dict]:
    """Filas del tablero: usuario, roles y conteos de casos."""
    roles_map: dict[int, list[str]] = {}
    for rol, nombre in (
        ("inspectores", "Inspector"),
        ("revisores", "Revisor"),
        ("coordinadores", "Coordinador"),
    ):
        for user in usuarios_por_rol()[rol]:
            roles_map.setdefault(user.pk, []).append(nombre)

    user_ids = list(roles_map.keys())
    if not user_ids:
        return []

    stats = {
        row["pk"]: row
        for row in User.objects.filter(pk__in=user_ids)
        .annotate(
            n_inspector=Count("casos_inspeccion", distinct=True),
            n_revisor=Count("casos_revision", distinct=True),
        )
        .values("pk", "username", "first_name", "last_name", "n_inspector", "n_revisor")
    }

    filas = []
    for uid in user_ids:
        row = stats[uid]
        nombre = (f"{row['first_name']} {row['last_name']}".strip()) or row["username"]
        filas.append(
            {
                "id": uid,
                "username": row["username"],
                "nombre": nombre,
                "roles": roles_map[uid],
                "n_inspector": row["n_inspector"],
                "n_revisor": row["n_revisor"],
                "total": row["n_inspector"] + row["n_revisor"],
            }
        )
    filas.sort(key=lambda r: (-r["total"], r["nombre"].lower()))
    return filas


def kpis_asignacion() -> dict[str, int]:
    qs = CasoRojo.objects.all()
    total = qs.count()
    sin_inspector = qs.filter(inspector_asignado__isnull=True).count()
    sin_revisor = qs.filter(revisor_asignado__isnull=True).count()
    sin_ambos = qs.filter(
        inspector_asignado__isnull=True, revisor_asignado__isnull=True
    ).count()
    con_ambos = qs.filter(
        inspector_asignado__isnull=False, revisor_asignado__isnull=False
    ).count()
    return {
        "total": total,
        "sin_inspector": sin_inspector,
        "sin_revisor": sin_revisor,
        "sin_ambos": sin_ambos,
        "con_ambos": con_ambos,
    }


def filtrar_casos(request) -> QuerySet:
    qs = CasoRojo.objects.select_related("inspector_asignado", "revisor_asignado")
    estado = request.GET.get("estado", "").strip()
    banda = request.GET.get("banda", "").strip()
    sin_inspector = request.GET.get("sin_inspector")
    sin_revisor = request.GET.get("sin_revisor")
    usuario_id = request.GET.get("usuario")
    rol_usuario = request.GET.get("rol", "inspector")
    q = request.GET.get("q", "").strip()

    if estado:
        qs = qs.filter(estado_2da=estado)
    if banda:
        qs = qs.filter(banda=banda)
    if sin_inspector == "1":
        qs = qs.filter(inspector_asignado__isnull=True)
    if sin_revisor == "1":
        qs = qs.filter(revisor_asignado__isnull=True)
    if usuario_id:
        try:
            uid = int(usuario_id)
            if rol_usuario == "revisor":
                qs = qs.filter(revisor_asignado_id=uid)
            else:
                qs = qs.filter(inspector_asignado_id=uid)
        except ValueError:
            pass
    if q:
        if q.isdigit():
            qs = qs.filter(hab_id=int(q))
        else:
            qs = qs.filter(
                Q(nombre_hab__icontains=q)
                | Q(nombre_conf__icontains=q)
                | Q(direccion_hab__icontains=q)
                | Q(muni_parr__icontains=q)
            )
    return qs.order_by("-score", "hab_id")


def aplicar_asignacion(
    casos: QuerySet,
    *,
    inspector_id: int | None = None,
    revisor_id: int | None = None,
    limpiar_inspector: bool = False,
    limpiar_revisor: bool = False,
) -> int:
    """Actualiza asignaciones en lote. Devuelve cantidad de casos tocados."""
    update_fields = ["updated_at"]
    values: dict = {}

    if limpiar_inspector:
        values["inspector_asignado_id"] = None
        update_fields.append("inspector_asignado_id")
    elif inspector_id:
        values["inspector_asignado_id"] = inspector_id
        update_fields.append("inspector_asignado_id")

    if limpiar_revisor:
        values["revisor_asignado_id"] = None
        update_fields.append("revisor_asignado_id")
    elif revisor_id:
        values["revisor_asignado_id"] = revisor_id
        update_fields.append("revisor_asignado_id")

    if len(update_fields) == 1:
        return 0

    return casos.update(**values)
