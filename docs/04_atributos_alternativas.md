# 04. Atributos de alternativas completas

Las rutas se reconstruyeron con arcos/nodos ARISTO; se verificó continuidad, orientación, conectividad y sumas de costos/distancia. No se usó una ruta interregional como sustituto local. Origen/destino son anclajes físicos explícitos: Chile Chico1358, Coyhaique1223 y acceso público de Puerto Ibáñez1021. No son domicilios ni centros urbanos validados; el acceso intrazonal permanece pendiente. Los conectores convencionales10 km con velocidad/costo0 no se suman como distancia física.

## Ejemplo Chile Chico→Coyhaique

| segmento | alternativa | distancia_terrestre_total_km | tiempo_conduccion_terrestre_h | tiempo_navegacion_h | COV_terrestre_privado_ARISTO_CLP |
| --- | --- | --- | --- | --- | --- |
| VL | terrestre_chile | 382.515 | 6.05203 | 0 | 78,538 |
| VL | barcaza_actual | 121.956 | 1.45839 | 2 | 22,135 |
| CAM | terrestre_chile | 382.515 | 7.23201 | 0 | 399,966 |
| CAM | barcaza_actual | 121.956 | 1.98438 | 2 | 97,372 |

Unidad de costos: CLP privados diciembre2025 por vehículo-viaje. `t_conduccion=sum(L_km/V_kmh)`. COV por arco: costo/km de Tipos de arcos×longitud, redondeado como Excel; se suma toda la conducción terrestre. VL y VP tienen velocidades/costos distintos; VP representa mezcla de tipos, no todo camión individual. Las fórmulas/cache de los arcos empleados se reprodujeron en etapa09; openpyxl no recalcula Excel.

`CostGen VL` ya incluye tiempo monetizado y, en algunos arcos, penalización de pavimento. **No se suma a COV ni se usa como tiempo físico.** Los precios sociales de beneficios no sustituyen los privados del logit.

## Separación temporal

| Componente | Tratamiento |
|---|---|
| Acceso de barcaza | Todos los tramos terrestres de acercamiento y egreso entre anclajes |
| Viaje barcaza | Navegación2 h más anticipación/desembarque imputados al mismo beta_t |
| Anticipación | Vehículos2 h, peatones1 h; exigencia del operador, no duración medida ni desutilidad observada |
| Embarque previo | Contenido en anticipación; sin otra hora añadida |
| Desembarque vehicular | Supuesto15/30/45min; central30; no medido en La Tehuelche |
| Horario | `0,25×168/f`; desajuste, no espera física en muelle |
| Tierra vehicular | Viaje=conducción; acceso/horario de barcaza0 |

La conducción descriptiva no vuelve a sumarse al acceso. En11/11B la utilidad mantiene cuatrocoeficientes: se agrupan previo/desembarque con viaje, no se crea otro beta. Se conservan las sensibilidades de calendario efectivo como antecedentes, pero el central usa168/f. Calendario publicado de alta12vs11delmodelo continúa como discrepancia, no se elimina un zarpe arbitrariamente.

## Dinero y transporte público

ARISTO tabla 52: VL hasta5,5 m21270, adulto2550, metrolineal7310CLP; exenciones dependen de categoría. Conductor liberado en servicio subvencionado según extracto web actual; no es una condición verificada por ticket histórico. Acompañantes, descuentos y tasas no se deducen de la edad de quien respondió. La tarifa del arco de barco no se suma como COV terrestre.

EOD incluye ocupantes/longitudes; se usan individualmente solo en bases locales. No se publica la distribución de celdas pequeñas ni se impone16 m a camiones. Tarifa lineal=7310×longitud facturable, pendiente de cotejo con dimensiones declaradas/categoría y redondeo.

Tarifas del equipo: bus Coyhaique–Puerto Ibáñez10000; escenario general separado bus+ferry12550CLP. Integración no verificada. Tierra completa9000 es supuesto, no tarifa confirmada Interlagos. Vigencia/documento del equipo pendientes.

Carolina6 h bimodal, Interlagos8 h terrestre, Freddy5 h aeropuertoBalmaceda–ChileChico: ARISTO tabla 61. No sustituir Coyhaique por aeropuerto. El perfil peatonal de 11B paraCoyhaique divide6 h en viaje3,5 h(navegación+previo+desembarque) y acceso residual2,5 h: imputación explícita, no velocidad de automóvil ni servicio declarado por todos los peatones. Las6 h no reciben nuevamente navegación/embarque. Bus terrestre8h no usa conducciónVL.

Base común exploratoria diciembre2025: factor tarifario109,26/109,71; enero2026 es fecha imputada, no vigencia comprobada. El escenario monetario central no es desembolso confirmado completo. Ver `outputs/atributos_logit_actualizados/` para faltantes autorizados localmente.
