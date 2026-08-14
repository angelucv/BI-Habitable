# BI Habitable

Tablero analítico (Streamlit) para las **inspecciones de habitabilidad** del sistema Habitable, en el marco de la **Comisión Presidencial para la Evaluación de Habitabilidad (CPEH)** tras el sismo de junio de 2026 en Venezuela.

Este repositorio concentra la aplicación **BI Habitable**: panorama ejecutivo, análisis dimensional (flujo ANIH, año, pisos, uso, material), estimación **PDNA** (matriz tipología × semáforo y costos), exploración libre con Perspective, depuración de datos y carga del CSV de inspecciones.

**Repositorio:** [https://github.com/angelucv/BI-Habitable](https://github.com/angelucv/BI-Habitable)

---

## Índice

1. [Para quién es](#1-para-quién-es)
2. [Qué problema resuelve](#2-qué-problema-resuelve)
3. [Mapa de pantallas](#3-mapa-de-pantallas)
4. [Funcionalidades en detalle](#4-funcionalidades-en-detalle)
5. [Modelo de datos (mart)](#5-modelo-de-datos-mart)
6. [Modelo de valoración PDNA](#6-modelo-de-valoración-pdna)
7. [Arquitectura del código](#7-arquitectura-del-código)
8. [Requisitos e instalación](#8-requisitos-e-instalación)
9. [Cómo ejecutar](#9-cómo-ejecutar)
10. [Cargar o actualizar datos](#10-cargar-o-actualizar-datos)
11. [Cómo aportar](#11-cómo-aportar)
12. [Alcance y límites](#12-alcance-y-límites)

---

## 1. Para quién es

| Perfil | Uso típico |
|--------|------------|
| **Coordinación / gerencia** | Inicio: KPIs nacionales, semáforo, distribución por estado |
| **Analistas estructurales / ANIH** | Análisis dimensional: embudo de decisión, año, pisos (resonancia), uso y material |
| **Equipo PDNA / ONU / costos** | Matriz agregada tipología × semáforo, costos en USD, guía de calibración |
| **Calidad de datos** | Depuración: posibles duplicados y conflictos de semáforo |
| **Desarrollo** | Carga CSV → mart Parquet; extensión de capas y parámetros |

---

## 2. Qué problema resuelve

1. **Traducir** decenas de miles de inspecciones Habitable a un lenguaje de negocio (semáforo, tipologías, territorio).
2. **Explorar asociación** entre características de la edificación (año, altura, uso, material) y daño crítico (rojo + pérdida total), sin saturar la vista con jerga estadística.
3. **Generar insumos PDNA** del sector vivienda: matriz física + estimación monetaria parametrizable (daño infraestructura, contenidos, necesidades con *Build Back Better*).
4. **Auditar** coherencia espacial (mismo lugar con etiquetas distintas).

El corte de referencia incluido en `data/processed/` ronda **~58.000 inspecciones** (ver `summary.json`).

---

## 3. Mapa de pantallas

```
BI Habitable
├── Inicio                         Panorama nacional
├── Análisis dimensional
│   ├── 1 · Flujo de decisión      Embudo / Sankey ANIH
│   ├── 2 · Año de construcción    Décadas / quinquenios + heatmaps
│   ├── 3 · Número de pisos        Bandas de altura (resonancia)
│   ├── 4 · Uso agrupado           Capas nominales (KPIs de negocio)
│   └── 5 · Material agrupado
├── PDNA
│   ├── Matriz y costos            Insumo agregado + parámetros
│   └── Guía del modelo            Qué calibrar (didáctica)
├── Explorar / cruces
│   └── Perspective                Pivotes y gráficos libres
├── Depuración de datos
│   └── Auditoría de multiplicidad
└── Cargar información
    └── Cargar CSV                 Ingesta → mart
```

La navegación vive en `src/nav_schema.py` y se renderiza en barra lateral (`src/ui_theme.py`).

---

## 4. Funcionalidades en detalle

### 4.1 Inicio (vista ejecutiva)

- KPIs de volumen y semáforo (Verde / Amarillo / Rojo / **Negro = Pérdida total**).
- Distribución por estado y gráficos de uso / material.
- Pensada para lectura rápida de gerencia: **sin** rutas técnicas ni metadata de pipeline en pantalla.

Archivo principal: `src/page_ejecutivo.py`.

### 4.2 Análisis dimensional

Selector tipo “pastillas” 1–5 (`src/page_analisis_dimensional.py`).

#### Flujo de decisión (ANIH)

- Embudo y Sankey del recorrido de la planilla (salidas tempranas legítimas vs pasos de daño).
- KPIs de terminación temprana y síntesis en lenguaje de negocio.
- Lógica: `src/anih_logic.py` + pestaña en `src/page_ejecutivo.py` / dimensional.

#### Año de construcción

- Bandas temporales vs daño crítico.
- Heatmaps año × uso / ubicación: escala global o por fila; celdas con muestra insuficiente marcadas.
- `src/page_dimension_anio.py`, `src/analisis_temporal_anio.py`.

#### Número de pisos (resonancia)

- Bandas de altura: Baja (1–3), Media-Baja (4–8), Media-Alta (9–12), Alta (13+).
- Contrastes relativos vs banda baja (OR), sin imponer tendencia lineal forzosa.
- `src/page_dimension_pisos.py`, `src/stats_asociacion.py`.

#### Uso y material (nominal)

- Capas agrupadas (Casa, Edificio/Multifamiliar, … / Concreto, Acero, Mampostería, …).
- **KPIs de negocio** en la franja superior: inspecciones, tasa de falla, grupo más vulnerable / más seguro, factor de brecha.
- Estadística técnica (V de Cramer, χ², OR) **solo** en expander de auditoría.
- Síntesis ejecutiva automática (escenarios base ≠ peor / base = peor).
- `src/page_dimension_nominal.py`, `src/analisis_nominal.py`, `src/clean_catalog.py`.

### 4.3 PDNA (Post-Disaster Needs Assessment)

Alineado a la lógica de **efectos en activos físicos** (PDNA Volume A) y a la plantilla sectorial “por estado” (tipología × semáforo × costos).

#### Matriz y costos

- Filtro territorial (estado / municipio).
- **Esquemas de tipología** (bandas de pisos configurables):
  - Plantilla sectorial (12 tipologías).
  - Ampliado: más bandas de pisos.
  - Dinámico: solo combinaciones presentes en el corte.
- KPIs PDNA: unidades físicas, daño infraestructura, daño contenidos, **necesidades de recuperación (BBB)**.
- Síntesis narrativa automática (executive summary).
- Matriz agregada con *data bars* y **export CSV solo agregado** (insumo para el equipo ONU/PDNA).
- Parámetros de valoración en accordion **cerrado por defecto**.

#### Guía del modelo

- Flujo del cálculo paso a paso.
- Qué **calibrar** (USD/m², m²/piso, factores semáforo, contenidos) vs qué son salidas.
- Checklist y recorrido numérico de una vivienda.

Archivos: `src/page_pdna.py`, `src/page_pdna_guia.py`, `src/pdna_costs.py`, tipologías en `src/process_habitable.py`.

### 4.4 Explorar (Perspective)

- Cruces libres: el usuario arma tablas y gráficos con variables tipificadas (año, pisos, uso, material, semáforo).
- `src/page_explorar_perspective.py`.

### 4.5 Depuración

- Posibles duplicados por vecindad GPS + similitud de nombre.
- Alerta crítica si el mismo posible caso tiene **semáforos distintos**.
- `src/page_depuracion.py`, `src/depuracion_datos.py`, `src/audit_fuzzy.py`.

### 4.6 Carga de información

- Subida de CSV Habitable → normalización de semáforo, territorio, catálogos de uso/material, tipología PDNA, relleno tipado de nulos.
- Persistencia en `data/processed/inspecciones_habitable.parquet` + `summary.json`.
- `src/page_carga.py`, `src/process_habitable.py`.

---

## 5. Modelo de datos (mart)

Tras la carga, cada fila es una inspección enriquecida. Campos clave (no exhaustivo):

| Campo | Rol |
|-------|-----|
| `etiqueta_n` | Semáforo canónico: `VERDE`, `AMARILLO`, `ROJO`, `NEGRO` |
| `estado_n`, `municipio_n`, `parroquia_n` | Territorio normalizado |
| `uso_n`, `material_n` | Catálogos limpios |
| `num_pisos`, `anio_construccion_n` | Estructura / edad |
| `tipologia_pdna` | Material × casa/edificio × banda de pisos |
| `lat`, `lng` | Geo (si válida) |

Metadatos del corte: `data/processed/summary.json`.

**Semáforo en UI:** `NEGRO` se muestra como **Pérdida total** (`etiqueta_display` en `process_habitable.py`).

---

## 6. Modelo de valoración PDNA

### Idea central

1. Estimar **área** ≈ `max(pisos × m²/piso, área mínima)`.
2. **Valor de reposición** = área × USD/m² del material.
3. **Contenidos** = valor vivienda × (% inventario).
4. **Daño infraestructura** = valor × `min(factor_semáforo, 1)` (daño físico directo).
5. **Daño contenidos** = inventario × factor de contenidos.
6. **Necesidades de recuperación** = valor × factor_semáforo + daño contenidos  
   (si el factor &gt; 1, el exceso es prima *Build Back Better*).

Los conteos por tipología y color salen de los datos; los USD dependen de **premisas calibrables** (ver Guía del modelo en la app). Hasta validación sectorial, presentar cifras como **escenario de trabajo**, no como movilización oficial.

---

## 7. Arquitectura del código

```
bi-habitable/
├── app.py                 # Entrada Streamlit + enrutado por nav_item
├── requirements.txt
├── .streamlit/config.toml
├── data/
│   ├── processed/         # Mart Parquet + summary.json
│   └── uploads/           # CSV subidos (ignorados por git salvo .gitkeep)
├── scripts/               # Utilidades auxiliares (si aplica)
└── src/
    ├── nav_schema.py      # Menú
    ├── ui_theme.py        # CSS ejecutivo, KPIs, nav
    ├── process_habitable.py
    ├── page_*.py          # Pantallas
    ├── pdna_costs.py      # Motor PDNA
    ├── analisis_*.py      # Motores analíticos
    ├── charts_habitable.py
    └── ...
```

- **UI:** Streamlit + ECharts (`streamlit-echarts`) + Perspective.
- **Idioma:** español (es-VE) en etiquetas y textos de negocio.
- **Estilo:** presentación ejecutiva (evitar jerga ETL/HTTP en pantallas de gerencia).

---

## 8. Requisitos e instalación

- Windows / macOS / Linux
- **Python 3.11+** recomendado (probado en entornos 3.12–3.14)
- Git

```powershell
git clone https://github.com/angelucv/BI-Habitable.git
cd BI-Habitable

python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Windows PowerShell
# source .venv/bin/activate           # Linux / macOS

python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 9. Cómo ejecutar

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8825
```

Abrir: [http://localhost:8825](http://localhost:8825)

Si el puerto está ocupado, use otro (`8826`, `8827`, …). En este proyecto suele preferirse **puerto nuevo** al iterar para no confundir caché de sesión.

Configuración Streamlit: `.streamlit/config.toml`.

---

## 10. Cargar o actualizar datos

1. En la app: **Cargar información → Cargar CSV**.
2. Suba el export Habitable (CSV UTF-8).
3. El sistema escribe:
   - `data/processed/inspecciones_habitable.parquet`
   - `data/processed/summary.json`

Sin mart, las pantallas de análisis muestran aviso para cargar datos. El repositorio puede incluir un mart de referencia para pruebas; **reemplácelo** con el corte oficial de su equipo.

Columnas críticas esperadas (entre otras): `etiqueta`, `material`, `uso`, `num_pisos`, `anio_construccion`, territorio, coordenadas, campos de daño ANIH según export Habitable.

---

## 11. Cómo aportar

1. Cree una rama desde `main`.
2. Mantenga textos de UI en **español de negocio**; reserve Cramer/χ²/OR a expanders técnicos.
3. En PDNA, no reexponer microdato de 50k filas como export principal: la matriz **agregada** es el insumo.
4. No commitear `.venv/`, `.env`, ni CSV crudos en `data/uploads/`.
5. Pruebe localmente con `streamlit run` y un corte pequeño si itera tipologías.
6. Abra un Pull Request describiendo: pantalla afectada, supuesto de negocio y cómo probar.

### Convenciones útiles

- Nuevas rutas de menú → `nav_schema.py` + `app.py`.
- Nuevos KPIs → `render_kpi_strip` en `ui_theme.py`.
- Tipologías PDNA / bandas de pisos → `process_habitable.py` (`tipologia_pdna`, esquemas).

---

## 12. Alcance y límites

**Incluye**

- Análisis descriptivo y de asociación sobre inspecciones Habitable.
- Estimación PDNA de **efectos en vivienda + contenidos** con parámetros editables.
- Herramientas de calidad (duplicados / conflicto de semáforo).

**No sustituye**

- Avalúo de campo ni presupuesto oficial de reconstrucción.
- PDNA completo (pérdidas de producción, macroeconomía, estrategia de recuperación multi-sector).
- El sistema operativo CPEH de capacitación/inscripción (otro producto del ecosistema).

---

## Contacto y contexto

- Trabajo analítico asociado al ecosistema CPEH / Habitable.
- Contacto técnico de referencia del repositorio: issues en GitHub.

---

## Licencia y datos

Los datos de inspecciones pueden contener información sensible operativa. Distribuya cortes solo por canales autorizados por la Comisión / entidades responsables. Este código se publica para facilitar la colaboración técnica del equipo; respete las políticas de datos de su organización.
