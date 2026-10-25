# Estimación preliminar reproducible

Ejecutar desde este proyecto:

```bash
python scripts/03_estimar_demanda_local.py --anexos /ruta/a/Anexos
python -m unittest discover -s tests -p test_estimacion_local.py -v
```

El script utiliza pandas y openpyxl, lee únicamente fuentes seleccionadas y produce `outputs/estimacion_preliminar/INFORME_RESULTADOS.md` y tablas A–D. No requiere Excel, no recalcula originales y no publica resultados. `--refresh` invalida los caches locales.

Las rutas de fuentes, agrupación de usuarios, captación y calendario supuesto se configuran en `data/templates/config_estimacion.json`. Cada fijo indica procedencia o condición de supuesto. El informe ARISTO original se llama `Informe ARISTO.pdf` y está en la raíz de Anexos. Los archivos de auditoría y variables elaborados por IA sirven como índices, no como fuentes verificadas. El PDF EVALSO disponible se llama `INFORME_2_EVALSO-1.pdf` y ubica la metodología de demanda en el capítulo 3; la referencia al capítulo 5 corresponde a otra numeración que no se pudo verificar.

Primero se reproduce `TD Transb` y se guardan fórmulas/caches de esa hoja, `arcos_ptocontrol` y matrices. Luego se preserva el flujo original y se construyen sensibilidades de media por zarpe con frecuencias de los documentos, sin elegir una como frecuencia anual comprobada. Una cuarta variante conserva la discrepancia de conteos de mayo entre el PDF y el Excel.

El flujo se distribuye por participaciones de entrevistas válidas del cruce, dentro de campaña, sentido y clase. Es un supuesto de composición, no un diseño muestral validado. Las clases conservan las particularidades de ARISTO (privados incluye bicicletas; carga incluye remolques). Pasajeros de bus/van/transfer no se convierten en vehículos. Donde falta muestra, el flujo se conserva sin asignar OD.

Se entregan captaciones exógenas de 10/25/50%, separando cuatro OD iniciales y envolvente del cruce completo; esta última no acredita elegibilidad de todos los OD para el proyecto. La demanda terrestre, inducida y total permanecen como NaN. La anualización es un escenario de calendario e invierno explícitos, sin crecimiento. El cálculo no modela todavía respuesta de demanda a la SBO de dos naves.

Los datos seleccionados en `data/interim/estimacion_preliminar/` contienen claves internas y nunca deben publicarse. Las salidas agregadas tampoco están destinadas a publicación automática: contienen celdas pequeñas y cifras condicionadas. Ambas rutas están excluidas de Git. El código, configuración y pruebas sintéticas pueden revisarse sin cargar microdatos al repositorio. No se ejecuta `git add`, commit ni push.

Las aserciones del proceso comprueban llaves, correspondencia de válidas, identidad de cálculos, conservación de flujos y SHA256 de fuentes antes/después. Las pruebas sintéticas verifican propagación de faltantes, conservación de unidades, dirección y calendario. Estas comprobaciones aritméticas no certifican representatividad poblacional.
