"""Secciones numeradas del informe — títulos compartidos (admin + PDF)."""

CASE_FIELDSETS: tuple[tuple[str, dict], ...] = (
    (
        "1 — Precarga Habitable (Fase 1)",
        {
            "fields": (
                "hab_id",
                "certificado",
                "nombre_hab",
                "etiqueta_f1",
                "fecha_f1",
                "inspector_f1",
                "direccion_hab",
                "muni_parr",
                "pisos_f1",
                "riesgos_f1",
                "colapso_f1",
                "piso_crit_f1",
                "acciones_f1",
                "obs_f1",
                "gps_hab",
            ),
        },
    ),
    (
        "2 — Ranking y prioridad",
        {"fields": ("score", "banda", "puestos", "score_detalle", "prob_rel")},
    ),
    (
        "3 — Validación de la precarga",
        {
            "fields": (
                "val_edificio",
                "val_etiqueta",
                "val_geometria",
                "val_ranking",
                "correcciones",
                "inspector_asignado",
                "revisor_asignado",
            ),
        },
    ),
    (
        "4 — Identidad y edificio (visita 2)",
        {
            "fields": (
                "nombre_conf",
                "fecha_v2",
                "gps_v2",
                "evaluadores_v2",
                "supervisor_v2",
                "uso",
                "pisos_conf",
                "sotanos_conf",
                "sistema",
                "ocupacion",
                "peligro_aledanos",
            ),
        },
    ),
    (
        "5 — Daño detallado (visita 2)",
        {
            "fields": (
                "piso_crit_v2",
                "pct_columnas",
                "inclinacion",
                "delta_incl",
                "dano_vigas",
                "riesgo_fachada",
                "analisis_libre",
            ),
        },
    ),
    (
        "6 — Daño estructural (detalle)",
        {
            "classes": ("collapse",),
            "fields": (
                "col_mec",
                "col_nivel",
                "col_evidencia",
                "vig_mec",
                "vig_nivel",
                "vig_evidencia",
                "mur_mec",
                "mur_nivel",
                "escaleras",
                "preexistentes",
            ),
        },
    ),
    (
        "7 — Mampostería",
        {
            "classes": ("collapse",),
            "fields": ("mam_mec", "mam_nivel", "mam_diag"),
        },
    ),
    (
        "8 — Procedimientos sugeridos",
        {
            "classes": ("collapse",),
            "fields": ("proc_codigos", "repar_viable", "proc_notas"),
        },
    ),
    (
        "9 — Decisión de control",
        {
            "fields": (
                "estado_2da",
                "decision_D",
                "complementos_D",
                "complemento_plazo",
                "complemento_detalle",
                "magnitud_M",
                "prioridad",
                "medidas",
                "justificacion",
            ),
        },
    ),
    (
        "10 — Evidencia y firmas",
        {"fields": ("n_fotos", "firmas")},
    ),
    (
        "11 — Resumen ejecutivo",
        {"fields": ("resumen_ejecutivo",)},
    ),
    (
        "12 — Auditoría del sistema",
        {
            "classes": ("collapse",),
            "fields": ("created_at", "updated_at"),
        },
    ),
)
