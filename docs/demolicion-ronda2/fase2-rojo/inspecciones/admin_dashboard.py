"""KPIs compactos para la portada del admin."""
from __future__ import annotations

from django.contrib import admin

from inspecciones import choices as ch
from inspecciones.models import CasoRojo


def _kpi(label: str, value: int, icon: str, css_class: str, url: str = "/admin/inspecciones/casorojo/") -> dict:
    return {"label": label, "value": value, "icon": icon, "class": css_class, "url": url}


def get_dashboard_context() -> dict:
    qs = CasoRojo.objects.all()
    total = qs.count()
    return {
        "dashboard_kpis": [
            _kpi("Casos totales", total, "fas fa-building", "kpi-blue"),
            _kpi(
                "Sin inspector",
                qs.filter(inspector_asignado__isnull=True).count(),
                "fas fa-user-slash",
                "kpi-yellow",
                "/asignacion/?sin_inspector=1",
            ),
            _kpi(
                "Sin revisor",
                qs.filter(revisor_asignado__isnull=True).count(),
                "fas fa-user-clock",
                "kpi-yellow",
                "/asignacion/?sin_revisor=1",
            ),
            _kpi("D1 Complementos", qs.filter(decision_D=ch.DecisionD.D1).count(), "fas fa-tasks", "kpi-blue"),
            _kpi("D2 Reparar", qs.filter(decision_D=ch.DecisionD.D2).count(), "fas fa-tools", "kpi-yellow"),
            _kpi("D3 Demoler", qs.filter(decision_D=ch.DecisionD.D3).count(), "fas fa-exclamation-triangle", "kpi-red"),
            _kpi("D4 Escombros", qs.filter(decision_D=ch.DecisionD.D4).count(), "fas fa-dumpster", "kpi-red"),
            _kpi(
                "Sin dictamen",
                qs.filter(decision_D=ch.DecisionD.PENDIENTE).count(),
                "fas fa-question-circle",
                "kpi-neutral",
            ),
            _kpi(
                "Pend. verificación",
                qs.filter(estado_2da=ch.Estado2daRonda.PENDIENTE).count(),
                "fas fa-clock",
                "kpi-neutral",
            ),
            _kpi("En visita", qs.filter(estado_2da=ch.Estado2daRonda.EN_VISITA).count(), "fas fa-hard-hat", "kpi-yellow"),
            _kpi("Borrador", qs.filter(estado_2da=ch.Estado2daRonda.BORRADOR).count(), "fas fa-pencil-alt", "kpi-blue"),
            _kpi("Revisados", qs.filter(estado_2da=ch.Estado2daRonda.REVISADO).count(), "fas fa-check", "kpi-green"),
            _kpi("Aprobados", qs.filter(estado_2da=ch.Estado2daRonda.APROBADO).count(), "fas fa-check-double", "kpi-green"),
            _kpi(
                "Prior. inmediata",
                qs.filter(prioridad=ch.PrioridadOperativa.INMEDIATA).count(),
                "fas fa-bolt",
                "kpi-red",
            ),
            _kpi("Prior. alta", qs.filter(prioridad=ch.PrioridadOperativa.ALTA).count(), "fas fa-fire", "kpi-red"),
            _kpi(
                "Score ≥ 70",
                qs.filter(score__gte=70).count(),
                "fas fa-chart-line",
                "kpi-red",
            ),
            _kpi(
                "Con visita 2",
                qs.filter(fecha_v2__isnull=False).count(),
                "fas fa-calendar-check",
                "kpi-blue",
            ),
        ],
        "dashboard_recientes": qs.order_by("-updated_at")[:8],
        "dashboard_total": total,
    }


def patch_admin_index() -> None:
    original = admin.site.index

    def index(request, extra_context=None):
        ctx = extra_context or {}
        ctx.update(get_dashboard_context())
        return original(request, ctx)

    admin.site.index = index
