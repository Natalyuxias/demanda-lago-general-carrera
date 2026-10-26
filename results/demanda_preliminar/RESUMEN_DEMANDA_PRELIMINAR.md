# Demanda preliminar — Etapa13

Primera estimación bajo supuestos editables; sin recalibrar11B ni reconstruir atributos12. Se separan demanda existente redistribuida, inducida y total. Argentina excluida. La cobertura vehicular comprende los cuatroOD dirigidos y las cuatro estaciones. EnPEATON se estiman ocho mercadosChileChico↔Coyhaique; las ocho celdasPuertoIbáñez se mantienen como servicio observado/transferido aparte, sin inventar un bus ni forzar elección del ferry.

## Totales anuales preliminares para el equipo

Los valores se presentan por intervalos amplios, deliberadamente sin cantidades exactas porOD/sentido/estación que permitan reconstruir celdas reservadas. Cada intervalo incluye el extremo inferior y excluye el superior. No sumar conceptos: la captación es parte de la demanda existente y nuevo_total ya incluye nuevo_inducido. No sumar personas con vehículos.

| Segmento | Existente ySBO | Desviada al nuevo cruce | Inducida, todo el mercado | Total con proyecto | Total nuevo cruce |
| --- | --- | --- | --- | --- | --- |
| VL | 28,000 a <29,000 | 4,000 a <5,000 | 0 a <1,000 | 28,000 a <29,000 | 4,000 a <5,000 |
| CAM | 9,000 a <10,000 | 0 a <1,000 | 0 a <1,000 | 9,000 a <10,000 | 0 a <1,000 |
| PEATON | 160,000 a <170,000 | 20,000 a <30,000 | 0 a <10,000 | 170,000 a <180,000 | 20,000 a <30,000 |

El detalle numérico porOD, sentido, estación, segmento y alternativa está disponible en el entorno local `outputs/etapa13_demanda_preliminar/`. No se publica completo: contiene celdas pequeñas. La ausencia del detalle enGitHub no significa cero viajes. La selección pública conserva solo un ejemploVL ya divulgado, con sus alternativas, demanda existente, inducida y total; los demás mercados se agrupan por segmento a nivel anual. No se publica una segunda tabla exacta complementaria por temporada o geografía.

## Método y supuestos centrales

1. Prioridad a ferry expandido+tierra24h de sensibilidad. ParaCAM se transfiere el factorVL; en mayo falta factor propio y se usa primavera como supuesto explícito.
2. Si solo existe ferry: reconstrucción del total medianteP histórica11B, nuncaP_SBO. Piso deprobabilidad0.05, registrado si actúa. ParaPEATON se conserva el proxy12 cuando existe.
3. Mayo representa marzo-mayo e inicialmente invierno. Si falta el dato propio, se prioriza otra estación del mismoOD/sentido. CAM dePuertoIbáñez sin muestra se transfiere desdeCoyhaique mediante razón de mercadosVL de la misma dirección. No se impone simetría.
4. Oferta central de12: SBO14/12 semanales por sentido en alta/baja; nuevo cruce14 y80min, P-20a. Requiere nave adicional independiente y conexiones intralocales aproximadas. Los escenarios no certifican operación ni capacidad.
5. Inducción por perfil: beneficio=deltaLogsum/abs(beta_c), dividido porCG privado esperadoSBO positivo, sinASC. CG usa dinero y tiempos con valores consistentes conbetas; no se duplica embarque/desembarque. Se aplica elasticidad constante por perfil y después se agrega. Comparación con aproximación local en sensibilidades.
6. Elasticidades supuestasVL−0.354,CAM−0.106,PEATON−0.80. No son estimacionesARISTO ni un objetivo de crecimiento2.5–5.1%. Si r>0.95 se limita explícitamente y se registra; no se modificanASC.
7. Anualización2026: verano90días, otoño92, invierno92, primavera91. No hay nueva proyección de crecimiento. Los totales deSBO y referencia histórica comparten tamaño de mercado.

El archivo público de sensibilidades se limita a frecuencia7/21, elasticidades bajas/altas y aproximación local, con los mismos mercados agrupados. El informe local incluye además expansión, transferencia estacional, cuota de imputación, peatones,lambda,ASC nueva, tarifas y tiempos. Los escenarios no se suman y no son intervalos de confianza. La auditoría conjunta de intervalos incluye las transferencias, el ejemplo ya conocido y la cuota globalVL11B: exige que ningún otro mercado quede determinado ni acotado por debajo de la amplitud relativa configurada del10%. Es un control conservador, no una garantía formal de anonimato.

## Archivos y reproducción

- [Totales anuales por segmento, en intervalos](totales_anuales_intervalos.csv).
- [Sensibilidades principales, en intervalos](sensibilidades_intervalos.csv).
- [Supuestos editables y procedencia](supuestos_centrales.csv).
- [EjemploVL divulgable, con inducción por alternativa](ejemplo_vl_verano.csv).

Configuración: `data/templates/config_etapa13.json`. Cálculo local: `.venv/bin/python scripts/15_estimar_demanda_preliminar.py`. Exportación revisada: agregar`--publicar` al mismo comando, solo después de validar la revisión. Pruebas: `PYTHONPATH=src .venv/bin/python -m pytest -q`; validador: `.venv/bin/python scripts/13_validar_repositorio.py`. Reproducción completa exige resultados locales07–12, no distribuidos. Sin ellos se puede consultar la selección y ejecutar pruebas sintéticas.

Pendientes de revisión: representatividad de cuotas y factores temporales, cobertura y estacionalidad, geometría/terminales y estándar vial, tarifas y accesos, flota y capacidad, transferencia de elasticidades y perfiles personales sin alternativa terrestre. Esta publicación tiene supresión y coarsening conservadores, no una garantía formal de anonimato.
