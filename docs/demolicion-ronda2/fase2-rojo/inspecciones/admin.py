from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils.html import format_html

from .models import CasoRojo, EvidenciaFoto, HistorialEstado, InformePdfAdjunto, Procedimiento
from .gps_utils import coordenadas_caso
from .section_labels import CASE_FIELDSETS
from .workflow import es_coordinador, es_inspector, es_revisor, validar_dictamen, validar_transicion_estado


class HistorialEstadoInline(admin.TabularInline):
    model = HistorialEstado
    extra = 0
    readonly_fields = ("estado_anterior", "estado_nuevo", "usuario", "nota", "created_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class EvidenciaFotoInline(admin.TabularInline):
    model = EvidenciaFoto
    extra = 1
    fields = ("imagen", "descripcion", "subido_por", "created_at")
    readonly_fields = ("created_at",)


class InformePdfAdjuntoInline(admin.TabularInline):
    model = InformePdfAdjunto
    extra = 1
    fields = (
        "titulo",
        "archivo",
        "tipo_informe",
        "codigo_documento",
        "notas",
        "ver_pdf",
        "created_at",
    )
    readonly_fields = ("ver_pdf", "created_at")

    @admin.display(description="Ver")
    def ver_pdf(self, obj: InformePdfAdjunto) -> str:
        if obj.pk and obj.archivo:
            url = reverse("ver_informe_pdf_adjunto", args=[obj.pk])
            return format_html(
                '<a href="{}" target="_blank" rel="noopener">Abrir PDF</a>', url
            )
        return "—"


@admin.register(CasoRojo)
class CasoRojoAdmin(admin.ModelAdmin):
    change_form_template = "admin/inspecciones/casorojo/change_form.html"
    inlines = [InformePdfAdjuntoInline, EvidenciaFotoInline, HistorialEstadoInline]
    list_display = (
        "hab_id",
        "nombre_conf",
        "score",
        "banda",
        "estado_2da",
        "decision_D",
        "prioridad",
        "inspector_asignado",
        "fecha_v2",
        "enlace_pdf",
        "enlace_excel",
        "enlace_mapa",
    )
    list_display_links = ("hab_id", "nombre_conf")
    list_filter = (
        "estado_2da",
        "decision_D",
        "prioridad",
        "banda",
        "etiqueta_f1",
        "val_etiqueta",
        "sistema",
        "inspector_asignado",
        "revisor_asignado",
    )
    search_fields = (
        "hab_id",
        "nombre_hab",
        "nombre_conf",
        "certificado",
        "direccion_hab",
        "muni_parr",
        "evaluadores_v2",
    )
    readonly_fields = ("created_at", "updated_at", "lat", "lng")
    autocomplete_fields = ("inspector_asignado", "revisor_asignado")
    date_hierarchy = "fecha_v2"
    list_per_page = 30
    save_on_top = True
    actions = (
        "descargar_excel_informe",
        "descargar_excel_lote",
        "marcar_en_visita",
        "enviar_a_revision",
    )

    @admin.action(description="Descargar Excel informe (1 pestaña/caso)")
    def descargar_excel_informe(self, request, queryset):
        from inspecciones.export_views import respuesta_excel_admin

        resp = respuesta_excel_admin(request, queryset, "informe_multi")
        if resp:
            return resp
        self.message_user(request, "Sin casos seleccionados.", level=messages.WARNING)

    @admin.action(description="Descargar Excel lote (1 fila/caso)")
    def descargar_excel_lote(self, request, queryset):
        from inspecciones.export_views import respuesta_excel_admin

        if queryset.count() > 500:
            self.message_user(request, "Máximo 500 casos por lote.", level=messages.ERROR)
            return
        resp = respuesta_excel_admin(request, queryset, "lote")
        if resp:
            return resp
        self.message_user(request, "Sin casos seleccionados.", level=messages.WARNING)

    @admin.action(description="Marcar seleccionados → En visita")
    def marcar_en_visita(self, request, queryset):
        from inspecciones import choices as ch

        n = 0
        for caso in queryset:
            try:
                validar_transicion_estado(request.user, caso.estado_2da, ch.Estado2daRonda.EN_VISITA)
                anterior = caso.estado_2da
                caso.estado_2da = ch.Estado2daRonda.EN_VISITA
                caso.save(update_fields=["estado_2da", "updated_at"])
                HistorialEstado.objects.create(
                    caso=caso,
                    estado_anterior=anterior,
                    estado_nuevo=caso.estado_2da,
                    usuario=request.user,
                    nota="Acción masiva admin",
                )
                n += 1
            except ValidationError as exc:
                self.message_user(request, f"{caso.hab_id}: {exc}", level=messages.WARNING)
        self.message_user(request, f"{n} caso(s) marcados En visita.", level=messages.SUCCESS)

    @admin.action(description="Enviar seleccionados → Revisado")
    def enviar_a_revision(self, request, queryset):
        from inspecciones import choices as ch

        n = 0
        for caso in queryset:
            try:
                validar_transicion_estado(request.user, caso.estado_2da, ch.Estado2daRonda.REVISADO)
                validar_dictamen(caso, cerrar=True)
                anterior = caso.estado_2da
                caso.estado_2da = ch.Estado2daRonda.REVISADO
                caso.save()
                HistorialEstado.objects.create(
                    caso=caso,
                    estado_anterior=anterior,
                    estado_nuevo=caso.estado_2da,
                    usuario=request.user,
                    nota="Enviado a revisión (acción masiva)",
                )
                n += 1
            except ValidationError as exc:
                self.message_user(request, f"{caso.hab_id}: {exc}", level=messages.WARNING)
        self.message_user(request, f"{n} caso(s) enviados a Revisado.", level=messages.SUCCESS)

    @admin.display(description="Excel")
    def enlace_excel(self, obj: CasoRojo) -> str:
        url = reverse("export_excel_informe", args=[obj.pk])
        return format_html('<a href="{}" title="Plantilla informe">XLS</a>', url)

    @admin.display(description="PDF")
    def enlace_pdf(self, obj: CasoRojo) -> str:
        url = reverse("admin:inspecciones_casorojo_pdf", args=[obj.pk])
        return format_html('<a href="{}" target="_blank" rel="noopener">PDF</a>', url)

    @admin.display(description="Mapa")
    def enlace_mapa(self, obj: CasoRojo) -> str:
        if not coordenadas_caso(obj):
            return "—"
        url = reverse("mapa_casos") + f"?caso={obj.hab_id}"
        return format_html('<a href="{}" target="_blank" rel="noopener">Ver</a>', url)

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if not es_coordinador(request.user):
            ro.extend(["inspector_asignado", "revisor_asignado"])
        if es_inspector(request.user) and not es_revisor(request.user) and obj:
            if obj.estado_2da in ("Revisado", "Aprobado", "Publicado"):
                return [f.name for f in self.model._meta.fields if f.name not in ("id",)]
        return ro

    def save_model(self, request, obj, form, change):
        anterior = None
        if change and obj.pk:
            anterior = CasoRojo.objects.filter(pk=obj.pk).values_list("estado_2da", flat=True).first()
            if anterior and anterior != obj.estado_2da:
                validar_transicion_estado(request.user, anterior, obj.estado_2da)
        from inspecciones import choices as ch

        cerrar = obj.estado_2da in (
            ch.Estado2daRonda.REVISADO,
            ch.Estado2daRonda.APROBADO,
            ch.Estado2daRonda.PUBLICADO,
        )
        validar_dictamen(obj, cerrar=cerrar)
        obj.sync_gps_texto()
        super().save_model(request, obj, form, change)
        if change and anterior and anterior != obj.estado_2da:
            HistorialEstado.objects.create(
                caso=obj,
                estado_anterior=anterior,
                estado_nuevo=obj.estado_2da,
                usuario=request.user,
            )

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for inst in instances:
            if isinstance(inst, EvidenciaFoto) and not inst.subido_por_id:
                inst.subido_por = request.user
            if isinstance(inst, InformePdfAdjunto):
                if not inst.subido_por_id:
                    inst.subido_por = request.user
                if inst.archivo and not inst.nombre_archivo_origen:
                    inst.nombre_archivo_origen = inst.archivo.name.rsplit("/", 1)[-1]
            inst.save()
        formset.save_m2m()
        for inst in formset.deleted_objects:
            inst.delete()

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<path:object_id>/pdf/",
                self.admin_site.admin_view(self.vista_pdf),
                name="inspecciones_casorojo_pdf",
            ),
        ]
        return custom + urls

    def vista_pdf(self, request, object_id):
        from inspecciones.views import caso_rojo_pdf

        caso = get_object_or_404(CasoRojo, pk=object_id)
        return caso_rojo_pdf(request, caso.pk)

    fieldsets = CASE_FIELDSETS


@admin.register(Procedimiento)
class ProcedimientoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "categoria", "titulo", "activo")
    list_filter = ("categoria", "activo")
    search_fields = ("codigo", "titulo", "descripcion")
    ordering = ("categoria", "codigo")


@admin.register(HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):
    list_display = ("caso", "estado_anterior", "estado_nuevo", "usuario", "created_at")
    list_filter = ("estado_nuevo",)
    search_fields = ("caso__hab_id", "caso__nombre_hab", "nota")
    readonly_fields = ("caso", "estado_anterior", "estado_nuevo", "usuario", "nota", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(EvidenciaFoto)
class EvidenciaFotoAdmin(admin.ModelAdmin):
    list_display = ("caso", "descripcion", "subido_por", "created_at")
    list_filter = ("created_at",)
    search_fields = ("caso__hab_id", "descripcion")
    autocomplete_fields = ("caso",)


@admin.register(InformePdfAdjunto)
class InformePdfAdjuntoAdmin(admin.ModelAdmin):
    list_display = ("caso", "titulo", "tipo_informe", "nombre_archivo_origen", "subido_por", "created_at", "enlace_ver")
    list_filter = ("tipo_informe", "created_at")
    search_fields = ("caso__hab_id", "titulo", "nombre_archivo_origen", "codigo_documento")
    autocomplete_fields = ("caso",)
    fields = (
        "caso",
        "archivo",
        "titulo",
        "tipo_informe",
        "codigo_documento",
        "nombre_archivo_origen",
        "notas",
        "subido_por",
        "created_at",
    )
    readonly_fields = ("created_at",)

    @admin.display(description="PDF")
    def enlace_ver(self, obj: InformePdfAdjunto) -> str:
        if obj.pk and obj.archivo:
            url = reverse("ver_informe_pdf_adjunto", args=[obj.pk])
            return format_html('<a href="{}" target="_blank" rel="noopener">Abrir</a>', url)
        return "—"

    def save_model(self, request, obj, form, change):
        if not obj.subido_por_id:
            obj.subido_por = request.user
        if obj.archivo and not obj.nombre_archivo_origen:
            obj.nombre_archivo_origen = obj.archivo.name.rsplit("/", 1)[-1]
        super().save_model(request, obj, form, change)
