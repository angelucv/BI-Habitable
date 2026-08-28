"""Vistas del tablero de asignación de casos (solo coordinadores)."""
from __future__ import annotations

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from inspecciones.asignacion import (
    aplicar_asignacion,
    filtrar_casos,
    kpis_asignacion,
    resumen_usuarios,
    usuarios_por_rol,
)
from inspecciones.models import CasoRojo
from inspecciones.workflow import es_coordinador


def _requiere_coordinador(request):
    if not es_coordinador(request.user):
        return HttpResponseForbidden(
            "Solo coordinadores pueden gestionar asignaciones de casos."
        )
    return None


@staff_member_required
@require_http_methods(["GET", "POST"])
def tablero_asignacion(request):
    denied = _requiere_coordinador(request)
    if denied:
        return denied

    if request.method == "POST":
        return _procesar_asignacion(request)

    qs = filtrar_casos(request)
    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get("page"))

    estados = (
        CasoRojo.objects.exclude(estado_2da="")
        .values_list("estado_2da", flat=True)
        .distinct()
        .order_by("estado_2da")
    )
    bandas = (
        CasoRojo.objects.exclude(banda="")
        .values_list("banda", flat=True)
        .distinct()
        .order_by("banda")
    )

    usuarios = usuarios_por_rol()
    ctx = {
        "kpis": kpis_asignacion(),
        "usuarios_tabla": resumen_usuarios(),
        "inspectores": usuarios["inspectores"],
        "revisores": usuarios["revisores"],
        "coordinadores": usuarios["coordinadores"],
        "casos": page,
        "paginator": paginator,
        "estados": estados,
        "bandas": bandas,
        "filtros": request.GET,
        "total_filtrado": paginator.count,
    }
    return render(request, "inspecciones/tablero_asignacion.html", ctx)


def _procesar_asignacion(request):
    action = request.POST.get("action", "masiva")
    redirect_url = reverse("tablero_asignacion") + "?" + request.POST.get("query_string", "")

    if action == "uno":
        try:
            caso_id = int(request.POST.get("caso_id", ""))
        except ValueError:
            messages.error(request, "Caso inválido.")
            return redirect(redirect_url)
        casos = CasoRojo.objects.filter(pk=caso_id)
    else:
        ids = [int(x) for x in request.POST.getlist("caso_ids") if x.isdigit()]
        if not ids:
            messages.warning(request, "Seleccione al menos un caso.")
            return redirect(redirect_url)
        casos = CasoRojo.objects.filter(pk__in=ids)

    inspector_raw = request.POST.get("inspector_id", "")
    revisor_raw = request.POST.get("revisor_id", "")
    limpiar_inspector = inspector_raw == "__clear__"
    limpiar_revisor = revisor_raw == "__clear__"

    inspector_id = None if limpiar_inspector or not inspector_raw else int(inspector_raw)
    revisor_id = None if limpiar_revisor or not revisor_raw else int(revisor_raw)

    if not any([inspector_id, revisor_id, limpiar_inspector, limpiar_revisor]):
        messages.warning(request, "Indique inspector y/o revisor a asignar.")
        return redirect(redirect_url)

    n = aplicar_asignacion(
        casos,
        inspector_id=inspector_id,
        revisor_id=revisor_id,
        limpiar_inspector=limpiar_inspector,
        limpiar_revisor=limpiar_revisor,
    )
    messages.success(request, f"Asignación aplicada a {n} caso(s).")
    return redirect(redirect_url)
