"""Resumen automatico de las tablas de los pasos04/05, sin nueva estimacion."""
from pathlib import Path
import json,importlib.util,sys,math,hashlib
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/sbo_actualizada'
sys.path.insert(0,str(ROOT/'src'))
from demanda.capacidad import documento_legible
spec=importlib.util.spec_from_file_location('prev',ROOT/'scripts/03_estimar_demanda_local.py')
prev=importlib.util.module_from_spec(spec);spec.loader.exec_module(prev)

def main():
    a=pd.read_csv(OUT/'A_historica_mensual.csv')
    mean=a.loc[a.mes.isin([1,5,9])].groupby(['estacion','mes','segmento']).flujo_dia.agg(lambda s:s.sum(min_count=2)).reset_index()
    mean=mean.loc[mean.segmento.isin(['VL','CAM','PEATON'])]
    c=pd.read_csv(OUT/'C_D_oferta_y_ocupacion_SBO.csv')
    cfg=json.loads((OUT/'config_utilizada.json').read_text())
    # Un ejemplo reproducible de sensibilidad, seleccionado por su nombre documentado.
    example=c.loc[c.mes.isin([1,9])&c.perfil.eq('compacto')&c.ml_Tehuelche.eq(164)&c.navegacion_h.eq(2)&c.escenario.isin(['mismo_total_dos_naves','baja_12_alta_14'])]
    example=example[['estacion','sentido','escenario','frecuencia_SBO','ocupacion_ml','ocupacion_pax']].copy()
    for k in ['ocupacion_ml','ocupacion_pax']:example[k]*=100
    example=example.rename(columns={'ocupacion_ml':'ocupacion_ml_pct_diseno','ocupacion_pax':'ocupacion_pax_pct_diseno'})
    minimum=pd.read_csv(OUT/'C_frecuencias_minimas_condicionales.csv')
    example_min=minimum.loc[minimum.mes.eq(1)&minimum.perfil.eq('compacto')&minimum.ml_Tehuelche.eq(164)&minimum.navegacion_h.eq(2)&minimum.ocupacion_objetivo.eq(.8)]
    land=pd.read_csv(OUT/'E_resumen_cuatro_OD_cuatro_estaciones.csv')
    lsum=land.groupby('estacion')[['encuestas_totales','barcaza_confirmada','tierra_confirmada_por_declaracion','ruta_desconocida','argentina_interceptacion']].sum().reset_index()
    counts=land[['encuestas_totales','barcaza_confirmada','tierra_confirmada_por_declaracion','ruta_desconocida']].sum()
    # Variabilidad de embarques por fila: maximo muestral, no percentil de llegadas.
    raw=pd.read_csv(OUT/'conteos_clases_separadas.csv')
    peaks=raw.groupby(['campana','sentido']).agg(filas=('fila_excel','size'),VL_medio=('VL','mean'),VL_maximo=('VL','max'),CAM_medio=('CAM','mean'),CAM_maximo=('CAM','max')).reset_index()
    peaks['factor_punta_VL_embarques_muestra']=peaks.VL_maximo/peaks.VL_medio
    peaks['factor_punta_CAM_embarques_muestra']=peaks.CAM_maximo/peaks.CAM_medio
    peaks.to_csv(OUT/'D_puntas_embarques_muestra_NO_llegadas.csv',index=False,encoding='utf-8-sig',na_rep='NaN')
    text=f'''# Actualización de demanda histórica, capacidad/SBO y viajes terrestres

Fecha:25/10/2026. Sustituye como resultados principales las captaciones porcentuales del24/10, conservadas como históricas. Captación del proyecto pendiente de CG/elección; no se calcula aquí.

## Demanda histórica atendida, con frecuencias ordinarias

Base: ARISTO, conteos originales sin modificar; frecuencia confirmada por usuario,11 zarpes/sentido/semana diciembre–abril y8 mayo–noviembre, sin carga peligrosa. Los conteos aún requieren distinguir servicios especiales. Media por fila/zarpe×frecuencia/7; exposición de verano/mayo sigue condicionada a una fila por zarpe. Clases separadas: VL cuatro ruedas, CAM agregado de carga ARISTO, motos, bicicletas, peatones; no comparar directamente VL con el antiguo agregado de privados que incluía motos/bicis.

Flujos diarios equivalentes **ambos sentidos**, meses de referencia: enero representa perfil de verano y septiembre perfil de primavera por transferencia condicional de campaña; mayo es solo mes de otoño.

{prev.mdtable(mean)}

Cuatro estaciones conservadas. Marzo/abril tienen frecuencia11 pero no perfil de ocupación identificado; mayo frecuencia8 y campaña Normal. Invierno no tiene perfil. No se completó otoño con mayo ni se anualizó una base incompleta. Las tablas A estacionales tienen cobertura explícita y totales parciales separados. Una demanda atendida no es el mercado potencial total.

## Capacidad documental y SBO

Tehuelche:70.2m,250pasajeros,30VL aproximados; cubierta80ml según CITRA Informe2c p417 frente a164ml según ARISTO p126/AnexoA RevB. Se conservan ambas sin elección definitiva. Nueva:80m,300asientos,44VL aproximados,252ml,diésel/eléctrica,13nudos técnicos; ARISTO p155 informa288pasajeros y se documenta la diferencia con300 del usuario. Capacidades iniciales, no certificación. Cupos VL aproximados no se aplican a una mezcla con camiones.

Solo se modifica frecuencia. Mercado total fijo; inducción SBO=0 por supuesto. También se mantiene el volumen lacustre histórico como escenario de oferta pura: el cambio desde tierra y la demanda antes no atendida no se identifican. Tarifa/accesos/navegación constantes entre histórico y SBO. Dos variantes documentales de navegación (2h y2h40), iguales para ambas naves; no se usa la velocidad técnica nueva para mejorar tiempos. El gancho de CG deja desfase y VST como faltantes hasta disponer de datos, sin suponer espera=intervalo/2.

Ejemplo de ocupación **de diseño**, no ocupación observada: Tehuelche164ml, nueva252ml, perfil compacto configurado (longitudes y ocupantes supuestos), navegación2h. La columna pasajeros es composición supuesta que no vuelve a sumar ocupantes de vehículos como peatones; no incluye una cifra inventada de grupos/buses ni pasajeros adicionales por bicicletas. El mínimo completo de pasajeros y la estiba siguen no certificados.

{prev.mdtable(example)}

Ejemplo de mínimos por sentido para verano, mismo perfil, objetivo80%. Ambos buques deben operar. Los valores son restricciones agregadas bajo los supuestos, no garantía de atención a cada zarpe. El reparto que minimiza frecuencia puede ser diferente del reparto casi por mitades de los escenarios anteriores.

{prev.mdtable(example_min[['sentido','factor_punta_diseno','frecuencia_minima_capacidad_promedio','frecuencia_minima_capacidad_con_punta','frecuencia_minima_con_ventana_operacional','frecuencia_SBO_minima_condicional']])}

Se entregan objetivos80/90/95% y factores punta de diseño1/1.5/2 para perfiles compacto, largo y longitud CAM observada en EOD cuando existe. Los máximos por fila medida se entregan aparte; no describen llegadas ni rechazos. Una punta aplicada a toda la semana es una envolvente de diseño, no estimación de un percentil. La frecuencia económicamente óptima queda NaN.

El calendario constructivo verifica2n navegaciones+(2n+1) maniobras por n ciclos, con maniobra0.5h,ventana12h/día y7días/semana SUPUESTOS. Las naves comienzan en orillas opuestas y regresan a su origen; se comprueban conflictos de maniobra de terminal. Veinte zarpes por sentido caben en este modelo con2h, pero no con2h40 y esa misma ventana. No es certificación de tripulación, rampa, atraque de espera, mantenimiento, clima ni horarios comerciales reales. Usuarios rechazados, espera de otro zarpe, cancelación y transferencias por capacidad quedan no identificados.

## Demanda terrestre: observaciones, no expansión poblacional

Cuatro OD iniciales, ambos sentidos, todas las unidades de encuesta (no sumar como vehículos):

{prev.mdtable(lsum)}

Total de entrevistas: {int(counts.encuestas_totales)}; barcaza confirmada por interceptación:{int(counts.barcaza_confirmada)}; tierra **por declaración explícita**:{int(counts.tierra_confirmada_por_declaracion)}; ruta desconocida:{int(counts.ruta_desconocida)}. Las desconocidas incluyen declaraciones lacustres usadas/por usar fuera del cruce: se conserva la evidencia sin convertirla en embarque confirmado. Los indicadores Argentina son adicionales y pueden solaparse con esas categorías; no se suman a ellas. Invierno sin encuestas indica ausencia de campaña, no demanda nula.

Tierra por declaración requiere control terrestre, respuesta explícita Ninguno a transbordadores y ningún campo positivo/contradictorio; no basta interceptación en carretera. Es confirmación de itinerario declarado, no verificación GPS ni prueba de ruta por Chile frente a Argentina. Las tablas por estación/OD/sentido/segmento y por punto permiten auditar el criterio. Río Ibáñez es zona/comuna, no localización inequívoca en Puerto Ibáñez.

Las dos representaciones procesadas de rutas enlazan otros candidatos, pero ninguna de las entrevistas de estos cuatro OD tiene enlace en ellas. Los conteos de Cerro Castillo se entregan por campaña/sentido/jornada y no se asignan íntegramente al OD. No se produjo demanda terrestre expandida: faltan marco de selección/no respuesta, enlace exacto de exposición y fecha de encuestas/conteos, rutas desconocidas y consolidación de controles; el flujo de un corredor no es flujo del OD exclusivamente terrestre. Los datos de invierno y marzo/abril tampoco se inventan.

CITRA se usa solo como PDF: matrices muestrales de verano sin expansión y conteos de12h, sin microdatos disponibles. Se transcribieron los cuatro OD para VL/CAM y se contrastaron con ARISTO, sin sumar muestras ni atribuir elección terrestre al total. Véase INFORME_TERRESTRE.md y E_contraste_CITRA_muestras_PDF.csv.

## Reproducción y archivos

1. `python scripts/04_actualizar_sbo.py`: prioridad, actualiza A/B/C/D con caches originales verificados.
2. `python scripts/05_investigar_demanda_terrestre.py`: clasificación y perfiles observados complementarios.
3. `python scripts/04_actualizar_sbo.py`: incorpora perfil CAM observado sin rellenar estratos sin muestra.
4. `python scripts/06_resumir_actualizacion.py`: este resumen y puntas muestrales.

Configuraciones: data/templates/config_sbo.json y config_rutas_terrestres.json. Informes:INFORME_SBO.md e INFORME_TERRESTRE.md. Todo resultado actual queda en outputs/sbo_actualizada; resultados anteriores en outputs/historico/estimacion_preliminar_2026-10-24. Los originales y caches no se versionan, ni las salidas con celdas pequeñas. No se hizo commit/push.
'''
    (OUT/'RESUMEN_ACTUALIZADO.md').write_text(documento_legible(text))
    checks={
        'cuatro_estaciones':set(a.estacion)==set(cfg['estaciones']),
        'meses_sin_perfil_no_imputados':a[a.mes.isin([3,4,6,7,8])].flujo_dia.isna().all(),
        'frecuencia_mensual_confirmada':all(r.frecuencia_ordinaria_semana==cfg['frecuencia_historica_por_mes'][str(r.mes)] for r in a.itertuples()),
        'SBO_no_inferior_a_historica':c.frecuencia_SBO.ge(c.frecuencia_historica).all(),
        'induccion_cero_supuesto':c.induccion_total_mercado.eq(0).all(),
        'oferta_no_crea_viajes':c.groupby(['mes','sentido']).demanda_lacustre_semana_fija_VL.nunique().le(1).all(),
        'tierra_no_expandida_arbitrariamente':land.flujo_terrestre_dia.isna().all(),
        'clasificacion_conserva_encuestas':(land.encuestas_totales==land.barcaza_confirmada+land.tierra_confirmada_por_declaracion+land.ruta_desconocida).all(),
        'frecuencia_economica_no_identificada':minimum.frecuencia_economicamente_optima.isna().all(),
        'missing_capacidad_no_equivale_saturacion':c.loc[c.ocupacion_ml.isna()|c.ocupacion_pax.isna(),'cumple_media_o_punta_condicional'].isna().all()
    }
    known=a.dropna(subset=['flujo_dia'])
    checks['diario_semanal_coherente']=all(math.isclose(r.flujo_dia*7,r.flujo_semana,rel_tol=1e-9) for r in known.itertuples())
    seasonal=pd.read_csv(OUT/'A_historica_estacional.csv')
    checks['otono_invierno_incompletos']=seasonal[seasonal.estacion.isin(['Otoño','Invierno'])].total_estacion.isna().all()
    manifest=pd.read_csv(ROOT/'outputs/historico/estimacion_preliminar_2026-10-24/fuentes_integridad.csv')
    checks['originales_intactos']=all(hashlib.sha256((ROOT.parent/r.fuente).read_bytes()).hexdigest()==r.sha256 for r in manifest.itertuples())
    checks['sin_identificadores_individuales_en_salidas']=all(not set(pd.read_csv(f,nrows=0).columns)&{'ID 2','Patente','Latitud','Longitud','ID'} for f in OUT.glob('*.csv'))
    cc=c.loc[c.escenario.eq('todas_20')]
    checks['veinte_viable_2h_condicionado']=cc[cc.navegacion_h.eq(2)].itinerario_constructible_condicionado.all()
    checks['veinte_no_viable_2h40_con_ventana']=not cc[cc.navegacion_h>2.6].itinerario_constructible_condicionado.any()
    types=pd.read_csv(OUT/'D_aportes_ocupacion_por_segmento.csv')
    keys=['estacion','mes','sentido','perfil','ml_Tehuelche','navegacion_h','escenario']
    sums=types.groupby(keys).aporte_ocupacion_ml.agg(lambda s:s.sum(min_count=5)).reset_index(name='suma_aportes_ml')
    join=c.merge(sums,on=keys,validate='one_to_one').dropna(subset=['ocupacion_ml','suma_aportes_ml'])
    checks['aportes_clases_conservan_ocupacion_ml']=all(math.isclose(r.ocupacion_ml,r.suma_aportes_ml,rel_tol=1e-9,abs_tol=1e-9) for r in join.itertuples())
    assert all(checks.values()),checks
    (OUT/'validacion.json').write_text(json.dumps({k:bool(v) for k,v in checks.items()},indent=2))
    print(OUT/'RESUMEN_ACTUALIZADO.md')

if __name__=='__main__':main()
