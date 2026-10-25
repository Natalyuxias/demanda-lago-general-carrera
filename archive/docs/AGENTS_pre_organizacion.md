# Instrucciones para Codex — demanda lacustre Bahía Jara–Levicán

## Objetivo
Construir una estimación **reproducible y trazable** de demanda del proyecto evaluado en el Informe 2 EVALSO, sección 5.1. La primera entrega es una estimación **preliminar por escenarios**; NO afirmar que hay un logit calibrado si no hay identificación.

## Fuentes y orden
1. `../INFORME_2_EVALSO-1.pdf` es la metodología **declarada** (no necesariamente factible hoy). La versión local ubica demanda en capítulo 3; comprobar numeración en otras versiones.
2. ARISTO, `Base de datos agregada.xlsx`, hojas `BBDD-1` y `BBDD-2 (solo válidas)` aporta microdatos de demanda local; `Consolidado Flujos.xlsx` aporta conteos que deben auditarse antes de expansión.
3. Auditorías y documentos de variables elaborados por IA son índices auxiliares, NO fuentes primarias ni entregables de consultoras. Verificar en Excel e informes originales.
4. CITRA, Informe 2 corregido, sección 6.1, aporta EOD **muestral y de verano, sin expansión**. Usar solo como contraste hasta comprobar compatibilidad.

## Límites no negociables
- Nunca confundir número de encuestas, conteo de un zarpe y demanda diaria/anual.
- Nunca inferir `tierra` a partir de `encuestado en carretera` ni de celdas sin transbordador.
- No tomar las matrices interregionales del capítulo 8 de ARISTO como matriz local: omiten OD clave Chile Chico–Coyhaique y Chile Chico–Río Ibáñez.
- No usar `Normal/Otoño` como `Invierno` sin sustento.
- No usar un mismo coeficiente de CG junto con sus componentes colineales para calibración simultánea.
- No inventar costos, tiempo preferido, horario de partida, factores de expansión, demanda rechazada, probabilidades, VST, elasticidad ni valores de beta o lambda.
- `lambda` del nido lago y la constante propia del cruce futuro NO se identifican a partir de elecciones históricas de un único cruce existente.
- `CG` o logsum no puede producir beneficios monetarios sin coherencia de escala y unidades.
- Separar pasajeros peatones, vehículos livianos y carga; no sumar personas con vehículos.
- No sumar muestras independientes CITRA y ARISTO sin diseño muestral combinado.

## Seguridad de datos
- **No agregar a Git/GitHub** microdatos, hojas Excel originales, identificadores individuales, coordenadas personales, contraseñas, claves, archivos geográficos no anonimizados ni grandes anexos.
- La carpeta `data/raw/` es local y está excluida. Trabajar allí o leer directamente la carpeta externa de Anexos.
- No copiar datos sensibles a servicios externos o Codex Cloud sin autorización expresa. Recomendado Codex CLI local.
- Nunca modificar los archivos originales; solo escribir a `data/interim`, `data/processed` y `outputs/`.

## Forma de trabajo
- Antes de implementar una etapa, identificar la ecuación del Informe 2, insumos exactos, unidades, trazabilidad y pruebas.
- Entregar primero reporte de auditoría con estados `observado`, `calculado`, `supuesto`, `no identificado`.
- Scripts CLI pequeños; pruebas con datos **sintéticos**; nunca pruebas de GitHub con registros reales.
- Si falta un dato, dejar `NaN` y documentar el bloqueo; NO completar automáticamente con cero.
- Cada salida debe indicar fuente, universo, periodo, unidad y supuestos.
- Primera meta: reproducir conteos de auditoría y construir una matriz muestral local. Segunda: validar conteos/expansión. Tercera: captación por escenarios. Solo después: logit binario/jerárquico.

## Comandos de verificación
Implementación vigente desde 25/10: cuatro estaciones y detalle mensual; frecuencia histórica ordinaria confirmada por usuario 11 diciembre–abril y 8 mayo–noviembre, por sentido, sin carga peligrosa. Marzo/abril e invierno no reciben automáticamente ocupación de mayo. Inducción total SBO=0 por supuesto; captación pendiente de CG/elección, sin porcentajes arbitrarios. Dos naves, solo cambia frecuencia. Ver `data/templates/config_sbo.json` y README.

`python scripts/04_actualizar_sbo.py`
`python scripts/05_investigar_demanda_terrestre.py`
`python scripts/04_actualizar_sbo.py` (incorpora longitudes CAM observadas después del paso 05)
`python scripts/06_resumir_actualizacion.py`
`python -m unittest discover -s tests -p test_sbo_terrestre.py -v`

Comandos generales/anteriores:
`PYTHONPATH=src python -m pytest -q`
`python scripts/01_auditar_eod.py --eod '/ruta/local/Base de datos agregada.xlsx'`
`python scripts/02_escenarios_demanda.py --input data/templates/flujos_base.csv`
