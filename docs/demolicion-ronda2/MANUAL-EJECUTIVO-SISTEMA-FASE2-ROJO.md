# Manual ejecutivo — Sistema Fase II ROJO (CPEH)

**Comisión Presidencial para la Evaluación de Habitabilidad**  
**Versión operativa:** agosto 2026 · **Ámbito:** segunda ronda de verificación de edificaciones etiqueta ROJO

---

## 1. Propósito del sistema

El sistema **Fase II ROJO** consolida la **segunda inspección técnica** de edificaciones declaradas **INSEGURAS (rojo)** tras el doble sismo del 24 de junio de 2026. Su objetivo es:

1. **Priorizar** casos según gravedad (ranking nacional y regional).
2. **Registrar** la visita detallada en un **informe único de 11 secciones** alineado a la plantilla acordada con Habitable.
3. **Gestionar** el flujo inspector → revisor → coordinación con trazabilidad.
4. **Adjuntar** informes PDF originales de campo y exportar datos para seguimiento operativo.

**URL de producción:** http://190.169.110.9/admin/

---

## 2. Actores y roles

| Rol | Responsabilidad | Acciones principales |
|-----|-----------------|----------------------|
| **Inspector** | Visita en campo, levantamiento técnico | Editar borrador del caso, cargar fotos, adjuntar PDF, proponer dictamen |
| **Revisor** | Validación técnica y coherencia | Revisar secciones, devolver correcciones, aprobar envío a revisado |
| **Coordinador** | Operación del programa | Asignar inspector/revisor, import masivo, tablero de avance, export Excel |
| **Administrador** | Infraestructura y usuarios | Django Admin completo, catálogos, despliegue |

### Usuarios de demostración (capacitación)

| Usuario | Rol | Contraseña inicial |
|---------|-----|-------------------|
| `inspector.demo` | Inspector | `Inspector2026!` |
| `revisor.demo` | Revisor | `Revisor2026!` |
| `coordinador.demo` | Coordinador | `Coordinador2026!` |

> Sustituir por cuentas institucionales antes de operación masiva.

---

## 3. Flujo operativo del proceso

```mermaid
flowchart LR
    A[Precarga Habitable] --> B[Ranking gravedad]
    B --> C[Asignación inspector/revisor]
    C --> D[Visita detallada — borrador]
    D --> E[Enviar a revisión]
    E --> F{Revisor}
    F -->|Correcciones| D
    F -->|Aprueba| G[Estado Revisado]
    G --> H[Export PDF / Excel]
```

### Estados de la segunda ronda

| Estado | Significado |
|--------|-------------|
| **Pendiente** | Caso en cola; sin visita iniciada |
| **Borrador** | Inspector trabajando el informe |
| **En revisión** | Enviado al revisor técnico |
| **Revisado** | Dictamen validado; listo para consolidación |
| **Cerrado** | Caso concluido operativamente |

### Transiciones válidas

- Inspector: **Pendiente/Borrador → En revisión** (con validación de campos mínimos).
- Revisor: **En revisión → Borrador** (devolución) o **→ Revisado**.
- Coordinador: puede reasignar en cualquier momento.

---

## 4. Modelo del informe (11 secciones)

Cada **Caso ROJO** es una fila administrable equivalente a la plantilla Excel de vaciado digital:

| Sección | Contenido | Origen típico |
|---------|-----------|---------------|
| **1. Precarga Habitable** | ID, certificado, dirección, inspector Fase 1, GPS | Import ranking Excel |
| **2. Ranking** | Score 0–100, banda, puesto La Guaira/nacional | Excel Ranking_ROJO_* |
| **3. Validación** | Confirmación edificio, etiqueta, geometría | Inspector en visita |
| **4. Identidad visita 2** | Nombre, fecha, evaluadores, uso, pisos, sistema | Campo + import PDF |
| **5. Daño detallado** | Piso crítico, % columnas, inclinación, vigas | Campo |
| **6. Daño estructural** | Columnas, vigas, muros, escaleras | Campo |
| **7. Mampostería** | Mecanismo, nivel, diagnóstico | Campo |
| **8. Procedimientos** | Códigos VIG/COL/MAM, viabilidad reparación | Catálogo + inspector |
| **9. Decisión de control** | Estado, decisión D, magnitud M, medidas | Dictamen final |
| **10. Evidencia** | N.º fotos, firmas | Campo |
| **11. Resumen** | Resumen ejecutivo | Inspector / import |

**Caso de referencia:** Residencias Franco Mar (decisión **D3 — Demoler**).

---

## 5. Escala de decisiones D (Fase II)

> **Nota:** Esta escala es propia de la segunda ronda de demolición/verificación ROJO; **no** sustituye el semáforo ANIH de Fase 1.

| Código | Nombre | Cuándo usar |
|--------|--------|-------------|
| **D1** | Complementos requeridos | Información insuficiente; requiere estudios, monitoreo o geotecnia antes de cerrar |
| **D2** | Reparar / reconstruir | Reparación viable; obliga magnitud **M1–M4** |
| **D3** | Demoler | Demolición controlada recomendada |
| **D4** | Escombros / ya colapsado | Edificación colapsada o en fase de retiro de escombros |

### Complementos D1 (obligatorios al enviar a revisión)

Códigos separados por coma: **GEO, ENS, MOD, MON, INV, REI, ALE, OTR**  
Además: **plazo objetivo**, **detalle del entregable** y **medidas inmediatas**.

### Magnitud M (solo D2)

De **M1** (menor intervención) a **M4** (reconstrucción mayor), ordenadas por gravedad ascendente.

---

## 6. Ranking nacional de gravedad

El Excel operativo incluye tres hojas de ranking importables al sistema:

| Hoja | Uso |
|------|-----|
| **Ranking_ROJO_LaGuaira** | Priorización regional La Guaira |
| **Ranking_ROJO_nacional** | Cola nacional completa (~4 200+ casos ROJO) |
| **Ranking_ROJO_Top200** | Subconjunto de máxima urgencia |

**Score de gravedad (0–100):** combina daño estructural, riesgo aledaños, ocupación, evidencia fotográfica y coherencia con Fase 1. Las bandas típicas son *Muy alta*, *Alta*, *Media* y *Baja*.

**Comando de importación:**

```bash
python manage.py importar_ranking --excel cruce-informes-v2.xlsx --hoja Ranking_ROJO_nacional --solo-gps
python manage.py importar_ranking --todas-hojas --solo-gps
```

---

## 7. Import enriquecido desde cruce PDF

Para los **36 informes** ya cruzados con el mart Habitable:

1. Cada PDF se vincula al **hab_id** mediante el CSV de cruce.
2. El sistema **enriquece** automáticamente: fecha visita, evaluadores, GPS, decisión preliminar, hallazgos, medidas, viabilidad reparación y resumen.
3. El PDF original queda como **adjunto** consultable desde la ficha del caso.

```bash
python manage.py cargar_informes_demolicion \
  --carpeta informes-demolicion \
  --csv cruce-informes-demolicion-habitable-2026-08-20.csv \
  --reemplazar-pdf --sobrescribir-campos
```

---

## 8. Catálogo de procedimientos sugeridos

Códigos **VIG** (vigas), **COL** (columnas), **MAM** (mampostería) cargados desde catálogo institucional. El inspector selecciona procedimientos aplicables en sección 8; el revisor valida coherencia con la decisión D.

```bash
python manage.py cargar_catalogo_procedimientos
```

---

## 9. Herramientas del sistema (manual de uso)

| Herramienta | Ruta | Uso |
|-------------|------|-----|
| **Admin casos** | `/admin/inspecciones/casorojo/` | Ficha completa del informe |
| **Tablero asignación** | `/asignacion/` | KPIs, filtros, asignación masiva |
| **Mapa GPS** | `/mapa/` | Visualización geográfica de casos |
| **Export PDF informe** | Botón en ficha del caso | Informe consolidado imprimible |
| **Export Excel** | Informe / lote / selección múltiple | Plantilla vaciado v1.1 (71 columnas) |
| **Health API** | `/api/health/` | Verificación de servicio |

### Guías integradas en pantalla

- **Tutorial del sistema** — recorrido para usuarios nuevos.
- **Sobre esta fase** — contexto D1–D4 y complementos.
- **Guía del informe** — sección por sección.
- **Roles y asignación** — coordinación operativa.
- **Guía desarrolladores** — §10 roadmap técnico (equipo TI).

---

## 10. Plantilla Excel de vaciado

Versión **1.1** · **71 columnas** alineadas a las 11 secciones. Permite:

- **Descarga** desde Admin (un caso, lote filtrado o selección).
- **Validación** de tipos y choices al reimportar (roadmap).

Columnas clave: `hab_id`, `score`, `decision_D`, `magnitud_M`, `complementos_D`, `proc_codigos`, `gps_v2`, `resumen_ejecutivo`.

---

## 11. Infraestructura y continuidad

| Componente | Detalle |
|------------|---------|
| **Stack** | Django 5 · PostgreSQL · Gunicorn · Apache proxy |
| **Servicio** | `fase2-rojo.service` (systemd — reinicio automático) |
| **Estáticos** | Jazzmin + identidad CPEH |
| **Despliegue** | Scripts server-bootstrap vía SSH |

Verificación post-despliegue: `/api/health/` debe responder JSON con estado OK.

---

## 12. Prioridades pendientes (roadmap)

| Prioridad | Tema | Estado |
|-----------|------|--------|
| P1 | Import ranking nacional + PDF enriquecido | ✅ Operativo |
| P2 | Asignación masiva de 4 000+ casos a inspectores reales | ⏳ Pendiente |
| P3 | Import Excel inverso (subir plantilla completada) | ⏳ Diseño |
| P4 | HTTPS / dominio institucional | ⏳ Infraestructura |
| P4 | Documentación y alineación con Habitable | ✅ Este manual |

---

## 13. Contacto y gobernanza

- **Coordinación técnica CPEH:** Ing. Francisco Garcés (referencia mediática).
- **Actores:** CIV, Funvisis, ministerios, universidades, plataforma Habitable.
- **Soporte aplicación:** equipo de desarrollo CPEH / BI Habitable.

---

*Documento para mesas de trabajo, capacitación de inspectores y alineación con Habitable. Actualizar cuando cambien criterios D o plantilla Excel.*
