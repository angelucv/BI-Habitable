"""Guía didáctica del modelo de valoración PDNA (qué calibrar)."""

from __future__ import annotations

import streamlit as st

from ui_theme import render_section


def render_guia_modelo_valoracion(*, embebida: bool = False) -> None:
    """Explicación didáctica: lógica del modelo y parámetros a calibrar."""
    if embebida:
        st.markdown("##### Guía del modelo de valoración")
        st.caption(
            "Qué calcula el modelo, qué premisa viene de datos y qué debe calibrar el equipo sectorial."
        )
    else:
        render_section(
            "Guía del modelo de valoración",
            "Qué calcula el modelo, qué premisa viene de datos y qué debe calibrar el equipo sectorial.",
        )

    st.info(
        "Los números del panel **Configuración del Modelo de Valoración** no son «la verdad» "
        "del PDNA: son **premisas editables**. Esta guía indica cuáles conviene acordar con "
        "ingeniería de costos / vivienda antes de usar la matriz como insumo ONU."
    )

    st.markdown("##### 1. Flujo del cálculo (de lo físico a lo monetario)")
    st.markdown(
        """
<div class="pdna-flow">1) Área estimada (m²)  =  max( pisos × m² por piso , área mínima )
2) Valor de reposición de la vivienda (USD)  =  Área × USD/m² del material
3) Inventario de contenidos (USD)  =  Valor vivienda × (% contenidos)
4) Daño físico infraestructura  =  Valor vivienda × min(factor semáforo, 1.0)
5) Daño a contenidos  =  Inventario × factor contenidos del semáforo
6) Daño físico directo  =  (4) + (5)
7) Necesidades de recuperación  =  Valor vivienda × factor semáforo  +  (5)
   └─ si factor Negro &gt; 1, el exceso es la prima Build Back Better (BBB)</div>
""",
        unsafe_allow_html=True,
    )
    st.caption(
        "Los conteos por tipología y semáforo salen de las inspecciones Habitable. "
        "Los USD salen de aplicar las premisas de arriba a cada unidad."
    )

    st.markdown("##### 2. Qué calibrar vs qué no tocar a la ligera")
    st.markdown(
        """
<div class="pdna-guide-grid">
  <div class="pdna-guide-card calibrar">
    <div class="pdna-guide-tag calibrar">Calibrar con expertos</div>
    <h4>USD/m² por material</h4>
    <p>Costo de reponer 1 m² según tipología constructiva (concreto, acero, mampostería formal/informal).
    Debe reflejar precios locales de reconstrucción, no el valor catastral histórico.</p>
    <ul>
      <li>Fuente típica: cámaras de construcción, presupuestos MOP/vivienda, PDNA sectoriales previos.</li>
      <li>Impacto: mueve casi en proporción todos los totales en USD.</li>
    </ul>
  </div>
  <div class="pdna-guide-card calibrar">
    <div class="pdna-guide-tag calibrar">Calibrar con expertos</div>
    <h4>m² por piso y área mínima</h4>
    <p>Como Habitable no trae área construida fiable en todas las fichas, el modelo estima
    superficie = pisos × m²/piso (con piso mínimo).</p>
    <ul>
      <li>Calibrar con tipología local (casa popular vs edificio).</li>
      <li>Si más adelante hay área real, se puede sustituir esta estimación.</li>
    </ul>
  </div>
  <div class="pdna-guide-card calibrar">
    <div class="pdna-guide-tag calibrar">Calibrar (juicio sectorial)</div>
    <h4>Factores de daño en vivienda (V / A / R / N)</h4>
    <p>Fracción del valor de reposición que se considera dañada según el semáforo de la inspección.</p>
    <ul>
      <li>Verde bajo (p. ej. 2 %): daños menores / cosméticos.</li>
      <li>Amarillo / Rojo: reparación parcial o mayor.</li>
      <li>Negro &gt; 1 (p. ej. 1,15): pérdida total + mejora BBB.</li>
    </ul>
  </div>
  <div class="pdna-guide-card calibrar">
    <div class="pdna-guide-tag calibrar">Calibrar (juicio sectorial)</div>
    <h4>Contenidos: % inventario y factores</h4>
    <p>El inventario se estima como % del valor de la vivienda; luego se aplica pérdida por color.</p>
    <ul>
      <li>% contenidos: suele situarse entre 10 % y 30 % según nivel de amueblamiento.</li>
      <li>Factores contenidos: en pérdida total suele ser 1,0 (100 %).</li>
    </ul>
  </div>
  <div class="pdna-guide-card fijo">
    <div class="pdna-guide-tag fijo">No es un “precio” a inventar</div>
    <h4>Conteos por tipología × semáforo</h4>
    <p>Salen del mart de inspecciones (unidades físicas). Se filtran por territorio y esquema de tipologías.</p>
    <ul>
      <li>Calibración aquí = calidad de datos / tipología, no un número a mano en el panel.</li>
    </ul>
  </div>
  <div class="pdna-guide-card fijo">
    <div class="pdna-guide-tag fijo">Resultado, no premisa</div>
    <h4>KPIs y matriz en USD</h4>
    <p>Daño físico, contenidos y necesidades de recuperación son <strong>salidas</strong> del modelo.
    No se editan: cambian al mover las premisas de arriba.</p>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown("##### 3. Lectura PDNA de los cuatro KPIs")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            """
| KPI | Significado |
|-----|-------------|
| **Unidades físicas** | Muestra cuantificada (inspecciones con tipología). |
| **Daño físico (infraestructura)** | Efecto monetario en la estructura, sin prima BBB. |
| **Daño a contenidos** | Mobiliario y enseres. |
| **Necesidades de recuperación** | Cifra para donantes: incluye BBB si el factor &gt; 1. |
            """
        )
    with c2:
        st.markdown(
            """
**Daño físico directo** (síntesis) = infraestructura + contenidos (sin BBB).

**Necesidades totales** = lo anterior + prima de reconstrucción mejorada
(*Build Back Better*), típica en Negro cuando el factor es 1,15.

La diferencia entre ambas es el “extra” de resiliencia, no un error de suma.
            """
        )

    st.markdown("##### 4. Checklist práctico de calibración")
    st.markdown(
        """
1. Acordar **USD/m²** por material con el equipo de costos / vivienda (prioridad 1).  
2. Revisar **m² por piso** y **área mínima** con tipólogos locales.  
3. Validar **factores por semáforo** con criterios de reparación vs demolición.  
4. Ajustar **% contenidos** según perfil socioeconómico del parque afectado.  
5. Correr sensibilidad (“estresár” el modelo) y comparar la matriz exportada.  
6. Congelar premisas y documentarlas en la nota metodológica del PDNA sectorial.
        """
    )

    st.warning(
        "Hasta que las premisas estén validadas por el sector, los USD deben presentarse como "
        "**estimación preliminar / escenario de trabajo**, no como cifra oficial de movilización."
    )

    with st.expander("Ejemplo numérico rápido (una vivienda)", expanded=False):
        st.markdown(
            """
Suponga una casa de **concreto**, **2 pisos**, etiqueta **Rojo**:

- Área = 2 × 80 = **160 m²** (si el mínimo es 40, no cambia)  
- Valor reposición = 160 × 450 = **USD 72.000**  
- Contenidos (20 %) = **USD 14.400**  
- Daño infraestructura (factor 0,65) = 72.000 × 0,65 = **USD 46.800**  
- Daño contenidos (factor 0,80) = 14.400 × 0,80 = **USD 11.520**  
- Daño físico directo = **USD 58.320**  
- Necesidades (mismo factor 0,65 &lt; 1) = **USD 58.320**  

Si fuera **Negro** con factor 1,15:

- Daño infraestructura directo = 72.000 × 1,00 = **USD 72.000**  
- Prima BBB = 72.000 × 0,15 = **USD 10.800**  
- Necesidades vivienda = 72.000 × 1,15 = **USD 82.800** (+ contenidos)
            """
        )
