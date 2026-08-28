"""Modelo consolidado Fase II — 11 secciones numeradas (plantilla Excel / Franco Mar)."""
from django.conf import settings
from django.db import models

from . import choices as ch


class CasoRojo(models.Model):
    """Un caso ROJO en 2.ª ronda (informe consolidado en una fila administrable)."""

    # --- 1 Precarga Habitable ---
    hab_id = models.PositiveIntegerField("ID Habitable", unique=True, db_index=True)
    certificado = models.CharField(max_length=64, blank=True)
    nombre_hab = models.CharField("Nombre (Habitable)", max_length=255, blank=True)
    etiqueta_f1 = models.CharField("Etiqueta Fase 1", max_length=20, default="ROJO")
    fecha_f1 = models.DateField("Fecha inspección Fase 1", null=True, blank=True)
    inspector_f1 = models.CharField("Inspector Fase 1", max_length=255, blank=True)
    direccion_hab = models.CharField("Dirección Habitable", max_length=500, blank=True)
    muni_parr = models.CharField("Municipio / Parroquia", max_length=255, blank=True)
    pisos_f1 = models.CharField("Pisos / sótanos (Fase 1)", max_length=64, blank=True)
    riesgos_f1 = models.CharField("Riesgo externo / severo", max_length=128, blank=True)
    colapso_f1 = models.CharField("Colapso estructura (Fase 1)", max_length=16, blank=True)
    piso_crit_f1 = models.CharField("Piso crítico (Fase 1)", max_length=255, blank=True)
    acciones_f1 = models.CharField("Acciones Fase 1", max_length=255, blank=True)
    obs_f1 = models.TextField("Observaciones Fase 1", blank=True)
    gps_hab = models.CharField("GPS Habitable", max_length=64, blank=True)
    lat = models.DecimalField("Latitud", max_digits=10, decimal_places=7, null=True, blank=True, db_index=True)
    lng = models.DecimalField("Longitud", max_digits=10, decimal_places=7, null=True, blank=True, db_index=True)

    # --- 2 Ranking ---
    score = models.PositiveSmallIntegerField("Score gravedad (0–100)", null=True, blank=True)
    banda = models.CharField("Banda prioridad", max_length=32, blank=True)
    puestos = models.CharField("Puesto La Guaira / nacional", max_length=64, blank=True)
    score_detalle = models.TextField("Detalle del score", blank=True)
    prob_rel = models.CharField("Probabilidad relativa (texto)", max_length=255, blank=True)

    # --- 3 Validación ---
    val_edificio = models.CharField(
        max_length=32, choices=ch.SiNoParcial.choices, default=ch.SiNoParcial.PENDIENTE, blank=True
    )
    val_etiqueta = models.CharField(
        max_length=32, choices=ch.SiNoInsuf.choices, default=ch.SiNoInsuf.PENDIENTE, blank=True
    )
    val_geometria = models.CharField(
        max_length=32, choices=ch.SiNoParcial.choices, default=ch.SiNoParcial.PENDIENTE, blank=True
    )
    val_ranking = models.CharField(
        max_length=32, choices=ch.SiNoParcial.choices, default=ch.SiNoParcial.PENDIENTE, blank=True
    )
    correcciones = models.TextField("Correcciones a la precarga", blank=True)

    # --- Asignación operativa ---
    inspector_asignado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="casos_inspeccion",
        verbose_name="Inspector asignado",
    )
    revisor_asignado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="casos_revision",
        verbose_name="Revisor asignado",
    )

    # --- 4 Identidad y edificio (visita 2) ---
    nombre_conf = models.CharField("Nombre confirmado", max_length=255, blank=True)
    fecha_v2 = models.DateField("Fecha visita detallada", null=True, blank=True)
    gps_v2 = models.CharField("GPS control (visita)", max_length=64, blank=True)
    evaluadores_v2 = models.CharField("Evaluadores visita 2", max_length=500, blank=True)
    supervisor_v2 = models.CharField("Supervisor", max_length=255, blank=True)
    uso = models.CharField("Uso", max_length=128, blank=True)
    pisos_conf = models.CharField("Pisos confirmados", max_length=16, blank=True)
    sotanos_conf = models.CharField("Sótanos confirmados", max_length=16, blank=True)
    sistema = models.CharField(
        max_length=64, choices=ch.SistemaEstructural.choices, default=ch.SistemaEstructural.PENDIENTE, blank=True
    )
    ocupacion = models.CharField(
        max_length=32, choices=ch.Ocupacion.choices, default=ch.Ocupacion.PENDIENTE, blank=True
    )
    peligro_aledanos = models.CharField(
        max_length=32, choices=ch.PeligroAledanos.choices, default=ch.PeligroAledanos.PENDIENTE, blank=True
    )

    # --- 5 Daño detallado ---
    piso_crit_v2 = models.CharField("Piso crítico (visita 2)", max_length=255, blank=True)
    pct_columnas = models.CharField(
        max_length=32, choices=ch.PctColumnas.choices, default=ch.PctColumnas.PENDIENTE, blank=True
    )
    inclinacion = models.CharField(
        max_length=32, choices=ch.Inclinacion.choices, default=ch.Inclinacion.PENDIENTE, blank=True
    )
    delta_incl = models.CharField("Δ inclinación (si midió)", max_length=64, blank=True)
    dano_vigas = models.CharField(
        max_length=16, choices=ch.NivelABC.choices, default=ch.NivelABC.PENDIENTE, blank=True
    )
    riesgo_fachada = models.CharField(
        max_length=16, choices=ch.NivelABC.choices, default=ch.NivelABC.PENDIENTE, blank=True
    )
    analisis_libre = models.TextField("Análisis libre (ingeniero)", blank=True)

    # --- 6 Daño estructural (detalle) ---
    col_mec = models.CharField("Columnas — mecanismo", max_length=255, blank=True)
    col_nivel = models.CharField(
        max_length=16, choices=ch.NivelABC.choices, default=ch.NivelABC.PENDIENTE, blank=True
    )
    col_evidencia = models.TextField("Columnas — ubicación / evidencia", blank=True)
    vig_mec = models.CharField("Vigas — mecanismo", max_length=255, blank=True)
    vig_nivel = models.CharField(
        max_length=16, choices=ch.NivelABC.choices, default=ch.NivelABC.PENDIENTE, blank=True
    )
    vig_evidencia = models.TextField("Vigas — ubicación / evidencia", blank=True)
    mur_mec = models.CharField("Muros/pantallas — mecanismo", max_length=255, blank=True)
    mur_nivel = models.CharField(
        max_length=16, choices=ch.NivelABC.choices, default=ch.NivelABC.PENDIENTE, blank=True
    )
    escaleras = models.TextField("Escaleras / evacuación", blank=True)
    preexistentes = models.TextField("Daños preexistentes (pre 24/06/2026)", blank=True)

    # --- 7 Mampostería ---
    mam_mec = models.CharField("Mampostería — mecanismo", max_length=255, blank=True)
    mam_nivel = models.CharField(
        max_length=16, choices=ch.NivelABC.choices, default=ch.NivelABC.PENDIENTE, blank=True
    )
    mam_diag = models.TextField("Diagnóstico mampostería", blank=True)

    # --- 8 Procedimientos sugeridos ---
    proc_codigos = models.TextField("Procedimientos seleccionados (códigos)", blank=True)
    repar_viable = models.CharField(
        max_length=32, choices=ch.SiNoInsuf.choices, default=ch.SiNoInsuf.PENDIENTE, blank=True
    )
    proc_notas = models.TextField("Notas procedimientos", blank=True)

    # --- 9 Decisión de control ---
    estado_2da = models.CharField(
        max_length=32,
        choices=ch.Estado2daRonda.choices,
        default=ch.Estado2daRonda.PENDIENTE,
        blank=True,
    )
    decision_D = models.CharField(
        max_length=64, choices=ch.DecisionD.choices, default=ch.DecisionD.PENDIENTE, blank=True
    )
    complementos_D = models.CharField(
        "Complementos requeridos (D1)",
        max_length=128,
        blank=True,
        help_text="Códigos separados por coma: GEO, ENS, MOD, MON, INV, REI, ALE, OTR.",
    )
    complemento_plazo = models.DateField("Plazo / fecha objetivo (D1)", null=True, blank=True)
    complemento_detalle = models.TextField(
        "Detalle complemento — qué falta y entregable (D1)",
        blank=True,
    )
    magnitud_M = models.CharField(
        max_length=64, choices=ch.MagnitudM.choices, default=ch.MagnitudM.PENDIENTE, blank=True
    )
    prioridad = models.CharField(
        max_length=32, choices=ch.PrioridadOperativa.choices, default=ch.PrioridadOperativa.PENDIENTE, blank=True
    )
    medidas = models.TextField("Medidas inmediatas", blank=True)
    justificacion = models.TextField("Justificación libre", blank=True)

    # --- 10 Evidencia ---
    n_fotos = models.CharField("N.º de fotos", max_length=128, blank=True)
    firmas = models.CharField("Firmas (elaboró / revisó / aprobó)", max_length=500, blank=True)

    # --- 11 Resumen ---
    resumen_ejecutivo = models.TextField("Resumen ejecutivo", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Caso ROJO Fase II"
        verbose_name_plural = "Casos ROJO Fase II"
        ordering = ["-score", "hab_id"]

    def __str__(self) -> str:
        nombre = self.nombre_conf or self.nombre_hab or f"ID {self.hab_id}"
        return f"{self.hab_id} — {nombre}"

    def sync_gps_texto(self) -> None:
        if self.lat is not None and self.lng is not None and not self.gps_hab:
            self.gps_hab = f"{self.lat}, {self.lng}"


class InformePdfAdjunto(models.Model):
    """Informe PDF en formato libre (original de campo / escaneado)."""

    caso = models.ForeignKey(
        CasoRojo,
        on_delete=models.CASCADE,
        related_name="informes_pdf",
        verbose_name="Caso ROJO",
    )
    archivo = models.FileField(
        "Archivo PDF",
        upload_to="informes/%Y/%m/",
        help_text="Informe técnico original en PDF (cualquier formato / plantilla).",
    )
    titulo = models.CharField("Título / referencia", max_length=255, blank=True)
    nombre_archivo_origen = models.CharField("Nombre archivo origen", max_length=255, blank=True)
    tipo_informe = models.CharField("Tipo de informe", max_length=128, blank=True)
    codigo_documento = models.CharField("Código documento", max_length=64, blank=True)
    notas = models.TextField("Notas", blank=True)
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="informes_pdf_subidos",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Informe PDF adjunto"
        verbose_name_plural = "Informes PDF adjuntos"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        ref = self.titulo or self.nombre_archivo_origen or f"PDF #{self.pk}"
        return f"{self.caso.hab_id} — {ref}"


class CategoriaProcedimiento(models.TextChoices):
    VIG = "VIG", "Vigas"
    COL = "COL", "Columnas"
    MAM = "MAM", "Mampostería"
    OTRO = "OTRO", "Otro"


class Procedimiento(models.Model):
    """Catálogo de procedimientos de reparación (referencia técnica)."""

    codigo = models.CharField("Código", max_length=16, unique=True)
    categoria = models.CharField(max_length=8, choices=CategoriaProcedimiento.choices)
    titulo = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Procedimiento"
        verbose_name_plural = "Catálogo de procedimientos"
        ordering = ["categoria", "codigo"]

    def __str__(self) -> str:
        return f"{self.codigo} — {self.titulo}"


class HistorialEstado(models.Model):
    """Trazabilidad de cambios de estado en el flujo de revisión."""

    caso = models.ForeignKey(CasoRojo, on_delete=models.CASCADE, related_name="historial_estados")
    estado_anterior = models.CharField(max_length=32, blank=True)
    estado_nuevo = models.CharField(max_length=32)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    nota = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Historial de estado"
        verbose_name_plural = "Historial de estados"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.caso.hab_id}: {self.estado_anterior} → {self.estado_nuevo}"


class EvidenciaFoto(models.Model):
    """Fotografía de evidencia vinculada a un caso."""

    caso = models.ForeignKey(CasoRojo, on_delete=models.CASCADE, related_name="fotos")
    imagen = models.ImageField("Imagen", upload_to="evidencias/%Y/%m/")
    descripcion = models.CharField(max_length=255, blank=True)
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Foto de evidencia"
        verbose_name_plural = "Fotos de evidencia"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Foto {self.pk} — caso {self.caso.hab_id}"
