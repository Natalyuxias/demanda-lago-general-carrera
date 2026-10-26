# 07. Resultados centrales y límites de interpretación

## Referencia OD compartible

| estacion | origen | destino | ruta | flujo_10h_vehiculos | flujo_diario_equivalente_vehiculos | estado |
| --- | --- | --- | --- | --- | --- | --- |
| Verano | Chile Chico | Coyhaique | barcaza_actual | No publicado / faltante | 27.2381 | expandido_condicional |
| Verano | Chile Chico | Coyhaique | terrestre_chile | 23.179 | 38.2862 | sensibilidad_24h_NO_observado |

No se publican matrices detalladas completas ni controles complementarios que permitan reconstruir celdas reservadas. La selección no mide todos los viajes de la región ni el mercado potencial. Barcaza es demanda atendida histórica, no toda demanda potencial ni SBO.

## Oferta actual entre anclajes, Chile Chico→Coyhaique

| segmento | alternativa | distancia_terrestre_total_km | tiempo_conduccion_terrestre_h | tiempo_navegacion_h | COV_terrestre_privado_ARISTO_CLP |
| --- | --- | --- | --- | --- | --- |
| VL | terrestre_chile | 382.515 | 6.05203 | 0 | 78,538 |
| VL | barcaza_actual | 121.956 | 1.45839 | 2 | 22,135 |
| CAM | terrestre_chile | 382.515 | 7.23201 | 0 | 399,966 |
| CAM | barcaza_actual | 121.956 | 1.98438 | 2 | 97,372 |

COV privado en CLP de diciembre de 2025, tiempo en h y distancia en km. COV no es CG; dinero completo conserva faltantes/condiciones en salida local. Recorridos públicos representativos, no viajes puerta a puerta validados.

## Etapa 11 histórica frente a11B vigente

| segmento | parametro | valor_11 | metodo | valor_11B |
| --- | --- | --- | --- | --- |
| VL | beta_c | -2 e-05 | supuesto | -2 e-05 |
| VL | beta_t | -0.2 | supuesto | -0.2 |
| VL | beta_a | -0.2 | supuesto | -0.3 |
| VL | beta_e | -1.39494 | estimado | -0.3 |
| VL | ASC_barcaza | 4.37425 | calibrado | -0.321915 |
| CAM | beta_c | -2 e-05 | supuesto | -2 e-05 |
| CAM | beta_t | -0.2 | supuesto | -0.2 |
| CAM | beta_e | -0.2 | supuesto | -0.3 |
| CAM | beta_a | -0.2 | supuesto | -0.3 |
| CAM | ASC_barcaza | -4.42184 | calibrado | -3.79334 |
| PEATON | beta_c | -2 e-05 | supuesto | -2 e-05 |
| PEATON | beta_t | -0.2 | supuesto | -0.2 |
| PEATON | beta_e | -0.2 | supuesto | -0.3 |
| PEATON | beta_a | -0.2 | supuesto | -0.3 |
| PEATON | ASC_barcaza | -0.616217 | calibrado | 0.0911272 |

Todas las pendientes11B son supuestos fijados; ASC se recalibra. En11 la pendiente horaria VL se ajustó condicionalmente, pero el intento libre de cinco cantidades fue de rango insuficiente y costo alcanzó frontera. La comparación no significa que hayan cambiado los usuarios: cambia la especificación condicionada.

## Ajuste global de 11B

| segmento | escenario | n_filas | tipo_filas | cuota_objetivo | cuota_predicha | log_likelihood | rho2 | fuente_objetivo |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| VL | central | 61 | encuestas_individuales | 0.229747 | 0.229747 | -31.5885 | 0.0391992 | Misma base/pesos Etapa11; VL 24 h exploratorio |
| CAM | central | 9 | encuestas_individuales | 0.487805 | 0.487805 | -7.20798 | -0.155931 | Misma base/pesos Etapa11; CAM tierra10 h vs ferry diario sin homologacion |
| PEATON | central | 3 | celdas_proxy_VL;NO_personas | 0.229747 | 0.229745 | No publicado / faltante | No publicado / faltante | Objetivos proxy VL 24 h Etapa 11; no cuota de personas |

Los tamaños son entrevistas para VL/CAM y celdas proxy para PEATON. Las cuotas globales se reproducen porque se calibró ASC. No es validación independiente. VL tiene ajuste relativo aproximado0,039 frente a solo ASC(Etapa 11≈0,126); al fijar horario se reduce el ajuste estacional. CAM≈−0,156 ajusta peor que solo ASC bajo las pendientes impuestas. Convergencia numérica no garantiza buen modelo.

## Probabilidades compartibles de barcaza

| origen | destino | estacion | segmento | probabilidad | estado_divulgacion |
| --- | --- | --- | --- | --- | --- |
| Chile Chico | Coyhaique | Verano | VL | 0.268862 | VL_soporte_compartido>=5_por_alternativa |
| Coyhaique | Chile Chico | Primavera | VL | 0.199454 | VL_soporte_compartido>=5_por_alternativa |
| Chile Chico | Coyhaique | Verano | PEATON | 0.273878 | perfil_modelado_con_cuota_proxy_NO_personas_observadas |
| Chile Chico | Coyhaique | Otoño | PEATON | 0.246053 | perfil_modelado_con_cuota_proxy_NO_personas_observadas |
| Chile Chico | Coyhaique | Invierno | PEATON | 0.19709 | perfil_modelado_con_cuota_proxy_NO_personas_observadas |
| Chile Chico | Coyhaique | Primavera | PEATON | 0.19709 | perfil_modelado_con_cuota_proxy_NO_personas_observadas |
| Coyhaique | Chile Chico | Verano | PEATON | 0.273878 | perfil_modelado_con_cuota_proxy_NO_personas_observadas |
| Coyhaique | Chile Chico | Otoño | PEATON | 0.246053 | perfil_modelado_con_cuota_proxy_NO_personas_observadas |
| Coyhaique | Chile Chico | Invierno | PEATON | 0.19709 | perfil_modelado_con_cuota_proxy_NO_personas_observadas |
| Coyhaique | Chile Chico | Primavera | PEATON | 0.19709 | perfil_modelado_con_cuota_proxy_NO_personas_observadas |

Tierra=1−P. PEATON representa un perfil de bus con cuota proxy de VL; no una cuota personal observada. Otras probabilidades, especialmenteCAMpor OD, se reservan al entorno local por soporte reducido. No convertir esas omisiones en cero ni recuperar celdas mediante totales.

## Límites sustantivos

- Encuestas por interceptación no son muestra aleatoria conjunta de elección; expansión/pesos son exploratorios.
- Tierra de 24 h procede de sensibilidad híbrida, no perfil de 24 h comparable medido. CAM usa10 h frente ferry diario.
- El soporte de calibración no incluye todas las estaciones/OD; invierno es extrapolación de oferta, no demanda observada.
- Usuarios de barcaza no equivalen a demanda potencial, rechazados o inducidos. No se duplican viajes al agregar una nave.
- La constante absorbe atributos omitidos y supuestos: no extrapolarla como gusto puro del usuario.
- Datos agregados y publicaciones compartibles no reemplazan la base individual de estimación ni autorizan redistribuir originales.
- Accesos, tarifas efectivas, longitudes facturables, horarios deseados, modos y costos completos todavía tienen incertidumbre.
- Lambda y ASC del nuevo cruce no se identifican históricamente. La [Etapa12](10_etapa12.md) aplica estos parámetros a Bahía Jara–Levicán bajo supuestos explícitos; las tablas de este documento conservan la referencia11B.

Archivos principales: [parámetros](../results/calibracion_logit/parametros_centrales_11b.csv), [probabilidades seleccionadas](../results/calibracion_logit/probabilidades_11b_divulgacion.csv), [sensibilidades](../results/sensibilidades/), [comparación11](../archive/results/etapa11/parametros_centrales.csv). La información reservada conserva su ubicación local en `outputs/` y no se perdió.
