# Registro de jornada — BI Habitable / demolición 2.ª ronda — 2026-08-20

## Contexto

Segunda ronda de verificación sobre etiquetas **ROJO** (demolición vs reparación), a partir de un lote de informes PDF detallados y el export Habitable del **20/08/2026**.

## Hecho

1. Extracción y cruce de ~36 PDF (carpeta Edificios Demolición) × Habitable (~60k filas; ~9.270 ROJO).
2. Score de gravedad 0–100 + bandas; Word de criterios didáctico con ejemplos.
3. Formato propuesto de inspección detallada (Word): precarga Fase 1 + ranking, D1–D5, M1–M4, anexo Franco Mar.
4. Excel operativo consolidado: Indice, Resumen, Cruce_informes, **Ranking_ROJO** (único, filtrable), Control_2da_ronda, Catalogo_campos.
5. Excel didáctico aparte: vaciado digital ejemplo Franco Mar + plantilla (acompaña el Word de formato).
6. Paquete a remitir Habitable documentado (4 archivos).

## Entregables (paquete Habitable)

| Archivo | Rol |
|---------|-----|
| Formato propuesto inspeccion detallada verificacion ROJO.docx | Modelo 2.ª visita |
| Criterios score gravedad etiquetas ROJAS.docx | Ranking / prioridad |
| Ejemplo vaciado digital inspeccion 2da ronda Franco Mar.xlsx | Vaciado digital de ejemplo |
| cruce-informes-demolicion-habitable-2026-08-20.xlsx | Listado + ranking + control |

Carpeta: `BI-Habitable/docs/demolicion-ronda2/`

## Pendiente

- Validación de matches dudosos PDF↔Habitable.
- Recalibrar score cuando existan dictámenes D1/D2 de campo.
- Decisión de producto (formulario web/app) a partir del Excel ejemplo.
