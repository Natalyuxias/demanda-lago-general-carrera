# Etapa 12 — Antecedente de oferta y demanda desviada

La [Etapa13](../results/demanda_preliminar/RESUMEN_DEMANDA_PRELIMINAR.md) continúa estos resultados con mercados completados bajo supuestos, inducción y anualización. Este documento conserva el escenario y los resultados de12.

Se aplicó el logit jerárquico de11B a la situación base optimizada (SBO) y al proyecto Bahía Jara–Levicán. Se mantienen tierra por Chile y ambos cruces lacustres coexistentes. Los coeficientes siguen siendo supuestos exploratorios y las ASC son constantes calibradas condicionalmente en11B; no se recalibraron al agregar el proyecto.

**Resultado ilustrativo central: el nuevo cruce capta10,15 vehículos livianos por día equivalente para Chile Chico → Coyhaique en verano.** La demanda tiene cobertura parcial y no se ha calculado inducción. No es una proyección anual ni una predicción definitiva de la obra.

## Resultado que puede compartirse

Un solo archivo reúne el ejemplo y todas sus sensibilidades: [ejemplo_vl_verano.csv](../results/etapa12/ejemplo_vl_verano.csv). Filtrar `escenario=central` para consultar el caso principal. Todas las filas pertenecen al mismo OD, sentido, estación y segmento; **no se suman entre escenarios**.

| Alternativa | Probabilidad SBO | Probabilidad con proyecto |
|---|---:|---:|
| Terrestre por Chile | 68,04 % | 60,15 % |
| Barcaza Puerto Ibáñez–Chile Chico | 31,96 % | 24,36 % |
| Bahía Jara–Levicán | No disponible en SBO | 15,48 % |

Mercado total fijo:65,52 vehículos/día equivalente exploratorio. Se obtiene de los flujos de referencia ya divulgados: ferry27,24 + tierra24h de sensibilidad38,29. No es un conteo observado de24h.

| Procedencia de la captación del nuevo cruce | Vehículos/día equivalente |
|---|---:|
| Desde terrestre por Chile | 5,17 |
| Desde barcaza actual | 4,98 |
| Total nuevo cruce | 10,15 |

Se calcula `D_r = D_total × P_r`. La procedencia corresponde a pérdidas netas agregadas entre SBO y proyecto, no al seguimiento de viajeros individuales. No se usaron porcentajes arbitrarios de captación.

## Supuestos que condicionan estos números

- SBO:14 zarpes semanales por sentido diciembre–abril y12 mayo–noviembre, escenario previo `baja_12_alta_14`. Histórica11/8; navegación, accesos y tarifas existentes conservados. Dos naves no duplican demanda.
- Nuevo cruce: P-20a,80min de navegación y14 zarpes semanales por sentido. Es un escenario de diseño con nave adicional independiente de las dos deSBO, no una frecuencia CITRA ni un óptimo económico. Su factibilidad es condicional a ventana12h/día y maniobras0,5h/terminal supuestas; no acredita tripulaciones, mantenimiento, meteo, rampas ni capacidad punta.
- Tarifas nominales de referencia iguales a las existentes; homologación a CLP diciembre2025 heredada11B. Se conservan los mismos supuestos de pagadores y longitudes; no son tarifas nuevas oficiales ni tickets comprobados.
- ASC nueva igual a la barcaza actual; ASC tierra0; lambda0,70 y escala superior1, con `mu_Biogeme=1/lambda`. Se conserva la utilidad con costo, viaje, horario y acceso separados.
- Horario `0,25 × 168/f`; anticipación vehicular2h y desembarque0,5h. Los accesos terrestres completos se suman una vez. El desajuste horario no se interpreta como espera física.

La red da **169,386km terrestres**, frente a162,84km preliminares deEVALSO: el tramo norte desde el anclaje público ARISTO1021 hastaCoyhaique mide121,546km frente a115km de referencia. No se sustituyó la referencia silenciosamente.

CITRA documenta X-763 pavimentada (operación60km/h) y X-735 de ripio con restricciones. Como esas rutas no aparecen como arcos explícitos en el grafoHDM4 actual, el proyecto utiliza segmentos virtuales con longitudes documentales y conexiones intralocales aproximadas. P-20a mejorada a50km/h y costos por tiposHDM4 análogos son supuestos, no estándares de proyecto certificados. Falta confirmar empalmes y terminales exactos.

## Sensibilidades del mismo ejemplo VL

Un factor a la vez; las ASC existentes se mantienen fijas. Los rangos son escenarios, no intervalos de confianza.

| Cambio respecto al central | Captación nueva, vehículos/día equivalente |
|---|---:|
| Central P-20a | 10,15 |
| P-20b / P-20d, solo cambio de longitud norte | 11,17 / 10,92 |
| Frecuencia nueva7 /21 por semana y sentido | 3,38 /13,93 |
| Tarifa nueva−20 % /+20 % | 11,39 /9,01 |
| Lambda0,50 /0,90 | 8,34 /11,66 |
| Diferencia ASC nueva−0,5 /+0,5 | 5,63 /16,90 |

El CSV incluye además navegación, velocidades de acceso, costos operacionales, desembarque ySBO20. Las sensibilidades de buses no modifican este ejemploVL. P-20b/d no constituyen una evaluación completa de esas variantes.

## Qué queda pendiente

La publicación se limita al mercado VL de verano Chile Chico → Coyhaique ya admitido por la regla de divulgación: soporte mínimo de5 entrevistas por alternativa. No se añaden resultados de otras celdas, totales complementarios, probabilidadesCAM ni volúmenes peatonales imputados. El umbral editorial no garantiza anonimato formal. Los parámetros agregados11B previamente compartidos se conservan.

En el cálculo local, CAM no tiene mercado diario homologado y sus resultados de otoño son un contraste mixto tierra10h/ferry diario. El tamaño del mercado peatonal procede de una imputación mediante cuotaVL, no de personas terrestres observadas. Invierno y otros mercados sin total identificado permanecenNaN. Por estas limitaciones, la aplicación está ejecutada pero la cobertura completa de demanda sigue pendiente.

Los logsums del ejemploVL pasan de−2,395569 enSBO a−2,272141 con proyecto, en utilidad normalizada. Su diferencia equivale a6171,44CLP por vehículo bajo beta_c supuesto, no a un beneficio social estimado. El CSV conserva ambos logsums y la medida monetaria. El nivel monetizado incluyeASC y entropía y tiene un origen arbitrario: no aplicar automáticamente cocientes de costos ni elasticidades. **La demanda inducida será una etapa posterior.**

## Código y reproducción técnica

Las entradas completas conservan sus rutas en `outputs/calibracion_logit_11b/`, `outputs/atributos_logit_actualizados/`, `outputs/matrices_od_referencia/`, `outputs/expansion_temporal_terrestre/` y `outputs/sbo_actualizada/`. Los originalesARISTO/CITRA están fuera deGit y se leen sin modificarlos. Para reproducir la aplicación se necesitan esos archivos locales; el material publicado permite consultar el ejemplo y verificar código/pruebas sintéticas.

Configuración: `data/templates/config_etapa12.json`. Aplicación: `scripts/14_aplicar_etapa12.py`. Núcleo: `src/demanda/proyecto.py`.

```bash
# Solo con las entradas completas locales; no recalibra ni reconstruye matrices.
.venv/bin/python scripts/14_aplicar_etapa12.py
# Exporta únicamente la selección revisada desde salidas ya calculadas.
.venv/bin/python scripts/12_preparar_resultados_compartibles.py
# Verifica selección pública y pruebas sintéticas, sin ejecutar la aplicación real.
.venv/bin/python scripts/13_validar_repositorio.py
PYTHONPATH=src .venv/bin/python -m pytest -q
```

La ejecución real conserva hashes de fuentes y resultados previos; reproduce las probabilidades históricas11B antes de cambiar oferta y verifica probabilidades, conservación y captación. Las55 pruebas sintéticas incluyen equivalencia conBiogeme para tres alternativas y distintas lambdas. Las pruebas no son una validación empírica de la predicción.

Los ocho entregables completos, evidencia documental y verificaciones permanecen locales en `outputs/etapa12/`. No se trasladan aGitHub. La selección del único CSV público se reproduce mediante12 y queda registrada por hash en `results/manifest_publicacion.json`;13 comprueba también que no incluya otros mercados y conserve los flujos publicados de referencia.
