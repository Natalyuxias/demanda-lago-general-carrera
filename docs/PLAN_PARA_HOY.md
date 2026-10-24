# Plan de trabajo — estimación preliminar, sábado 24/10/2026

## Alcance de lo que sí puede entregarse hoy

- Tabla de viajes muestrales de ARISTO por OD × temporada × segmento × evidencia de uso de barcaza (SIN expansión).
- Tabla de conteos de la barcaza por fecha, sentido y vehículo/persona, con exposición y número de zarpes **verificados o desconocidos**.
- Si el marco de expansión puede verificarse: flujo del cruce actual por sentido, segmento y temporada; con bandera de calidad.
- Escenarios de **desviación desde el cruce actual** (10/25/50 %) sobre flujos diarios validados o proxies explícitamente identificados. NO equivalen a captación completa del proyecto.
- Demanda terrestre elegible, inducida y total anual solo si hay evidencia o se reportan como escenarios condicionales con valores de entrada y procedencia claros.

## Primeros 90 minutos
1. Crear repo Git privado y copiar este kit. Con Codex CLI local: `codex` desde raíz.
2. Ejecutar `01_auditar_eod.py`. Verificar que existan 18.529 válidos y 264 del cruce. Si no cuadran, revisar las columnas antes de seguir.
3. Extraer solamente estratos de ARISTO transbordador por fecha, sentido y tipo de usuario y cotejar con `Consolidado Flujos.xlsx / Transbordadores`.
4. Completar `data/templates/flujos_base.csv` SOLO cuando esté clara la unidad de flujo/día y alcance. Si hay incertidumbre, marcar `supuesto` y describir explícitamente la regla.
5. Ejecutar `02_escenarios_demanda.py`; revisar salidas y no reportar total nuevo si falta tierra elegible.

## Entregables de esta jornada
`outputs/tables/control_eod.csv` — control de integridad, no demanda.
`outputs/tables/od_muestral_prueba.csv` — muestra local, no expandida.
`outputs/tables/escenarios_captacion.csv` — escenario de traslado con supuestos explícitos, si hay flujos de entrada.
`docs/bitacora_decisiones.md` — valores, fuentes y limitaciones.

## Pendientes para el lunes
- A SECTRA Austral: estado y posibilidad de obtener microdatos EOD Coyhaique 2025, encuesta en vía pública y bases anonimizadas, incluyendo expansión.
- A contraparte/ARISTO: protocolo de expansión EOD, días/zarpes muestreados, temporada, registros de capacidad/rechazos y tarifa histórica.
- A CITRA: microdatos por encuestado, puntos y momentos, si están disponibles.

## Criterio de honestidad técnica
Si no se verifica una tasa de expansión (o equivalencia por zarpe), NO convertir los 264 encuestados en demanda diaria. Si falta demanda terrestre, nunca escribir que es cero; reportar solo captación lacustre parcial.
