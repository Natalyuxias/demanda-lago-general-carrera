# Plan de trabajo — estimación de demanda Bahía Jara–Levicán

**Base metodológica:** Capítulo 5 del Informe 2 de EVALSO.
**Fuentes:** Informe final ARISTO, capítulo 6 (EOD/conteos), 7 (red), 8 (matrices/expansión), y CITRA Informe 2 corregido, sección 6.1.
**Limitación:** solo se ha recibido aquí la auditoría y el CSV resumen, no la carpeta completa de planillas originales. Los datos de cantidad/hojas son hallazgos reportados por esa auditoría y deberán reproducirse localmente.

## Fase A — Delimitar universo y unidades
- [ ] Definir si cada registro representa vehículo, peatón/persona o grupo, manteniendo cuentas separadas.
- [ ] Identificar ODs elegibles, DIRECCIÓN, segmento y temporada: no dar por elegibles todos los viajes Chile Chico-Río Ibáñez.
- [ ] Definir oferta 0 (dos naves) y oferta 1 (nuevo cruce) sin confundir base histórica y base optimizada.
- **Entrega:** diccionario de variables, universo OD y escenarios operacionales.

## Fase B — Preparar microdatos
- [ ] Leer BBDD-1 y BBDD-2 (solo válidas) con ID 2, comparar recuentos con auditoría.
- [ ] Revisar origen/destino, fechas y temporadas, personas/vehículos/ocupación.
- [ ] Clasificar ruta lago confirmada y tierra confirmada; preservar categoría desconocida.
- [ ] Auditar distintos puntos para mismo OD y posibles dobles interceptaciones.
- **Entrega:** base descriptiva y cuadros muestrales (sin expansión).

## Fase C — Expansión de demanda actual
- [ ] Vincular por punto-sentido-fecha-clase encuesta y conteo de misma exposición.
- [ ] Pedir protocolo de expansión y verificación de 9 viajes semanales/horarios efectivos.
- [ ] Construir d0 OD×temporada×tipo×ruta, con unidad consistente.
- [ ] Evaluar duplicidad de controles en serie/paralelo y cobertura de rutas terrestres.
- [ ] Contrastar embarques con el conteo del operador y flujos de CITRA.
- **Bloqueador:** sin protocolización de pesos y circulación por rutas no declarar demanda poblacional.
- **Entrega:** flujos diarios EXPANDIDOS con intervalos/escenarios de incertidumbre.

## Fase D — Anualización
- [ ] Determinar días que representa cada campaña y temporada invernal.
- [ ] Verificar proyección tendencial por pares locales; los factores ARISTO fueron obtenidos para demanda interregional.
- **Entrega:** matriz anual por segmento con fuente de factores.

## Fase E — Oferta, rutas y costos generalizados
- [ ] Para cada OD y alternativa T, Ibáñez–Chile Chico y Jara–Levicán definir factibilidad.
- [ ] Construir atributos de elegida y NO elegidas (acceso, viaje, horario, embarque, dinero) coherentes y sin doble conteo.
- [ ] Validar navegación, accesos X-735/X-763, tarifa, horarios y factibilidad de peatones.
- **Entrega:** tabla OD×temporada×segmento×escenario×alternativa con CG privados.

## Fase F — Calibración / selección de escenario
- [ ] Verificar si tierra y lago están realmente observados en los mismos OD y períodos.
- [ ] Auditar identificabilidad de betas con matriz de diseño, correlación y observaciones efectivas.
- [ ] Si no se identifican: MNL/binario parsimonioso y escenarios de coeficientes transferidos claramente marcados.
- [ ] Nido lago: lambda y ASC del nuevo cruce fijados/sensibilizados, no presentarlos como estimados.
- **Entrega:** especificación, parámetros y validación de cuotas modales expandidas.

## Fase G — Predicción + capacidad + inducción
- [ ] Calcular probabilidades, captación, desviación y límites de capacidad por zarpe, temporada y dirección.
- [ ] Diferenciar demanda latente no atendida de demanda inducida.
- [ ] Calcular inducción con elasticidad justificada y métrica COMPATIBLE de costo agregado; no asumir identidad promedio−logsum.
- [ ] Evaluar escenarios tarifarios y de frecuencia, 40/80 min, rutas X-735 y elasticidades.
- **Entrega:** D0/D1 por OD/temporada/segmento/ruta y archivos auditables para beneficios.

## Información prioritaria a solicitar
1. Datos y reglas de expansión para los puntos del lago + rutas terrestres comparables; protocolo EOD y definición de validez.
2. Conteos, frecuencias observadas por sentido/zarpe y demanda atendida/no atendida (reservas, listas de espera, rechazos).
3. Calendario operativo y tarifas históricas; diseño de dos naves para la situación base optimizada.
4. Parámetros operacionales del nuevo cruce (derrota/tiempo/capacidad/accesos/horarios/tarifas).
5. Confirmación de si existen microdatos individuales y fichas de CITRA, no solo cuadros publicados.

## Regla de integridad
Nunca presentar número de encuestas como flujos; nunca llamar terrestre a una encuesta de carretera sin validar recorrido; nunca extender otoño a invierno sin datos; nunca estimar lambda con una sola opción lacustre observada.
