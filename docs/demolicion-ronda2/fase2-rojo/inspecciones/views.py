from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_GET
from weasyprint import HTML

from django.conf import settings

from inspecciones.gps_utils import coordenadas_caso, filtrar_casos_con_gps
from inspecciones.guia_pdf import render_guia_usuario_pdf
from inspecciones.models import CasoRojo, InformePdfAdjunto
from inspecciones.report_sections import build_report_sections
from inspecciones.workflow import FlujoRevision


def health(request):
    return JsonResponse(
        {
            "status": "ok",
            "proyecto": "CPEH Fase II — Seguimiento ROJO",
            "version": "0.2.2-mapa-gps-fix",
            "casos": CasoRojo.objects.count(),
            "informes_pdf": InformePdfAdjunto.objects.count(),
        }
    )


def caso_rojo_pdf(request, pk: int) -> HttpResponse:
    caso = get_object_or_404(CasoRojo, pk=pk)
    nombre = caso.nombre_conf or caso.nombre_hab or f"ID {caso.hab_id}"
    html = render_to_string(
        "inspecciones/caso_rojo_informe_pdf.html",
        {
            "caso": caso,
            "nombre_display": nombre,
            "sections": build_report_sections(caso),
            "generado": timezone.localtime(timezone.now()),
        },
        request=request,
    )
    pdf = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()
    filename = f"informe-rojo-{caso.hab_id}.pdf"
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


@staff_member_required
@require_GET
def guia_usuario_pdf(request) -> HttpResponse:
    """Guía didáctica de usuario (PDF). Borrador hasta aprobación explícita."""
    borrador = not getattr(settings, "GUIA_USUARIO_PDF_APROBADA", False)
    pdf = render_guia_usuario_pdf(request=request, borrador=borrador)
    suffix = "borrador" if borrador else "aprobada"
    filename = f"guia-usuario-fase2-rojo-{suffix}.pdf"
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


@staff_member_required
def ver_informe_pdf_adjunto(request, pk: int) -> FileResponse:
    """Sirve el PDF original adjunto (formato libre)."""
    doc = get_object_or_404(InformePdfAdjunto, pk=pk)
    filename = doc.nombre_archivo_origen or f"informe-{doc.caso.hab_id}.pdf"
    response = FileResponse(doc.archivo.open("rb"), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


def _filtrar_queryset_mapa(request, qs):
    estado = request.GET.get("estado")
    decision = request.GET.get("decision")
    banda = request.GET.get("banda")
    min_score = request.GET.get("min_score")
    if estado:
        qs = qs.filter(estado_2da=estado)
    if decision:
        qs = qs.filter(decision_D__startswith=decision)
    if banda:
        qs = qs.filter(banda=banda)
    if min_score:
        try:
            qs = qs.filter(score__gte=int(min_score))
        except ValueError:
            pass
    return qs


@staff_member_required
@require_GET
def casos_geojson(request):
    """GeoJSON de casos con coordenadas para el mapa."""
    qs = _filtrar_queryset_mapa(request, CasoRojo.objects.all())

    features = []
    for c in filtrar_casos_con_gps(qs.iterator()):
        coords = coordenadas_caso(c)
        if not coords:
            continue
        lat, lng = coords
        nombre = c.nombre_conf or c.nombre_hab or f"ID {c.hab_id}"
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lng, lat]},
                "properties": {
                    "hab_id": c.hab_id,
                    "nombre": nombre,
                    "score": c.score,
                    "banda": c.banda,
                    "estado": c.estado_2da,
                    "decision": c.decision_D,
                    "prioridad": c.prioridad,
                    "direccion": c.direccion_hab,
                    "muni_parr": c.muni_parr,
                    "admin_url": f"/admin/inspecciones/casorojo/{c.pk}/change/",
                },
            }
        )
    return JsonResponse({"type": "FeatureCollection", "features": features})


@staff_member_required
def mapa_casos(request):
    """Mapa operativo de casos ROJO con GPS."""
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
    total_mapa = len(filtrar_casos_con_gps(CasoRojo.objects.all().iterator()))
    caso_foco = request.GET.get("caso")
    flujo = FlujoRevision()
    return render(
        request,
        "inspecciones/mapa_casos.html",
        {
            "estados": estados,
            "bandas": bandas,
            "total_mapa": total_mapa,
            "caso_foco": caso_foco,
            "flujo_pasos": flujo.pasos,
        },
    )

