from django.conf import settings
from django.contrib import admin
from django.urls import path
from django.views.static import serve

from inspecciones.asignacion_views import tablero_asignacion
from inspecciones.export_views import (
    export_excel_informe,
    export_excel_informes_multiples,
    export_excel_lote,
)
from inspecciones.views import casos_geojson, health, mapa_casos, ver_informe_pdf_adjunto

admin.site.site_header = "CPEH — Seguimiento ROJO Fase II"
admin.site.site_title = "CPEH Fase II"
admin.site.index_title = "Panel de administración"

urlpatterns = [
    path("api/health/", health),
    path("api/casos/geojson/", casos_geojson, name="casos_geojson"),
    path("informes/pdf/<int:pk>/", ver_informe_pdf_adjunto, name="ver_informe_pdf_adjunto"),
    path("mapa/", mapa_casos, name="mapa_casos"),
    path("asignacion/", tablero_asignacion, name="tablero_asignacion"),
    path("export/excel/informe/<int:pk>/", export_excel_informe, name="export_excel_informe"),
    path("export/excel/lote/", export_excel_lote, name="export_excel_lote"),
    path("export/excel/informes/", export_excel_informes_multiples, name="export_excel_informes_multiples"),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += [
        path("media/<path:path>", serve, {"document_root": settings.MEDIA_ROOT}),
    ]
