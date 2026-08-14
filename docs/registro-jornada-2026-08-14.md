# Registro de jornada — BI Habitable · 2026-08-14

**Equipo:** Laptop (perfil Windows `PC`)  
**Alcance:** tablero Streamlit **BI Habitable** (PDNA + análisis dimensional)  
**Prod:** https://bi-habitable.onrender.com · GitHub `angelucv/BI-Habitable` **`6998418`**

## Resumen

Se consolidó el frente **PDNA / salidas CPEDHI→PNUD** y se refinó el **análisis dimensional**, con verificación local y **deploy a Render** el mismo día.

## Hecho

### PDNA — salidas y valoración

- Pestaña **Análisis 2.º nivel**: matriz territorio × tipología × pisos × estratificación (estilo Excel DataAnálisis 2.º nivel), gráficos interactivos, descarga Excel (larga + ancha) y CSV.
- Estratificación: rojas (externo / estructural / no estructural), amarillas c/s daño estructural, verde, pérdida total; elementos Columnas/Muros/Vigas.
- Quitada la narrativa larga tipo informe PNUD; solo KPIs de estratificación no repetidos en otras vistas.
- **Guía de salidas** (tarjetas de lectura) alineada a reportes nacionales / 2.º nivel.
- Panel de parámetros: explicación didáctica + **bandas recomendadas** (USD/m², m²/piso, factores V/A/R/N, % y factores contenidos).
- Montos USD en matriz y territorio con **separador de miles** (es-VE).
- Esquema tipológico **Ampliado** por defecto; Excel físico sin costos; gráficos por banda.

### Análisis dimensional

- Orden de menú: Año → Pisos → Uso → Material → Flujo (Flujo al final).
- Año: % pérdida **año a año** (no quinquenio).
- Pisos: texto didáctico antes de métricas de pruebas.
- Uso agrupado: filtro cruzado por **material** (no por uso).
- Filtro **Parroquia** en cascada Estado → Municipio → Parroquia.

### Ops

- Commits en `main` (serie del día; cierre `6998418`).
- Deploy automático Render confirmado (Last-Modified actualizado ~11:54).

## Referencias de trabajo (internas)

- Insumos de diseño: Excel nivel nacional A+R, DataAnálisis 2.º nivel, informe CPEDHI→PNUD (corte 13/08).
- Módulo nuevo: `src/pdna_salidas.py`; cambios en `page_pdna.py`, `nav_schema.py`, `app.py`, dimensional / filtros.

## Pendiente / siguiente

- Calibrar premisas USD con equipo de costos / sala situacional si se usa como cifra de movilización.
- Opcional: alinear tipología/reglas 1:1 con el Excel externo si hay deltas de conteo.
- Sync Drive: empujar docs **D-CPEH** + **instrucciones-cursor** (ver aviso multi-equipo).

## Handoff

- Aviso: `AVISO-LAPTOP-A-PC-BI-HABITABLE-2026-08-14.md`
- REGISTRO: `REGISTRO-AVANCES-MULTI-CLIENTE-2026-08-14.md`
- AGENTS: `BI-Habitable/AGENTS.md` · `comision-presidencial-habitabilidad/AGENTS.md`
