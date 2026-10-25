# 02. Matrices OD de referencia

## Territorio y clasificación

Prioridad: Chile Chico↔Coyhaique y Chile Chico↔Puerto Ibáñez. No toda la región ni OD interregionales. Se conserva Río Ibáñez como comuna si no hay evidencia para resolver localidad. Las menciones textuales EOD pueden resolver Puerto Ibáñez; no se impone el centroide comunal como localidad.

Ruta confirmada por cruce: interceptación Puerto Ibáñez–Chile Chico. Tierra por Chile: declaración explícita de ningún transbordador y ninguna frontera, con control terrestre chileno compatible. Ser interceptado en carretera o declarar solo no uso de barcaza no demuestra itinerario por Chile. País/ruta desconocidos y Argentina se mantienen separados, sin redistribuirlos. Argentina no participa en11/11B.

## Expansión y unidades

Barcaza: media por fila/zarpe del conteo compatible × frecuencia ordinaria semanal/7. Distribuir dentro de sentido/campaña/segmento por participación muestral compatible: `Q_OD=Q_cruce*n_OD/N_estrato`. Las sumas y el flujo sin OD conservan el total. Media por fila como zarpe es una hipótesis documentada por campaña, no cobertura de todos los zarpes operados.

Tierra: usar solo Cerro Castillo para no sumar controles del mismo recorrido. Dentro de campaña/sentido/clase: `f=(conteo_clase/numero_jornadas)/encuestas_validas_estrato`; `Q_OD_10h=f*n_OD_ruta`. El marco temporal debe coincidir. No se asigna el flujo total del corredor a Chile Chico–Coyhaique. Los factores de arcos agregados de ARISTO no son por sí solos ponderadores de inclusión individuales.

Separar vehículos VL, carga CAM y personas PEATON. No multiplicar encuestas por tamaño de grupo ni sumar pasajeros de vehículos nuevamente como peatones. No transformar un dato faltante en cero.

## Ejemplo compartible, extraído sin recalcular

| estacion | origen | destino | ruta | flujo_10h_vehiculos | flujo_diario_equivalente_vehiculos | estado |
| --- | --- | --- | --- | --- | --- | --- |
| Verano | Chile Chico | Coyhaique | barcaza_actual | No publicado / faltante | 27.2381 | expandido_condicional |
| Verano | Chile Chico | Coyhaique | terrestre_chile | 23.179 | 38.2862 | sensibilidad_24h_NO_observado |

Barcaza: promedio diario equivalente. Tierra10 h: jornada medida;24 h: sensibilidad del paso 08. Las dos cifras no tienen igual estatus estadístico. No es TMDA ni total anual.

## Cobertura y conservación

Verano/primavera tienen campañas, Normal corresponde a mayo; no representa marzo/abril ni invierno. Las frecuencias se mantienen mensuales11diciembre–abril y8 mayo–noviembre. Sin perfil suficiente no se completa silenciosamente una estación.

Las matrices completas y balances están en `outputs/matrices_od_referencia/`, locales: matriz_od_barcaza.csv, matriz_od_terrestre.csv, matriz_od_desconocidos.csv, matriz_od_consolidada.csv; conservación de flujos y controles separados. Permanecen sin modificación.

La selección `results/matrices_od/matriz_vl_divulgacion.csv` NO reproduce toda la matriz local. Se limita al ejemplo de soporte suficiente; otras celdas se reservan, incluidas complementarias para evitar reconstrucción algebraica mediante totales. El umbral editorial de 5 encuestas por alternativa no es garantía formal de anonimato. Los resultados completos requieren acceso autorizado al entorno local.
