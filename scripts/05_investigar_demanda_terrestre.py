"""Clasificacion de rutas con evidencia explicita y contraste de PDF CITRA.

No convierte entrevistas externas ni matrices muestrales en flujos poblacionales.
"""
from pathlib import Path
import sys,json,math,hashlib,importlib.util
import pandas as pd
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from demanda.capacidad import documento_legible
spec=importlib.util.spec_from_file_location('prev',ROOT/'scripts/03_estimar_demanda_local.py')
prev=importlib.util.module_from_spec(spec);spec.loader.exec_module(prev)
OUT=ROOT/'outputs/sbo_actualizada'
CACHE=ROOT/'data/interim/estimacion_preliminar'

def save(df,n):df.to_csv(OUT/f'{n}.csv',index=False,encoding='utf-8-sig',na_rep='NaN')


def clasificar(row,ferry_fields,border_fields,cfg):
    values=[prev.norm(row.get(c)) for c in ferry_fields]
    negatives=set(cfg['sin_transbordador_explicito'])
    explicit=any(v in negatives for v in values)
    positives=[v for v in values if v and v not in negatives]
    lake=any(prev.es_lago(v) for v in positives)
    place=prev.norm(row['Lugar encuestado'])
    area=prev.norm(row['Lugar de Encuesta'])
    crossing=prev.es_lago(place)
    arg_control=any(t in place for t in cfg['fronteras_argentina'])
    arg_declared=any(any(t in prev.norm(row.get(c)) for t in cfg['fronteras_argentina']) for c in border_fields)
    control_terrestre=('carretera' in area or 'fronter' in area or arg_control)
    # Confirmado por declaracion explicita, sin reconstruccion GPS del recorrido.
    land=explicit and not positives and control_terrestre and not crossing
    if crossing:status='barcaza_confirmada_interceptacion'
    elif land:status='tierra_confirmada_por_declaracion_sin_transbordadores'
    else:status='ruta_desconocida'
    return dict(clase_ruta=status,lago_declarado_no_confirmado=lake and not crossing,
                argentina_interceptacion=arg_control,argentina_declarada=arg_declared,
                ningun_transbordador_explicito=explicit,contradiccion_ninguno_y_ruta=explicit and bool(positives))


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    cfg=json.loads((ROOT/'data/templates/config_rutas_terrestres.json').read_text())
    p=ROOT.parent/'Cap 6/BBDD EOD/Base de datos agregada.xlsx'
    digest=hashlib.sha256(p.read_bytes()).hexdigest()
    extras=['ID 2','Lugar de Encuesta','Longitud en metros','Ocupantes del vehículo','Tamaño del Grupo','Número de ejes','Peso de carga transportada (Toneladas)','Tipo de vehículo de carga']
    more=prev.cache_frame(p,'BBDD-1','eod_fronteras_longitudes_v2',digest,False,
        usecols=lambda c:c in extras or 'fronterizo' in str(c).lower())
    a=pd.read_pickle(CACHE/'eod_original_seleccion.pkl')
    assert (CACHE/'eod_original_seleccion.sha256').read_text()==digest
    b=pd.read_pickle(CACHE/'eod_valida_seleccion.pkl')
    d=a.merge(b,on='ID 2',validate='one_to_one').merge(more,on='ID 2',validate='one_to_one')
    ferry=[c for c in a if 'transbordador' in c.lower()]
    border=[c for c in more if 'fronterizo' in c.lower()]
    # Extremo Chile Chico o evidencia del cruce; no es elegibilidad confirmada.
    relevant=d['Nombre origen'].eq('Chile Chico')|d['Nombre destino'].eq('Chile Chico')|d['Lugar encuestado'].map(prev.es_lago)
    d=d.loc[relevant].copy()
    flags=d.apply(lambda r:pd.Series(clasificar(r,ferry,border,cfg)),axis=1)
    d=pd.concat([d,flags],axis=1)
    d['estacion']=d['Versión'].str.strip().replace({'Normal':'Otoño'})
    d['mes_registro']=pd.to_datetime(d['Día'],errors='coerce').dt.month
    d['sentido_OD']=d['Nombre origen']+' → '+d['Nombre destino']
    cats={'Auto':'VL','Camioneta':'VL','Vehículo privado':'VL','Camión o furgón de carga':'CAM','Moto':'MOTO','Pasajero (peatón)':'PEATON'}
    d['segmento']=d['Tipo usuario'].map(cats).fillna('OTRO_PASAJERO')
    d['barcaza_confirmada']=d.clase_ruta.eq('barcaza_confirmada_interceptacion')
    d['tierra_confirmada_declaracion']=d.clase_ruta.eq('tierra_confirmada_por_declaracion_sin_transbordadores')
    d['desconocida']=d.clase_ruta.eq('ruta_desconocida')
    keys=['estacion','Nombre origen','Nombre destino','sentido_OD','segmento']
    s=d.groupby(keys).agg(encuestas_totales=('ID 2','size'),barcaza_confirmada=('barcaza_confirmada','sum'),
        tierra_confirmada_por_declaracion=('tierra_confirmada_declaracion','sum'),ruta_desconocida=('desconocida','sum'),
        lago_declarado_no_confirmado=('lago_declarado_no_confirmado','sum'),argentina_interceptacion=('argentina_interceptacion','sum'),
        argentina_declarada=('argentina_declarada','sum'),meses_con_registros=('mes_registro','nunique')).reset_index()
    assert (s.encuestas_totales==s.barcaza_confirmada+s.tierra_confirmada_por_declaracion+s.ruta_desconocida).all()
    s['demanda_terrestre_expandida']=math.nan
    s['posibilidad_expansion']='no_ejecutada_sin_marco_punto_sentido_fecha_clase_exposicion_y_no_respuesta'
    save(s,'E_clasificacion_OD_estacion_segmento')
    cols=['estacion','Nombre origen','Nombre destino','sentido_OD']
    z=s.groupby(cols)[['encuestas_totales','barcaza_confirmada','tierra_confirmada_por_declaracion','ruta_desconocida','lago_declarado_no_confirmado','argentina_interceptacion','argentina_declarada']].sum().reset_index()
    core=(z['Nombre origen'].eq('Chile Chico')&z['Nombre destino'].isin(['Coyhaique','Río Ibáñez']))|(z['Nombre destino'].eq('Chile Chico')&z['Nombre origen'].isin(['Coyhaique','Río Ibáñez']))
    core=z.loc[core].copy()
    # Incluir invierno como ausencia de campana, no como demanda observada cero.
    for origin,dest in [('Chile Chico','Coyhaique'),('Coyhaique','Chile Chico'),('Chile Chico','Río Ibáñez'),('Río Ibáñez','Chile Chico')]:
        for season in ['Verano','Otoño','Invierno','Primavera']:
            if not ((core['Nombre origen']==origin)&(core['Nombre destino']==dest)&core.estacion.eq(season)).any():
                r={c:0 for c in core.columns if c not in cols};r.update(dict(zip(cols,[season,origin,dest,origin+' → '+dest])))
                core=pd.concat([core,pd.DataFrame([r])],ignore_index=True)
    core['conteos_para_explorar']='CerroCastillo_y_fronteras; ver E_encuestas_por_punto y E_conteos_CerroCastillo'
    core['flujo_terrestre_dia']=math.nan
    save(core,'E_resumen_cuatro_OD_cuatro_estaciones')
    point=d.groupby(['estacion','Lugar de Encuesta','Lugar encuestado','Sentido Viaje','segmento','clase_ruta'],dropna=False).size().reset_index(name='encuestas')
    save(point,'E_encuestas_por_punto')
    save(d.groupby(['estacion','clase_ruta','ningun_transbordador_explicito','contradiccion_ninguno_y_ruta','lago_declarado_no_confirmado','argentina_interceptacion'],dropna=False).size().reset_index(name='encuestas'),'E_reglas_y_evidencias')
    # Cruces con representaciones de rutas, solo cobertura agregada de claves.
    coverage=[]
    coremask=((d['Nombre origen'].eq('Chile Chico')&d['Nombre destino'].isin(['Coyhaique','Río Ibáñez'])) | (d['Nombre destino'].eq('Chile Chico')&d['Nombre origen'].isin(['Coyhaique','Río Ibáñez'])))
    for rel,sn in [('Cap 8/EOD_Puntos_Pasada_Final.xlsx','Puntos por OD (Ordenados)'),('Cap 8/BBDD_para_Pijas_actualizada_EOD_Final.xlsx','Arcos por OD')]:
        path=ROOT.parent/rel
        rh=hashlib.sha256(path.read_bytes()).hexdigest()
        routes=prev.cache_frame(path,sn,'rutas_'+('puntos' if 'Puntos' in sn else 'arcos'),rh,False)
        linked=d['ID 2'].isin(routes['ID 2'])
        coverage.append(dict(archivo=rel,hoja=sn,encuestas_candidatas_enlazadas=int(linked.sum()),cuatro_OD_enlazadas=int((linked&coremask).sum()),
                             uso='representacion_procesada_no_medicion_independiente'))
        # Ninguna ausencia de arco se interpreta como ruta exclusivamente terrestre.
    save(pd.DataFrame(coverage),'E_cobertura_rutas_procesadas')
    roads=pd.read_pickle(CACHE/'carretera.pkl')
    roads=roads.loc[roads.PC.eq('ODC-3')]
    road=roads.groupby(['Temporada','SENTIDO']).agg(intervalos=('CUARTO','size'),jornadas=('DÍA','nunique'),privados=('V.Privado','sum'),camiones=('Camión','sum')).reset_index()
    road['estacion']=road.Temporada.str.strip().replace({'Normal':'Otoño'})
    road['unidad']='unidades_clasificadas_durante_jornadas_medidas_no_24h'
    save(road,'E_conteos_CerroCastillo')
    # Longitudes y ocupaciones observadas: solo perfil agregado, sin claves personales.
    local=d.loc[d['Lugar encuestado'].map(prev.es_lago)].copy()
    for field,name in [('Longitud en metros','longitud_CAM_m'),('Ocupantes del vehículo','ocupantes_vehiculo')]:
        data=local.loc[local.segmento.eq('CAM')] if 'Longitud' in field else local.loc[local.segmento.isin(['VL','CAM','MOTO'])]
        value=pd.to_numeric(data[field],errors='coerce')
        data=data.assign(valor=value.where(value>0))
        prof=data.groupby(['estacion','Sentido Viaje','segmento']).agg(respuestas=('ID 2','size'),valores_positivos=('valor','count'),media=('valor','mean'),minimo=('valor','min'),maximo=('valor','max')).reset_index()
        save(prof,'B_D_perfil_observado_'+name)
    citra=pd.DataFrame(cfg['citra_muestras_pdf'],columns=['origen','destino','segmento','encuestas','fuente'])
    ar=s.loc[(s.estacion=='Verano')].groupby(['Nombre origen','Nombre destino','segmento']).encuestas_totales.sum().reset_index().rename(columns={'Nombre origen':'origen','Nombre destino':'destino','encuestas_totales':'ARISTO_encuestas_todas_rutas'})
    contrast=citra.rename(columns={'encuestas':'CITRA_encuestas_todas_rutas'}).merge(ar,on=['origen','destino','segmento'],how='left')
    contrast['expansion']='ninguna; no_suma_muestras; no_equivale_tierra'
    save(contrast,'E_contraste_CITRA_muestras_PDF')
    (OUT/'INFORME_TERRESTRE.md').write_text(documento_legible(report(core,road,contrast,pd.DataFrame(coverage),cfg)))
    assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
    print(core[['estacion','Nombre origen','Nombre destino','encuestas_totales','barcaza_confirmada','tierra_confirmada_por_declaracion','ruta_desconocida']].sort_values(['Nombre origen','Nombre destino','estacion']).to_string(index=False))


def report(core,road,contrast,coverage,cfg):
    return f'''# Investigación de viajes terrestres — 25/10/2026

## Fuentes y unidad de observación

ARISTO es fuente principal: BBDD-1 y BBDD-2 del Cap6, Transbordadores, Carretera/ODC-3 Cerro Castillo y representaciones procesadas de Cap8. Se reutilizan caches verificados por SHA256 y se leen únicamente campos adicionales de fronteras, longitud de camiones y ocupantes. No se exportan registros individuales ni coordenadas. CITRA se limita al Informe2c PDF; no se buscaron ni se presuponen microdatos de esa consultora.

Cada cifra de encuesta es una respuesta válida, no un flujo diario ni una unidad física homogénea. Se segmenta VL, CAM, MOTO, PEATON y otros pasajeros antes de cualquier comparación. El alcance amplio es extremo en Chile Chico o interceptación en el cruce: otros OD son candidatos, no elegibilidad acreditada. Río Ibáñez es el nombre zonal/comunal de BBDD-2; no implica que todos los viajes sean a la localidad Puerto Ibáñez. Estación Otoño corresponde a registros Normal de mayo, no cobertura de marzo/abril. Las filas de invierno con cero entrevistas indican ausencia de campaña, no demanda nula.

## Criterio de clasificación auditable

1. Barcaza confirmada: interceptación en Ruta Pto.Ibáñez–Chile Chico. Una declaración de transbordador usado/por usar fuera del cruce se conserva como lago declarado no confirmado, dentro de ruta desconocida hasta verificar uso efectivo.
2. Tierra confirmada **por declaración**: control de carretera/frontera y respuesta explícita Ninguno/ninguna/no utiliza transbordador/no uso transbordador en campos de transbordadores; ningún otro campo de transbordador tiene respuesta positiva ni texto adicional. No basta estar en carretera. Es evidencia de itinerario declarado sin transbordadores, no trazado GPS ni confirmación externa del recorrido. No se infiere el itinerario por Chile frente a Argentina a partir de ese negativo.
3. Argentina: dos indicadores independientes, interceptación en frontera argentina y declaración usada/por usar. Pueden coexistir con lago o tierra; no se suman a las tres categorías exclusivas de la tabla. La lista de controles y reglas está en config_rutas_terrestres.json. Un registro con ruta desconocida puede tener tramo argentino conocido sin reconstrucción completa del viaje.
4. Desconocida: todos los demás, incluidos vacíos, negativos ausentes, contradicciones y declaraciones lacustres sin interceptación. No se completa con tierra.

Las categorías barcaza+tierra por declaración+desconocida conservan el total de entrevistas. `E_reglas_y_evidencias.csv` muestra los indicadores agregados. Para una definición de confirmación limitada a verificación externa, las terrestres de esta tabla deben mantenerse como **terrestres declaradas**, no como itinerarios independientemente comprobados.

{prev.mdtable(core[['estacion','Nombre origen','Nombre destino','encuestas_totales','barcaza_confirmada','tierra_confirmada_por_declaracion','ruta_desconocida']])}

## Rutas y puntos de pasada

Se enlazaron ID2 con Puntos por OD (Ordenados) y Arcos por OD. Son transformaciones de encuestas, no una muestra nueva. La cobertura hallada es:

{prev.mdtable(coverage)}

Los campos disponibles incluyen Ruta OD, OD-Nodos del recorrido, Nodos_Pasada, Transb1…6, Ruta1…4 y Paso Fronterizo1…4. En los cuatro OD principales, la cobertura indicada arriba determina si hay representación para examinar. No se interpretó ausencia de arco como prueba de tierra ni se asignó una ruta de otra encuesta al OD local. No se reconstruyó una ruta terrestre a partir de una red de mínimo costo como si fuera la ruta elegida observada.

## Conteos y expansión

{prev.mdtable(road)}

Son conteos de corredor, incluyendo viajes de otros OD y combinaciones carretera/barcaza. Su unidad es jornada medida, no24h. El archivo usa Día1/Día2 y CUARTO, no fecha calendario completa por fila. La tabla E_encuestas_por_punto conserva estación, punto, sentido y clase para cotejar con esos conteos; no se asigna el total de Cerro Castillo a Chile Chico–Coyhaique. Las categorías privados de conteos y VL de encuestas necesitan reconciliar motos/bicicletas y pasajeros de bus/van, como se documentó en la fase previa.

No se implementó expansión terrestre poblacional. Faltan: correspondencia comprobada de fecha/jornada y horas de selección EOD con cada conteo, definición de elegibilidad y selección por clase, tratamiento de no respuesta y probabilidad de interceptación, ruta de los desconocidos, cobertura de caminos/Argentina y regla de consolidación de controles en serie. Aun donde hay negativa explícita de transbordador, esas entrevistas no proporcionan por sí solas el universo de OD local. Una proporción bruta de entrevistados de carretera no es una probabilidad de inclusión. Para diarios completos y cuatro estaciones se requieren además exposición24h/calendario y campañas faltantes. Se entregan las observaciones muestrales y los conteos, con demanda terrestre expandida NaN, no cero.

## Contraste complementario CITRA

CITRA Informe2c §6.1, pp75–90: campaña20/01–05/02/2026; matrices muestrales sin expansión (Cuadros2/3), conteos por hora08:00–20:00 en Cuadros4/5. La transcripción y su fuente están en la configuración, separadas de los cálculos ARISTO.

{prev.mdtable(contrast)}

Las diferencias describen muestras con puntos, días, coberturas y clasificaciones distintas; no se interpretan como diferencias poblacionales ni como cuotas terrestres. Los ceros publicados son celdas de la muestra, no prueba de ausencia de viajes. El PDF no permite recuperar la elección lacustre/terrestre por persona de esos cuadros. No se suman muestras ni se generan pesos para CITRA. No se usan sus conteos de carretera como OD exclusivamente terrestre.

## Continuidad del modelo

Demanda terrestre expandida, transferencia tierra→barcaza y demanda no atendida continúan no identificadas. Esto no bloquea los resultados de oferta/capacidad del paso04: el mercado se mantiene fijo por instrucción y no se computa captación del proyecto sin CG/elección. Los perfiles agregados de longitud de camión y ocupantes observados se entregan para revisar las sensibilidades del módulo de capacidad; no se imputan a estratos sin respuesta ni a pasajeros de vehículos contados otra vez como peatones.

Reproducción: `python scripts/05_investigar_demanda_terrestre.py`. Informe SBO y tablas A–D en esta misma carpeta; configuración de rutas/capturas de PDF en data/templates/config_rutas_terrestres.json. No se modificaron originales ni se realizó commit/push.
'''


if __name__=='__main__':main()
