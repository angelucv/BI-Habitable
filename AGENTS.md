# AGENTS — BI Habitable (Streamlit / PDNA)

**Repo:** https://github.com/angelucv/BI-Habitable (`main`)  
**Prod:** https://bi-habitable.onrender.com  
**Local:** `clients/comision-presidencial-habitabilidad/BI-Habitable`  
**Padre CPEH:** `../AGENTS.md` · `../docs/ESTADO-PROYECTO-Y-SYNC.md`

## Qué es

Tablero Streamlit sobre el mart de inspecciones Habitable (~58k en corte 13/08/2026): ejecutivo, análisis dimensional (ANIH), **PDNA** (matriz tipología × semáforo + costos), análisis 2.º nivel, Perspective, depuración y carga CSV.

**No confundir** con:

| Proyecto | URL / repo |
|----------|------------|
| CPEH web (Django) | https://cpeh-web.onrender.com |
| Habitable 1×10 / cruce histórico | https://habitable.onrender.com · `angelucv/habitable` |
| Nube MINCYT | GitLab `sismo` / `habitabilidad-1-10-nube-local` |

## Stack

Python · Streamlit · Pandas/Parquet · ECharts · Perspective · deploy Render (`Dockerfile` + `render.yaml`)

## Avance reciente (agentes)

| Fecha | Tema | Git |
|-------|------|-----|
| **14/08/2026** | PDNA: análisis 2.º nivel (matriz + gráficos + Excel); guía parámetros con bandas; USD con miles; dimensional (parroquia, uso×material, % año a año, Flujo al final). **En prod.** | `6998418` (+ commits del día) |
| **13–14/08** | PDNA Ampliado por defecto; Excel físico sin costos; gráficos por banda; Dockerfile/Render | `eb26f39` … `8256f0a` |

## Reglas de trabajo

- Tras cambiar UI: levantar Streamlit en **puerto nuevo** (regla global).
- Montos en pantalla: formato es-VE (`fmt_es_money` / `fmt_es_int`).
- Premisas PDNA = editables; presentar USD como estimación hasta calibración sectorial.
- Código versionado en GitHub; docs multi-equipo vía `instrucciones-cursor` + espejo **D-CPEH**.

## Registro

- Jornada: `docs/registro-jornada-2026-08-14.md`
- Multi-cliente: `instrucciones-cursor/REGISTRO-AVANCES-MULTI-CLIENTE-2026-08-14.md`
- Aviso handoff: `instrucciones-cursor/AVISO-LAPTOP-A-PC-BI-HABITABLE-2026-08-14.md`
