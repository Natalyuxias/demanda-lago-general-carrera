# Resultados vigentes para consulta

**Escenario central: Etapa 11B.** Estos CSV son una selección revisada de salidas ya calculadas, no otra estimación. Se consultan sin Python. En sus columnas se indican unidades y estado.

| Carpeta | Contenido |
|---|---|
| matrices_od/ | EjemploVLverano con soporte suficiente; restoNaNreservado/faltante |
| expansion_temporal/ | Factores híbridos de sensibilidad, no oficiales10→24 h |
| atributos/ | Distancias, tiempos yCOV de red; tarifas de referencia, sin atributos individuales |
| calibracion_logit/ | Parámetros11B, objetivos globales y probabilidades seleccionadas |
| sensibilidades/ | Parámetros y probabilidades seleccionadas por escenario |

`manifest_publicacion.json` registra fuente local, criterio de selección, cantidad de filas y hash de cadaCSV. `scripts/12_preparar_resultados_compartibles.py` vuelve a seleccionar desde outputs locales; nunca estima demanda. `scripts/13_validar_repositorio.py` verifica esta selección sin los originales.

## Privacidad y alcance

Se aplica umbral editorial de 5 entrevistas por alternativa para divulgar probabilidadesVL y se excluyenODde soporte incierto; además hay supresión complementaria de flujos. No es garantía formal de anonimato. Se reservan las probabilidadesCAMpor OD y todos los microdatos. Los perfilesPEATONcompartidos son escenarios de oferta con cuota proxy, no datos de personas. Se muestran solo parámetros de modelos agregados para CAM.

No publicar controles o totales locales adicionales para intentar reconstruir celdas reservadas. `NaN` puede significar noidentificado o noautorizado, nunca viaje0. Los CSV no son un reemplazo íntegro de las matrices locales. No sumar personas con vehículos ni escenarios como observaciones distintas.

Las salidas completas siguen en `outputs/` local, sin modificaciones y fuera de Git. Recalibrar exige base individual/local y fuentes autorizadas; desde Git solo es posible consultar resultados, revisar fórmulas/parametrización y verificar pruebas sintéticas/consistencia del material compartido.
