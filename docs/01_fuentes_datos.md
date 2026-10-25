# 01. Fuentes y permisos

| Fuente | Material disponible localmente | Uso | Distribución en GitHub |
|---|---|---|---|
| ARISTO | Excel EOD, conteos, factores/matrices, red vial y costos, informe final | Fuente principal; fórmulas y valores almacenados revisados | No originales ni microdatos; solo selección derivada revisada |
| CITRA | PDF Informe 1 e Informe 2 corregido, entre otros | Perfiles y contraste muestral independiente | No PDF, microdatos ni tablas muestrales copiadas |
| EVALSO | `INFORME_2_EVALSO-1.pdf` | Ecuaciones de demanda/CG privado/utilidad | Método documentado; PDF fuera de Git |
| MOP/PNCV | Referencias oficiales a coeficientes12→24 h | Parte de sensibilidades; no factor oficial10→24 h | Factores y enlaces; no nueva campaña |
| Naviera Austral | Tarifarios, FAQ, condiciones e itinerarios | Anticipación, navegación, frecuencia y tarifas | Parámetros con vigencia/condición explícita |
| Equipo EVALSO | Frecuencia11/8, tarifas de buses y escenarios | Definiciones de trabajo | Configuraciones; fuente documental/vigencia de tarifas pendientes |
| Literatura | Wardman2004, OECD/ITF2014; documentación Biogeme | Respaldo conceptual y convención del modelo | Referencias; no atribuirles nuestros betas numéricos |

## Archivos originales esperados fuera del repositorio

- `../Cap 6/BBDD EOD/Base de datos agregada.xlsx`: BBDD-1, BBDD-2 (solo válidas), TD Transb.
- `../Cap 6/Mediciones de flujo/Consolidado Flujos.xlsx`: Transbordadores, Carretera.
- `../Cap 8/EOD_Puntos_Pasada_Final.xlsx`: arcos_ptocontrol, Puntos por OD (Ordenados).
- `../Cap 8/BBDD_para_Pijas_actualizada_EOD_Final.xlsx`: Arcos por OD.
- `../Cap 8/Matrices Situación Actual.xlsx`: revisión histórica de matrices, no sustituto local automático.
- `../Cap 7/HDM4/Costos_Red_Vial_Actual.xlsx`: Costos_Red_Vial, Tipos de arcos. Enlace HDM4 privado de diciembre2025 conservado; no motor HDM4 recalculado.
- `../Cap 7/Arcos con sentido.xlsx`, `../Cap 7/SIG Red_Vial_Final/` con nodos, red y rutas SIG.
- `../Cap 10/Resumen_Rutas_Red_Vial_Actual.xlsx`: Rutas Red Actual.
- `../SIG/Coberturas/ARISTO/Transbordadores.*`: catastro histórico y discrepancias de frecuencia.
- `../Informe ARISTO.pdf`: §§2.2.6,5,6,7,8 y10; tabla 38 itinerarios,52 tarifas,61 buses,78 encuestas y107/138/169 conteos.
- `../Estudios de consultoras/Informe 1 - MOP aysen vf.pdf`: perfiles Chile Chico pp165–218 y otros inventarios puntuales.
- `../Estudios de consultoras/Informe 2c - MOP aysen vf.pdf`: EOD muestral §6.1 y carga pp86–87.
- `../INFORME_2_EVALSO-1.pdf`: §§3.2–3.3 y ecuaciones3.2,3.3,3.8 en versión local.

Las EOD de ARISTO y CITRA son estudios distintos. No hay microdatos CITRA en este proyecto. Sus matrices publicadas son encuestas sin expansión, no flujos diarios; no se mezclan con ARISTO ni se usan conteos completos de corredor como un OD local.

## Fuentes públicas y limitaciones

- [Naviera Austral: ruta y tarifas](https://www.navieraustral.cl/lago-general-carrera/).
- [FAQ de anticipación](https://www.navieraustral.cl/preguntas-frecuentes/) y [Condiciones2025](https://www.navieraustral.cl/wp-content/uploads/2024/12/Condiciones-Comerciales-2025-NASA.pdf).
- [PNCV Dirección de Vialidad](https://vialidad.mop.gob.cl/plan-nacional-de-censo-vial/).
- [IPC difundido por SII2025](https://www.sii.cl/valores_y_fechas/utm/utm2025.htm), [2026](https://www.sii.cl/valores_y_fechas/utm/utm2026.htm).
- [Wardman2004](https://doi.org/10.1016/j.tranpol.2004.05.001), [copia institucional](https://eprints.whiterose.ac.uk/id/eprint/3393/2/Public_Transport_Values_of_Time_secure.pdf).
- [OECD/ITF2014](https://www.oecd.org/content/dam/oecd/en/publications/reports/2014/12/valuing-convenience-in-public-transport_g1g4525d/9789282107683-en.pdf).

Consulta documental incorporada en etapas previas,25/10/2026. No se efectuó nueva búsqueda de factores o modelos para organizar el repositorio. Las auditorías de IA son índices, nunca evidencia primaria. Disponibilidad de un archivo no implica permiso de redistribuirlo: los originales y transcripciones reservadas quedan locales.
