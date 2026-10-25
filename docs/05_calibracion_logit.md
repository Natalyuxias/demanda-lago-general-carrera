# 05. Especificación, estimación y recalibración

Informe 2 EVALSO local §§3.2–3.3.1, ecuaciones3.2,3.3,3.8:

`V_ijgr = ASC_gr + beta_c,g C_ijgr + beta_t,g t_viaje,ijgr + beta_e,g t_horario,ijgr + beta_a,g t_acceso,ijgr`.

C es costo privado completo construido/condicionado; tiempos en horas. No se reemplaza por tiempo único ni se estima CG simultáneamente con componentes colineales. Si se usa VST privado para resumirCG, debe justificarse; no es VST social.

## Alternativas y unidades

VL=viaje de vehículo con dinero de sus ocupantes; CAM=viaje de camión, no tonelada ni tripulante; PEATON=viaje de persona general con perfil de transporte público. Actual: terrestre_chile/barcaza_actual. Argentina excluida. Incorporar BahíaJara–Levicán es una etapa futura.

Nidos terrestre y lago. Normalización ASC_tierra0 y escala superior1. Biogeme utiliza `mu_lago=1/lambda`; central lambda 0,70 y sensibilidades0,50/0,90 son supuestos. Con una alternativa en cada nido, `lambda*log(exp(V/lambda))=V`: las probabilidades actuales son algebraicamente logit de dos alternativas, **manteniendo los cuatro atributos de utilidad**. No se identifica lambda ni ASC del cruce futuro con esta muestra.

## Etapa 11, comparación histórica

Biogeme intentó ASC y cuatrobetas libres: rango3/5; no se retuvo como identificación. Los intentos de costo negativo alcanzaron frontera cercana a0. Se adoptaron pendientes negativas supuestas. ParaVL se estimó condicionalmente beta_horario, con variación estacional limitada; no es efecto causal de frecuencia. CAM quedó con ASC condicionada a pendientes fijas. Peatones utilizó objetivo proxy, no MLE de elecciones terrestres personales.

## Etapa 11B vigente

Pendientes fijadas según instrucción del equipo y respaldo conceptual de literatura, **no coeficientes numéricos acreditados por literatura para el lago**:

| parametro | valor | unidad | metodo |
| --- | --- | --- | --- |
| beta_c | -2 e-05 | utilidad_por_CLP | supuesto |
| beta_t | -0.2 | utilidad_por_hora | supuesto |
| beta_a | -0.3 | utilidad_por_hora | supuesto |
| beta_e | -0.3 | utilidad_por_hora | supuesto |
| ASC_barcaza | -0.321915 | adimensional | calibrado |
| ASC_terrestre | 0 | adimensional | supuesto |
| lambda_lago | 0.7 | adimensional | supuesto |

| segmento | valor | metodo |
| --- | --- | --- |
| VL | -0.321915 | calibrado |
| CAM | -3.79334 | calibrado |
| PEATON | 0.0911272 | calibrado |

Biogeme 3.3.2 recibe C/10000CLP, beta_c=-0,20 en esa escala; CSV informa beta_c por CLP. Betas t/a/e son porhora. VST implícito10000CLP/unidad-h es supuesto distinto según unidad, no se multiplica automáticamente por ocupación.

## Interpretación de los coeficientes

Un beta negativo reduce la utilidad cuando aumenta el atributo. Con beta_c=−0,00002/CLP, agregar 10000 CLP al viaje reduce la utilidad en 0,20. Una hora adicional de viaje reduce 0,20; una hora de acceso o desajuste reduce 0,30 en 11B. Son unidades de utilidad normalizada, no pesos monetarios ni beneficios sociales.

La ASC es un ajuste relativo a tierra, cuya constante se normaliza a cero. Depende de las pendientes, atributos omitidos y objetivo de calibración; no es por sí sola una preferencia observada. Una probabilidad es una predicción condicionada al escenario y al soporte, no la certeza de una cuota poblacional.

## Muestra y ponderaciones

Se conserva la base individual11 sin difundirla. Ruta elegida confirmada, atributos de ambas alternativas y disponibilidad condicionada; se excluyen Argentina/desconocidos yODcomunales no resueltos como localidad.

`w_n=Q_celda,ruta / N_encuestas_elegibles_celda,ruta`, normalizados a sumaN por segmento/escenario. Esto no certifica inclusión probabilística ni elimina selección por punto de interceptación.

- VL:61 entrevistas de3 estratos con ambas rutas y sensibilidad24 hPC1 laboral. Verano ChileChico→Coyhaique y primavera ambos sentidos. Cobertura parcial.
- CAM:9 entrevistas de mayo, tierra10 h frente ferry diario. Cuota48,78% es contraste temporal incompleto, no participación diaria defendida.
- PEATON:3 celdas objetivo de cuota/distribuciónVL. Se optimiza enBiogeme `s log(P_M)+(1−s) log(P_T)` con fracciónproxy s y pesos por celda. No se generan elecciones terrestres falsas; sin errores estándar de personas.

La calibración de ASC reproduce la cuota global por condición del ajuste, no valida cadaOD ni el diseño muestral. No combinar escenarios como observaciones nuevas. Los errores deASCvehicular son condicionales del modelo, no de encuesta. No reportar significancia de betas fijados o del proxy.

## Implementación

`scripts/modelo_biogeme.py` y `modelo_biogeme_11b.py`: utilidad/nidos y calibración. `11_calibrar_logit.py`: reconstrucción de base y experimentos históricos. `11b_recalibrar_logit.py`: reutilización de base/pesos y sensibilidades. No se ejecutaron otra vez para organizar este repositorio.

El código puede inspeccionarse y probarse sintéticamente en GitHub; recalibrarARISTO requiere la base derivada local y fuentes autorizadas. [Fuentes](01_fuentes_datos.md), [supuestos](06_supuestos_sensibilidades.md), [resultados](07_resultados_y_limitaciones.md).
