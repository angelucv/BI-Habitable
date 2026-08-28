"""Catálogo de procedimientos de reparación (referencia técnica VIG / COL / MAM)."""

PROCEDIMIENTOS_INICIALES: list[dict[str, str]] = [
    {
        "codigo": "VIG-01",
        "categoria": "VIG",
        "titulo": "Inyección estructural de fisuras en vigas",
        "descripcion": "Inyección de resina o lechada en fisuras de flexión o corte en vigas con daño leve a moderado.",
    },
    {
        "codigo": "VIG-02",
        "categoria": "VIG",
        "titulo": "Reparación localizada de recubrimiento en vigas",
        "descripcion": "Restitución de recubrimiento y protección en zonas con pérdida localizada del hormigón.",
    },
    {
        "codigo": "VIG-03",
        "categoria": "VIG",
        "titulo": "Reconstrucción de rótula plástica",
        "descripcion": "Reparación de nudos con formación de rótula plástica bajo descarga diseñada.",
    },
    {
        "codigo": "VIG-04",
        "categoria": "VIG",
        "titulo": "Reconstrucción de núcleo en vigas",
        "descripcion": "Sustitución o reconstrucción del núcleo comprimido con confinamiento adecuado.",
    },
    {
        "codigo": "COL-01",
        "categoria": "COL",
        "titulo": "Sellado y protección superficial en columnas",
        "descripcion": "Tratamiento de fisuras superficiales y protección anticorrosiva.",
    },
    {
        "codigo": "COL-02",
        "categoria": "COL",
        "titulo": "Inyección estructural en columnas",
        "descripcion": "Inyección de resina o lechada en fisuras diagonales o longitudinales.",
    },
    {
        "codigo": "COL-03",
        "categoria": "COL",
        "titulo": "Reparación localizada de recubrimiento en columnas",
        "descripcion": "Reparación parcial del recubrimiento con mortero estructural o equivalente.",
    },
    {
        "codigo": "COL-04",
        "categoria": "COL",
        "titulo": "Reconstrucción equivalente bajo descarga diseñada",
        "descripcion": "Reconstrucción de sección de columna con apuntalamiento y descarga calculada.",
    },
    {
        "codigo": "COL-05",
        "categoria": "COL",
        "titulo": "Refuerzo o encamisado de columnas",
        "descripcion": "Encamisado, confinamiento o refuerzo externo para recuperar capacidad portante.",
    },
    {
        "codigo": "COL-CRIT",
        "categoria": "COL",
        "titulo": "Condición crítica — fuera de alcance de reparación",
        "descripcion": "Aplastamiento, pandeo de barras, núcleo triturado u otros mecanismos fuera de COL-01 a COL-04.",
    },
    {
        "codigo": "MAM-01",
        "categoria": "MAM",
        "titulo": "Reparación no estructural de fisuras leves",
        "descripcion": "Sellado de fisuras en mampostería o tabiques no estructurales.",
    },
    {
        "codigo": "MAM-02",
        "categoria": "MAM",
        "titulo": "Inyección estructural en mampostería",
        "descripcion": "Inyección de fisuras y grietas moderadas en muros de arriostre o mampostería.",
    },
    {
        "codigo": "MAM-03",
        "categoria": "MAM",
        "titulo": "Reconstrucción localizada (llaveado y costura)",
        "descripcion": "Reconstrucción parcial de paños con llaveado y costura estructural.",
    },
    {
        "codigo": "MAM-04",
        "categoria": "MAM",
        "titulo": "Sustitución por tabiquería liviana sismorresistente",
        "descripcion": "Reemplazo de mampostería dañada en rutas de evacuación por sistema liviano.",
    },
]
