"""Descarga de plantillas Excel (informe y lote)."""
from __future__ import annotations

from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404

from inspecciones.excel_plantilla import (
    generar_excel_informe,
    generar_excel_informes_multiples,
    generar_excel_lote,
    nombre_archivo_informe,
    nombre_archivo_lote,
    nombre_archivo_multinforme,
)
from inspecciones.models import CasoRojo


def _excel_response(content: bytes, filename: str) -> HttpResponse:
    resp = HttpResponse(
        content,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


@staff_member_required
def export_excel_informe(request, pk: int) -> HttpResponse:
    caso = get_object_or_404(CasoRojo, pk=pk)
    data = generar_excel_informe(caso)
    return _excel_response(data, nombre_archivo_informe(caso))


@staff_member_required
def export_excel_lote(request) -> HttpResponse:
    ids_raw = request.GET.get("ids", "")
    if not ids_raw:
        return HttpResponseBadRequest("Indique ids= separados por coma.")
    try:
        ids = [int(x.strip()) for x in ids_raw.split(",") if x.strip()]
    except ValueError:
        return HttpResponseBadRequest("IDs inválidos.")
    if not ids:
        return HttpResponseBadRequest("Sin casos.")
    if len(ids) > 500:
        return HttpResponseBadRequest("Máximo 500 casos por lote.")
    casos = list(CasoRojo.objects.filter(pk__in=ids).order_by("-score", "hab_id"))
    if not casos:
        raise Http404("No hay casos con esos IDs.")
    data = generar_excel_lote(casos)
    return _excel_response(data, nombre_archivo_lote(len(casos)))


@staff_member_required
def export_excel_informes_multiples(request) -> HttpResponse:
    ids_raw = request.GET.get("ids", "")
    if not ids_raw:
        return HttpResponseBadRequest("Indique ids= separados por coma.")
    try:
        ids = [int(x.strip()) for x in ids_raw.split(",") if x.strip()]
    except ValueError:
        return HttpResponseBadRequest("IDs inválidos.")
    if not ids:
        return HttpResponseBadRequest("Sin casos.")
    if len(ids) > 100:
        return HttpResponseBadRequest("Máximo 100 pestañas por archivo.")
    casos = list(CasoRojo.objects.filter(pk__in=ids).order_by("-score", "hab_id"))
    if not casos:
        raise Http404("No hay casos con esos IDs.")
    if len(casos) == 1:
        data = generar_excel_informe(casos[0])
        return _excel_response(data, nombre_archivo_informe(casos[0]))
    data = generar_excel_informes_multiples(casos)
    return _excel_response(data, nombre_archivo_multinforme(len(casos)))


def queryset_desde_request(request, queryset=None):
    """Casos seleccionados en admin action o queryset explícito."""
    if queryset is not None:
        return queryset
    ids = request.POST.getlist("_selected_action") or request.POST.getlist("caso_ids")
    if ids:
        return CasoRojo.objects.filter(pk__in=ids)
    return CasoRojo.objects.none()


def respuesta_excel_admin(request, queryset, modo: str) -> HttpResponse | None:
    """modo: 'informe' | 'lote' | 'informe_multi'"""
    casos = list(queryset.order_by("-score", "hab_id"))
    if not casos:
        return None
    if modo == "lote":
        return _excel_response(generar_excel_lote(casos), nombre_archivo_lote(len(casos)))
    if len(casos) == 1:
        c = casos[0]
        return _excel_response(generar_excel_informe(c), nombre_archivo_informe(c))
    if modo == "informe_multi":
        return _excel_response(
            generar_excel_informes_multiples(casos),
            nombre_archivo_multinforme(len(casos)),
        )
    return _excel_response(
        generar_excel_informes_multiples(casos),
        nombre_archivo_multinforme(len(casos)),
    )
