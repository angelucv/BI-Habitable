# -*- coding: utf-8 -*-
"""Crea grupos CPEH y usuarios ejemplo inspector / revisor / coordinador."""
from __future__ import annotations

from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from inspecciones.models import CasoRojo, EvidenciaFoto, HistorialEstado, Procedimiento
from inspecciones.workflow import GRUPO_COORDINADOR, GRUPO_INSPECTOR, GRUPO_REVISOR, asegurar_grupos

USUARIOS_EJEMPLO = (
    {
        "username": "inspector.demo",
        "password": "Inspector2026!",
        "first_name": "Ana",
        "last_name": "Inspector Demo",
        "email": "inspector.demo@cpeh.local",
        "grupo": GRUPO_INSPECTOR,
    },
    {
        "username": "revisor.demo",
        "password": "Revisor2026!",
        "first_name": "Carlos",
        "last_name": "Revisor Demo",
        "email": "revisor.demo@cpeh.local",
        "grupo": GRUPO_REVISOR,
    },
    {
        "username": "coordinador.demo",
        "password": "Coordinador2026!",
        "first_name": "María",
        "last_name": "Coordinador Demo",
        "email": "coordinador.demo@cpeh.local",
        "grupo": GRUPO_COORDINADOR,
    },
)


def _permisos_modelo(model, acciones: tuple[str, ...]) -> list[Permission]:
    ct = ContentType.objects.get_for_model(model)
    return list(Permission.objects.filter(content_type=ct, codename__in=[f"{a}_{model._meta.model_name}" for a in acciones]))


class Command(BaseCommand):
    help = "Crea grupos cpeh_* y usuarios demo inspector / revisor / coordinador"

    def handle(self, *args, **options):
        grupos = asegurar_grupos()

        perms_caso_rw = _permisos_modelo(CasoRojo, ("view", "add", "change"))
        perms_caso_all = _permisos_modelo(CasoRojo, ("view", "add", "change", "delete"))
        perms_proc_view = _permisos_modelo(Procedimiento, ("view",))
        perms_hist_view = _permisos_modelo(HistorialEstado, ("view",))
        perms_foto_rw = _permisos_modelo(EvidenciaFoto, ("view", "add", "change"))

        grupos[GRUPO_INSPECTOR].permissions.set(
            perms_caso_rw + perms_proc_view + perms_hist_view + perms_foto_rw
        )
        grupos[GRUPO_REVISOR].permissions.set(
            perms_caso_rw + perms_proc_view + perms_hist_view + perms_foto_rw
        )
        grupos[GRUPO_COORDINADOR].permissions.set(
            perms_caso_all
            + _permisos_modelo(Procedimiento, ("view", "add", "change"))
            + _permisos_modelo(HistorialEstado, ("view",))
            + _permisos_modelo(EvidenciaFoto, ("view", "add", "change", "delete"))
        )

        for spec in USUARIOS_EJEMPLO:
            user, created = User.objects.get_or_create(
                username=spec["username"],
                defaults={
                    "first_name": spec["first_name"],
                    "last_name": spec["last_name"],
                    "email": spec["email"],
                    "is_staff": True,
                },
            )
            user.set_password(spec["password"])
            user.is_staff = True
            user.save()
            user.groups.set([grupos[spec["grupo"]]])
            accion = "Creado" if created else "Actualizado"
            self.stdout.write(f"{accion}: {user.username} → {spec['grupo']}")

        self.stdout.write(self.style.SUCCESS("Usuarios demo listos (ver guía desarrolladores §6.1)."))
