# 09. Organización, validación y publicación

## Flujo vigente y dependencias

| Archivo | Estado | Dependencias y uso |
|---|---|---|
| `07_matrices_od_referencia.py` | Matrices vigentes | Importa lectores/normalización de03 y formato de capacidad; contraste CITRA opcional |
| `08_expandir_tiempo_terrestre.py` | Sensibilidades temporales vigentes | Lee07, PDF y configuración; usa el módulo temporal |
| `09_construir_atributos.py` | Reconstrucción de red | GeoPandas, PyProj y red HDM4; conserva Argentina histórica, excluida de 11/11B |
| `10_completar_atributos_logit.py` | Dos alternativas actuales | Importa07/03; sus perfiles individuales permanecen locales |
| `11_calibrar_logit.py` | Base necesaria y comparación histórica | Importa10/07/03 y modelo_biogeme; conserva intentos de identificación |
| `11b_recalibrar_logit.py` | Escenario central vigente | Lee la base11 y atributos10; importa definiciones11 sin ejecutar su main |
| `modelo_biogeme.py`, `modelo_biogeme_11b.py` | Bibliotecas compartidas | Utilidad de cuatro componentes, nidos y calibración de ASC |
| `12_preparar_resultados_compartibles.py` | Organización, sin estimar | Selecciona columnas y celdas de CSV ya calculados |
| `13_validar_repositorio.py` | Validación, sin estimar | Sintaxis/importaciones, manifiesto, CSV, enlaces y revisión del índice |
| `14_aplicar_etapa12.py` | Aplicación exploratoria local autorizada | Lee resultados11B intactos; SBO/nuevo cruce, demanda parcial y logsums; sin recalibración ni inducción |
| `15_estimar_demanda_preliminar.py` | Etapa13, aplicación autorizada | Completa mercados e inducción por perfil, sin recalibrar ni reconstruir atributos; detalle local y selección pública mediante `--publicar` |
| `01_auditar_eod.py`, `02_escenarios_demanda.py` | Iniciales/históricos | Auditoría y esquema inicial; no método vigente de captación |
| `03_estimar_demanda_local.py` | Ejecutable histórico, funciones compartidas | No ejecutar sus porcentajes de captación; conservar sus lectores importados |
| `04_actualizar_sbo.py`, `05_investigar_demanda_terrestre.py`, `06_resumir_actualizacion.py` | Antecedentes históricos | No constituyen una SBO actual validada |

Los nombres en la tabla son relativos a `scripts/`. Se identificó duplicación conceptual de reportes y lectores, y una transcripción CITRA repetida en configuraciones. Se evitó refactorizar masivamente código analítico durante esta tarea. Los lectores en03 son deuda técnica documentada: moverlos exige actualizar importaciones y volver a verificar resultados con autorización.

## Cambios de organización

- README reescrito; documentos01–08 y este catálogo, con una guía específica de resultados.
- Planes, prompts, bitácora y pautas iniciales conservados en `archive/docs/`. No se eliminó información metodológica.
- Parámetros centrales de 11 conservados para comparación;11B es el central vigente.
- Resultados seleccionados mediante12, con procedencia y hashes. Las salidas completas permanecen locales e intactas.
- Contraste CITRA opcional en 07/05. La configuración original con tablas duplicadas se conserva en `data/private/configs/config_rutas_terrestres_pre_publicacion.json`; se comparten las mismas reglas de clasificación sin esa tabla. Esto no altera la expansión ARISTO.
- `.gitignore` ampliado para originales, bases individuales, salidas privadas, entornos, cachés, transcripciones, credenciales y temporales.
- Separación de dependencias de pruebas. No se borraron funciones analíticas, validaciones ni scripts importados.

`data/templates/citra_matriz_publicada.json` y `config_estimacion.json` quedan locales, excluidos deGit. El primero solo afecta el contraste y tiene una plantilla vacía compartida. El segundo se usa al ejecutar el estimador histórico03, no al importar sus funciones. El contexto para otra IA permanece local en `outputs/contexto_datos_para_otra_ia.md`.

No se ejecutaron los generadores reales07–11B para organizar el repositorio. Los cambios en05/07 solo toleran el contraste CITRA vacío; los cambios en el texto de 10 evitan incorporar detalles de celdas pequeñas en el código compartido. Los resultados anteriores no se reemplazaron.

## Dependencias y reproducción

Entorno de ejecución probado: Python3.12.9, Biogeme3.3.2, NumPy2.4.6, pandas2.3.3, SciPy1.17.1 y JAX0.10.1. Es una referencia de compatibilidad, no una garantía para cualquier versión futura. La lista completa de dependencias directas comprobadas está en [entorno_probado.json](entorno_probado.json).

- `requirements.txt`: lectura, red y gráficos. GeoPandas/PyProj/Matplotlib se usan en09 y se conservan.
- `requirements-logit.txt`: añade Biogeme3.3.2 y SciPy.
- `requirements-dev.txt`: añade pytest para las pruebas.
- `pdftotext`, de Poppler, es una dependencia del sistema para leer PDF, no un paquete Python.

Las dependencias transitivas de Biogeme/JAX no se eliminaron manualmente. Reproducir datos reales exige los originales o intermediarios privados; consultar resultados y ejecutar pruebas sintéticas no.

## Validación de esta organización

```bash
python scripts/13_validar_repositorio.py
PYTHONPATH=src python -m pytest -q
```

El validador importa y analiza el código sin ejecutar los bloques main. Comprueba coeficientes11B, normalización, unidades, pares de probabilidades, reservas, hashes y enlaces. `--indice` revisa además archivos preparados para commit: extensiones prohibidas, rutas privadas, tamaño y patrones de secretos.

Las pruebas solo usan datos sintéticos; algunas verifican optimización Biogeme sintética. Eso no constituye una nueva calibración ARISTO ni prueba de reproducibilidad integral sin originales. El informe final registra cantidad y resultado de las pruebas.

La selección de resultados tiene una regla editorial conservadora y supresión complementaria, no una garantía formal de anonimato. No se redistribuyen originales ni se concede licencia sobre datos de terceros.

## Publicación del avance de Etapa12

Remoto existente: `https://github.com/Natalyuxias/demanda-lago-general-carrera.git`, rama `main`. La publicación se realiza con autorización expresa del usuario, después de consultar el remoto y comprobar divergencias, mediante commit y push normales, sin force ni reescritura de historial.

La selección del avance se concentra en [un resumen para el equipo](10_etapa12.md) y [un CSV del ejemploVL ya divulgable](../results/etapa12/ejemplo_vl_verano.csv), con acceso directo desdeREADME. Se incluyen código, configuración y pruebas para trazabilidad. Los CSV públicos anteriores se conservan; no se publica `outputs/etapa12/`, bases individuales ni nuevas celdas reservadas. El selector12 y el validador13 incorporan la selección deEtapa12 sin volver a estimar el modelo.

El commit publicado se puede consultar en el historial deGitHub. La verificación operativa es `git fetch origin` y `git rev-list --left-right --count HEAD...origin/main`: `0 0` después del push confirma coincidencia con el remoto consultado. Un commit local por sí solo no demuestra publicación.

## Resultados de Etapa13

El usuario autorizó calcular una primera demanda completa bajo supuestos y publicar después de validar. La [selección pública](../results/demanda_preliminar/RESUMEN_DEMANDA_PRELIMINAR.md) contiene intervalos anuales porsegmento y un ejemploVL ya divulgado. El detalle requerido porOD, estación, sentido y alternativa queda local en `outputs/etapa13_demanda_preliminar/`, junto con matriz48celdas, ocho servicios personales separados, comprobaciones y hashes. No se borra ni modifica ninguna salida07–12.

No se ofrecen totales exactos complementarios de otras celdas. La revisión conjunta de intervalos usa programación lineal asumiendo conocidos los coeficientes pormercado, relaciones de transferencia, la cuota global11BVL y el ejemplo publicado. Cada mercado reservado debe conservar una amplitud factible mínima del10% bajo esa prueba; es un control de divulgación, no una garantía formal de anonimato. El exportador se detiene si falla.

Reproducción con entradas locales: `.venv/bin/python scripts/15_estimar_demanda_preliminar.py`; exportación revisada agregando`--publicar`. No se ejecutan07–12 ni se recalibran parámetros. Pruebas y revisión del índice mediante los comandos documentados; commit/push normales solo después de aprobar validaciones y privacidad.
