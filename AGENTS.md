# Trabajo en el repositorio de demanda EVALSO

Leer primero README.md y docs/01–09. Central vigente: Etapa11B. No ejecutar modelos ni extender área de influencia durante tareas de organización/documentación.

## Fuentes y unidades

ARISTO es fuente primaria; CITRA solo PDF de contraste, sin microdatos disponibles. Auditorías de IA son índices. Mantener cuatro estaciones, OD locales y distinción Puerto Ibáñez/localidad frente a Río Ibáñez/comuna. No inferir tierra desde interceptación en carretera; Argentina y rutas desconocidas quedan fuera de elección actual, sin redistribución.

Separar encuestas, conteos, flujos expandidos y supuestos. No sumar vehículos/personas ni convertir NaN en cero. Betas11B son supuestos de referencia y ASC condicionadas; lambda no se identifica con un cruce observado. P-20a, nuevo cruce, SBO e inducción son tareas futuras, no resultados actuales.

## Conservación y privacidad

No modificar fuentes originales. outputs/, data/interim/ y data/private/ son locales y no se publican. No versionar microdatos, identificadores, domicilios/coordenadas personales, Excel/PDF/SIG originales, bases individuales, credenciales ni cachés. Results contiene una selección de divulgación; respetar supresión de celdas pequeñas y complementarias, sin reconstruirlas con totales.

No borrar ni mover dependencias por parecer históricas. El script03 aporta funciones a07/10; los04–06 y archivos dearchive están fuera del flujo central, conservados por trazabilidad. Documentar cambios y mantener resultados anteriores intactos.

## Verificación

`python scripts/13_validar_repositorio.py`

`PYTHONPATH=src python -m pytest -q`

Pruebas solo sintéticas. No afirmar que un flujo real fue reestimado por haber compilado/importado el script. Publicar mediante commit/push solo con autorización del usuario; nunca force, reescritura de historial ni datos reservados. La instrucción del usuario prevalece sobre estas pautas.
