"""Etapa13: completa mercados y aplica inducción por perfil sin recalibrar.

Lee exclusivamente resultados07–12, sin reconstruir atributos o abrir microdatos
originales. Detalle local; publicación agregada por intervalos y selección segura.
"""
from pathlib import Path
import argparse
import calendar
import hashlib
import importlib.util
import json
import sys

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from demanda.induccion import respuesta_perfiles
from demanda.proyecto import desviar

K=['origen','destino','estacion','segmento']
ALTS=['terrestre_chile','barcaza_actual','bahia_jara_levican']
NAN=float('nan')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(n):
    return pd.read_csv(ROOT/'outputs'/(n+'.csv'))


def one(d, keys):
    for k,v in keys.items():
        d=d.loc[d[k].eq(v)]
    if len(d)>1:
        raise ValueError(f'Celda duplicada {keys}')
    return d.iloc[0] if len(d) else None


def value(d,keys,col):
    r=one(d,keys)
    return float(r[col]) if r is not None else NAN


def datos():
    return dict(bar=read('matrices_od_referencia/matriz_od_barcaza'),
                tierra=read('matrices_od_referencia/matriz_od_terrestre'),
                temporal=read('expansion_temporal_terrestre/matrices_24h_sensibilidades'),
                factores=read('expansion_temporal_terrestre/factores_10h_24h_y_cobertura'),
                historica=read('calibracion_logit_11b/probabilidades_base_recalibradas'),
                mercado12=read('etapa12/demanda_desviada_por_alternativa'),
                oferta12=read('etapa12/sensibilidad_proyecto').drop_duplicates(K+['escenario']),
                attrs=read('atributos_logit_actualizados/atributos_logit_actualizados'),
                sbo=read('etapa12/atributos_sbo'),nuevo=read('etapa12/atributos_bahia_jara_levican'))


def factor_temporal(d,c,s):
    donor=c['factor_mayo_donante'] if s in ['Otoño','Invierno'] else s
    v=value(d['factores'],dict(perfil=c['perfil_temporal'],estacion_destino=donor),'factor_24h_10h_sensibilidad')
    if not np.isfinite(v) or v<=0:
        raise ValueError('Factor temporal sin configurar')
    return v*c['factor_temporal_multiplicador']


def imputar_barcaza(q,p,c):
    raw=p*c['multiplicador_participacion_imputacion']
    used=float(np.clip(raw,c['probabilidad_minima_imputacion'],1))
    if not np.isfinite(q+raw) or q<0:
        return NAN,used,False
    return q/used,used,not np.isclose(raw,used)


def completar(d,c):
    rows={}; seeds={}
    for o,z in c['od']:
        for s in c['estaciones']:
            for seg,unit in c['segmentos'].items():
                key=(o,z,s,seg); keys=dict(zip(K,key))
                qm=value(d['bar'],keys,'demanda_diaria_24h_equivalente')
                qt=value(d['tierra'],keys,'demanda_expandida_viajes_diarios_promedio')
                ph=value(d['historica'],dict(keys,alternativa='barcaza_actual'),'probabilidad')
                total=anchor=NAN; method='sin_antecedente'; piso=False; pu=NAN
                scope='servicio_lacustre_sin_mercado_eleccion' if seg=='PEATON' and 'Puerto Ibáñez' in (o,z) else 'mercado_eleccion'
                f=factor_temporal(d,c,s)
                if scope=='mercado_eleccion' and s!='Invierno':
                    if seg in ['VL','CAM'] and np.isfinite(qm+qt) and (c['imputaciones_activas'] or s in ['Verano','Primavera']):
                        total=qm+qt*f; anchor=qm+qt
                        method='A_ferry_expandido_mas_tierra24h_sensibilidad'
                    elif seg=='PEATON' and np.isfinite(qm) and c['imputaciones_activas']:
                        proxy=one(d['mercado12'],dict(keys,alternativa=ALTS[2],escenario_mercado='PEATON_imputado_cuota_VL'))
                        pproxy=qm/proxy.demanda_total_OD if proxy is not None and np.isfinite(proxy.demanda_total_OD) else NAN
                        share=pproxy if c['peaton_metodo'].startswith('proxy_etapa12') and np.isfinite(pproxy) else ph
                        total,pu,piso=imputar_barcaza(qm,share,c);anchor=qm
                        method='B_peaton_cuota_proxy_VL12' if np.isfinite(pproxy) and share==pproxy else 'B_ferry_dividido_P_historica11B'
                    elif np.isfinite(qm) and c['imputaciones_activas']:
                        total,pu,piso=imputar_barcaza(qm,ph,c);anchor=qm
                        method='B_ferry_dividido_P_historica11B'
                elif scope.startswith('servicio') and np.isfinite(qm):
                    method='servicio_personas_expandido_NO_total_mercado'
                mayo= s=='Otoño'
                # Mayo representa marzo-mayo por instrucción13, nunca dato otoñal medido completo.
                scale=c['multiplicador_perfil_mayo'] if mayo else 1
                if np.isfinite(total):
                    total*=scale
                    if seg=='PEATON':total*=c['multiplicador_peaton']
                row=dict(keys, sentido=o+' → '+z, unidad=unit, ambito=scope,
                         demanda_total_OD=total, demanda_servicio_lacustre=qm if scope.startswith('servicio') else NAN,
                         ferry_expandido_fuente=qm,tierra10h_fuente=qt,factor10_24=f,
                         P_historica=ph,P_imputacion_utilizada=pu,limite_P_aplicado=piso,
                         metodo=method,estacion_donante=s,od_donante=o+' → '+z,
                         ancla_expandida_dia=min(anchor,total) if np.isfinite(anchor+total) else 0 if np.isfinite(total) else NAN,
                         estado_estacional='mayo_transferido_a_marzo_mayo' if mayo else 'perfil_campana_de_estacion',
                         fuente='matrices07; sensibilidad08; P_historica11B; mercado_proxy12')
                rows[key]=row
                if np.isfinite(total):seeds[key]=row.copy()
    if c['imputaciones_activas']:
        # Transferencias propias: primero se completan los dos mercados conCoyhaique
        # y todos losVL, sin usar jamás la dirección opuesta como sustituto automático.
        for key,row in rows.items():
            o,z,s,seg=key
            if row['ambito']!='mercado_eleccion' or np.isfinite(row['demanda_total_OD']):continue
            for ds in c['prioridad_estaciones_donantes'][s]:
                donor=seeds.get((o,z,ds,seg))
                if donor is None:continue
                row.update(demanda_total_OD=donor['demanda_total_OD']*c['multiplicador_transferencia'][s],
                           metodo='C_transferencia_misma_OD_y_sentido',estacion_donante=ds,
                           ancla_expandida_dia=0,estado_estacional='mercado_transferido; oferta_destino_conservada')
                break
        # CAM dePuertoIbáñez sin ninguna observación: razón de mercadosVL de esa
        # dirección sobre el OD comparableCoyhaique, no cuota de captación arbitraria.
        for key,row in rows.items():
            o,z,s,seg=key
            if seg!='CAM' or np.isfinite(row['demanda_total_OD']):continue
            forward=o=='Chile Chico'; co=('Chile Chico','Coyhaique') if forward else ('Coyhaique','Chile Chico')
            donor=rows[(*co,s,'CAM')];vl_local=rows[(o,z,s,'VL')];vl_co=rows[(*co,s,'VL')]
            vals=[donor['demanda_total_OD'],vl_local['demanda_total_OD'],vl_co['demanda_total_OD']]
            if np.isfinite(vals).all() and vals[2]>0:
                row.update(demanda_total_OD=vals[0]*vals[1]/vals[2],metodo='D_CAM_OD_comparable_razon_mercados_VL',
                           od_donante=co[0]+' → '+co[1],estacion_donante=s,ancla_expandida_dia=0,
                           estado_estacional='transferencia_tamano_mercado_NO_CAM_medido_PI')
        # Servicio personalPI separado: completar su perfil, sin inventar elección.
        for key,row in rows.items():
            o,z,s,seg=key
            if not row['ambito'].startswith('servicio'):continue
            q=row['demanda_servicio_lacustre']
            if np.isfinite(q):
                if s=='Otoño':q*=c['multiplicador_perfil_mayo']
            else:
                for ds in c['prioridad_estaciones_donantes'][s]:
                    donor=rows[(o,z,ds,seg)]
                    if np.isfinite(donor['ferry_expandido_fuente']):
                        q=donor['ferry_expandido_fuente']*c['multiplicador_transferencia'][s]
                        if ds=='Otoño':q*=c['multiplicador_perfil_mayo']
                        row.update(metodo='C_servicio_lacustre_transferido_NO_mercado',estacion_donante=ds)
                        break
            row['demanda_servicio_lacustre']=q*c['multiplicador_peaton']
    for row in rows.values():
        total=row['demanda_total_OD'];row['componente_imputado_dia']=total-row['ancla_expandida_dia']
        row['porcentaje_anclado_expansion']=100*row['ancla_expandida_dia']/total if np.isfinite(total) and total>0 else NAN
        row['porcentaje_dependiente_supuestos']=100-row['porcentaje_anclado_expansion']
    return pd.DataFrame(rows.values())


def cargar_perfiles(d,c):
    spec=importlib.util.spec_from_file_location('et12_reutilizada',ROOT/'scripts/14_aplicar_etapa12.py')
    oldstage=importlib.util.module_from_spec(spec);spec.loader.exec_module(oldstage)
    old=json.loads((ROOT/'outputs/calibracion_logit/config_utilizada.json').read_text())
    bases={s:read('calibracion_logit_11b/base_reutilizada_'+s) for s in c['segmentos']}
    result={}
    for key,pair in d['attrs'].groupby(K,sort=False):
        keys=dict(zip(K,key));seg=keys['segmento']
        if seg=='PEATON' and 'Puerto Ibáñez' in key[:2]:continue
        x,w,method=oldstage.perfiles(pair,bases,keys,old)
        sr=one(d['sbo'],dict(keys,alternativa=ALTS[1]));nr=one(d['nuevo'],keys)
        xs=x.copy();xs[:,1,2]=sr.t_horario_h
        n=np.tile(nr[['C_privado_CLP_dic2025','t_viaje_h','t_horario_h','t_acceso_h']].to_numpy(float),(len(w),1))
        if seg!='PEATON':
            # Mismos pagadores/longitudes11B: soloCOV de la ruta cambia en12.
            n[:,0]+=xs[:,1,0]-np.average(xs[:,1,0],weights=w)
        xp=np.concatenate([xs,n[:,None,:]],axis=1)
        result[key]=dict(xs=xs,xp=xp,pesos=w,betas=np.array([sr.beta_c,sr.beta_t,sr.beta_e,sr.beta_a]),
                         asc=sr.ASC,perfil=method,tarifa=xs[:,1,0]-sr.COV if seg!='PEATON' else np.repeat(old['tarifa_barcaza_adulto']*old['factor_IPC_tarifa'],len(w)))
    return result


def evaluar_perfiles(base,keys,c,c12):
    offer=c['escenario_oferta12']; change=c12['sensibilidades'].get(offer,{})
    xs=base['xs'].copy();xp=base['xp'].copy();seg=keys['segmento']
    # Se perturban únicamente los componentes de escenarios ya definidos en12;
    # no se recalculan distancias, red niCOV de arcos.
    if 'tarifa_factor' in change:xp[:,2,0]+=base['tarifa']*(change['tarifa_factor']-1)
    if 'navegacion_h' in change:xp[:,2,1]+=change['navegacion_h']-c12['navegacion_h']
    if 'desembarque_h' in change:xp[:,2,1]+=change['desembarque_h']-c12['desembarque_h']
    if 'nuevo_f_semana_sentido' in change:xp[:,2,2]=c12['w']*168/change['nuevo_f_semana_sentido']
    if 'velocidad_X735_kmh' in change:xp[:,2,3]+=c12['longitud_norte_km']*(1/change['velocidad_X735_kmh'][seg]-1/c12['velocidad_X735_kmh'][seg])
    eps=c['elasticidades'][seg] if c['induccion_activa'] else 0
    return respuesta_perfiles(xs,xp,base['pesos'],base['betas'],base['asc'],eps,
        lam=change.get('lambda_lago',c12['lambda_lago']),delta_asc_nuevo=change.get('delta_ASC_nuevo',0),
        max_reduccion=c['max_reduccion_cg'],formula=c['formula_induccion'],factor_cg=c['factor_cg_referencia'])


def aplicar(matrix,profiles,c,c12):
    sbo=[];proj=[];dev=[];ind=[];diag=[];annual=[]
    for row in matrix.to_dict('records'):
        keys={k:row[k] for k in K};key=tuple(keys.values());total=row['demanda_total_OD']
        days=sum(calendar.monthrange(c['ano'],m)[1] for m in c['estaciones'][row['estacion']])
        common=dict(keys,sentido=row['sentido'],unidad=row['unidad'],ambito=row['ambito'],dias_estacion=days)
        if key not in profiles:
            annual.append(dict(common,alternativa='servicio_lacustre_sin_asignacion',tipo_demanda='referencia_servicio_sin_mercado',
                               demanda_diaria=row['demanda_servicio_lacustre'],demanda_anual=row['demanda_servicio_lacustre']*days))
            for alt in ALTS:
                proj.append(dict(common,alternativa=alt,existente_redistribuida=NAN,inducida=NAN,total_con_proyecto=NAN,probabilidad=NAN))
                ind.append(dict(common,alternativa=alt,demanda_inducida_diaria=NAN,probabilidad_inducidos=NAN,asignacion='sin_mercado_eleccion_NO_cero'))
                if alt!=ALTS[2]:sbo.append(dict(common,alternativa=alt,probabilidad=NAN,demanda_diaria=NAN))
                for typ in ['SBO','existente_redistribuida','inducida','total_con_proyecto']:
                    annual.append(dict(common,alternativa=alt,tipo_demanda=typ,demanda_diaria=NAN,demanda_anual=NAN))
            dev.append(dict(common,demanda_total_OD=NAN,nuevo_desde_tierra=NAN,nuevo_desde_barcaza=NAN,captacion_existente=NAN,nuevo_inducido=NAN,nuevo_total=NAN))
            continue
        r=evaluar_perfiles(profiles[key],keys,c,c12)
        ds=total*r['p_sbo'];existing=total*r['p_proyecto'];extra=total*r['inducida_por_unidad'];dp=existing+extra
        losses=desviar(total,r['p_sbo'],r['p_proyecto'])
        diag.append(dict(common,**{k:v for k,v in r.items() if not isinstance(v,np.ndarray)},
                         epsilon=c['elasticidades'][row['segmento']] if c['induccion_activa'] else 0,
                         existente=total,inducida=float(extra.sum()),total_con_proyecto=float(dp.sum()),
                         diferencia_induccion_media_vs_perfil=total*(r['factor_transformacion_media']-r['factor_total']),
                         ancla_expandida=row['ancla_expandida_dia'],componente_imputado=row['componente_imputado_dia']))
        dev.append(dict(common,demanda_total_OD=total,nuevo_desde_tierra=losses[0],nuevo_desde_barcaza=losses[1],
                        captacion_existente=existing[2],nuevo_inducido=extra[2],nuevo_total=dp[2]))
        for j,alt in enumerate(ALTS):
            if j<2:sbo.append(dict(common,alternativa=alt,probabilidad=r['p_sbo'][j],demanda_diaria=ds[j]))
            proj.append(dict(common,alternativa=alt,probabilidad=r['p_proyecto'][j],existente_redistribuida=existing[j],inducida=extra[j],total_con_proyecto=dp[j]))
            ind.append(dict(common,alternativa=alt,demanda_inducida_diaria=extra[j],probabilidad_inducidos=extra[j]/extra.sum() if extra.sum()>0 else NAN,
                            asignacion='sum_perfil_D*w*(factor-1)*Pproyecto_perfil'))
            for typ,val in [('SBO',ds[j] if j<2 else 0 if np.isfinite(total) else NAN),('existente_redistribuida',existing[j]),('inducida',extra[j]),('total_con_proyecto',dp[j])]:
                annual.append(dict(common,alternativa=alt,tipo_demanda=typ,demanda_diaria=val,demanda_anual=val*days))
    return {n:pd.DataFrame(a) for n,a in [('demanda_sbo',sbo),('demanda_con_proyecto',proj),('demanda_desviada',dev),('demanda_inducida',ind),('demanda_total_anual',annual),('diagnostico_induccion',diag)]}


def totales(t):
    a=t['demanda_total_anual'];d=t['demanda_desviada'];g=t['diagnostico_induccion'];rows=[]
    for seg,unit in [('VL','vehiculos_livianos'),('CAM','camiones'),('PEATON','personas_a_pie')]:
        ag=a.loc[(a.segmento==seg)&(a.ambito=='mercado_eleccion')]
        gg=g.loc[g.segmento.eq(seg)];dd=d.loc[d.segmento.eq(seg)]
        sums=lambda typ:ag.loc[ag.tipo_demanda.eq(typ),'demanda_anual'].sum(min_count=1)
        n=lambda col:(dd[col]*dd.dias_estacion).sum(min_count=1)
        ancla=(gg.ancla_expandida*gg.dias_estacion).sum(min_count=1)
        total=sums('SBO')
        rows.append(dict(segmento=seg,unidad=unit,existente_anual=total,captada_existente_anual=n('captacion_existente'),
                         desde_tierra_anual=n('nuevo_desde_tierra'),desde_barcaza_anual=n('nuevo_desde_barcaza'),
                         inducida_anual=sums('inducida'),total_con_proyecto_anual=sums('total_con_proyecto'),
                         nuevo_inducido_anual=n('nuevo_inducido'),nuevo_total_anual=n('nuevo_total'),
                         ancla_expandida_anual=ancla,porcentaje_anclado_expansion=100*ancla/total,
                         porcentaje_dependiente_supuestos=100*(1-ancla/total),
                         mercados_estimados=int(gg.existente.notna().sum()),mercados_sin_eleccion=8 if seg=='PEATON' else 0))
    return pd.DataFrame(rows)


def markdown(d):
    def f(x):
        if pd.isna(x):return 'NaN'
        if isinstance(x,(float,np.floating)):return f'{x:,.3f}'
        return str(x).replace('|','/').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(d.columns)+' |','| '+' | '.join(['---']*len(d.columns))+' |']+['| '+' | '.join(f(v) for v in r)+' |' for r in d.itertuples(index=False,name=None)])


def supuestos(c):
    rows=[]
    for k,v in c.items():
        if k in ['sensibilidades','justificaciones']:continue
        alts={name:ch[k] for name,ch in c['sensibilidades'].items() if k in ch}
        rows.append(dict(supuesto=k,central=json.dumps(v,ensure_ascii=False),alternativas=json.dumps(alts,ensure_ascii=False),
                         justificacion=c['justificaciones'].get(k,'Configuración13; conserva parámetros/atributos12 salvo sensibilidad explícita'),
                         procedencia='instruccion_equipo13; resultados07-12',naturaleza='supuesto_editable_NO_observacion'))
    rows += [dict(supuesto=k,central=v,alternativas='',justificacion=v,procedencia='equipo13/EVALSO/resultadosprevios',naturaleza='criterio_metodologico') for k,v in c['justificaciones'].items()]
    return pd.DataFrame(rows)


def informe_local(out,m,t,tot,sens,c,checks):
    season=t['demanda_total_anual'];season=season.loc[season.ambito.eq('mercado_eleccion')].groupby(['segmento','unidad','estacion','tipo_demanda'],sort=False).agg(diaria=('demanda_diaria',lambda s:s.sum(min_count=1)),anual=('demanda_anual',lambda s:s.sum(min_count=1))).reset_index()
    services=t['demanda_total_anual'].loc[lambda a:a.tipo_demanda.eq('referencia_servicio_sin_mercado')]
    summary='''# Demanda preliminar — Etapa13 (detalle local reservado)

Estimación cuantitativa bajo supuestos, no medición nueva ni evaluación social. Se reutilizan resultados07–12, las pendientes yASC11B sin recalibrar y la oferta centralP-20a de12. Argentina excluida. Los números siguientes NO se publican íntegramente: incluyen celdas reservadas.

## Totales anuales de mercados de elección

'''+markdown(tot)+'''

Existente actual ySBO tienen el mismo mercado total;SBO solo redistribuye. Captada existente es parte de ese mercado, no viajes adicionales. Totalproyecto=existente+inducida. Nuevo total=captada existente+nuevo inducido. No sumar segmentos:VL yCAM son vehículos distintos;PEATON son personas sin ocupantes vehiculares duplicados.

PEATON cubre ocho mercados ChileChico↔Coyhaique. Las otras ocho celdas PuertoIbáñez↔ChileChico se reportan como servicio lacustre separado, sin alternativa terrestre inventada ni asignación automática al ferry. No hay estimación de captación/inducción para esas ocho celdas; los totalesPEATON no son totales completos de todos losOD.

## Por temporada, en sus unidades separadas

'''+markdown(season)+'''

No sumar las medias diarias entre estaciones como si fueran un mismo día. Los anuales usan días exactos del calendario de referencia: verano90, otoño92, invierno92, primavera91 (2026). No hay crecimiento futuro añadido.

## Demanda porOD, sentido y estación

'''+markdown(t['demanda_desviada'])+'''

## Servicio personal que queda fuera de elección

'''+markdown(services)+'''

Estos flujos son una referencia de servicio, no mercado de elección. No se suman a la demanda total con proyecto ni se supone inducción cero: el resultado de proyecto es desconocido.

## Construcción del mercado y evidencia

'''+markdown(m[K+['demanda_total_OD','demanda_servicio_lacustre','metodo','estacion_donante','od_donante','P_historica','P_imputacion_utilizada','porcentaje_anclado_expansion']])+'''

PrioridadA: ferry expandido+tierra24h de sensibilidad. CAM transfiere factorVL de misma campaña. Como no existe factorVL de mayo, se adopta el de primavera del perfil elegido para ambas clases y se marca supuesto. PrioridadB: ferry/P histórica11B (nuncaSBO), piso0.05 configurable;PEATON conserva proxy12 cuando existe y usaP histórica11B en el resto. PrioridadC: mayo representa otoño; invierno copia mercado de mayo de la misma dirección. Faltantes de otras estaciones toman primero otra estación del mismoOD/sentido. CAMPI sin antecedentes toma razón de tamañosVL respecto al ODCoyhaique de esa dirección. No se impone simetría ni se cambiaRíoIbáñez/comuna porPuertoIbáñez/localidad.

El porcentaje anclado en expansión identifica componentes de cantidad del perfil fuente: ferry observado-expandido y tierra10h expandida, antes del componente10-24h. El resto incluye reconstrucción por cuota,24h adicional y transferencias. No es porcentaje de días del año medidos, precisión estadística ni garantía de representatividad. La anualización de todos los perfiles es condicional; incluso lo anclado contiene hipótesis de expansión. En estaciones transferidas el anclaje de destino es0, aunque la fuente donante sí tenga registros. No se confunden registros, viajes expandidos y supuestos.

## Inducción y heterogeneidad

EVALSO Informe2 §3.4 ecuaciones3.10–3.17: se usaCG positivo esperadoSBO, calculado por perfil como suma deP_SBO por [C+(beta_t/beta_c)t+(beta_e/beta_c)e+(beta_a/beta_c)a]. Previo y desembarque ya están ent; no se suman otra vez. Valores privados implícitos10000CLP/viaje-h y15000CLP/acceso-h yhorario-h, por unidad de decisión; no valores sociales ni por ocupante.

Beneficio=(LSproyecto−LSSBO)/abs(beta_c), r=beneficio/CGref. Cociente=1−r, factor=(1−r)^epsilon; inducción=max(0,D*(factor−1)). ASC y entropía están en la diferencia de logsums pero no se suman alCG positivo. No se corrigeASC para hacer positivo el logsum. Si r supera el límite configurable0.95 se limita y se registra; se compara0.80/0.99. Cocientes no positivos sin límite se cuentan explícitamente. Se calcula por perfil y luego se pondera; inducidos de cada perfil se distribuyen por susPproyecto. La transformación de la media se conserva solo como diagnóstico de sesgo, no resultado central.

Elasticidades transferidas/supuestas:VL−0.354,CAM−0.106,PEATON−0.80. La última procede de la instrucción13 y sustituye el escenario sin inducción peatonal del PDF. El contraste2.5–5.1% no se impone como objetivo. Sensibilidad local usa1−epsilon*r, con los mismos perfiles.

'''+markdown(t['diagnostico_induccion'][K+['cg_referencia','beneficio','r_media','r_max','n_perfiles','n_limitados','peso_cociente_invalido_sin_limite','factor_total','factor_transformacion_media']])+'''

## Sensibilidades anuales

'''+markdown(sens)+'''

## Validación y reproducción

'''+json.dumps(checks,ensure_ascii=False,indent=2)+'''

Ejecutar `.venv/bin/python scripts/15_estimar_demanda_preliminar.py`. Configuración editable `data/templates/config_etapa13.json`; pruebas solo sintéticas. Los archivos anteriores se controlan mediante hashes antes/después. No se ejecutan07–12 ni se abre/reestima el modelo. Pendientes: calidad y cobertura de los mercados, terminales y estándar vial, tiempos/tarifas, capacidad/flota adicional, validación de elasticidades y ocho mercados personales sin alternativa terrestre modelada.
'''
    (out/'RESUMEN_DEMANDA_PRELIMINAR.md').write_text(summary,encoding='utf-8')


def auditar_intervalos(public, matrix, scenarios, c):
    """Ataque conservador por programación lineal sobre mercados diarios.

    Se supone conocido incluso el coeficiente privado de respuesta de cada
    mercado, las relaciones de transferencia y el ejemplo ya divulgado. Se exige
    que los intervalos conjuntos no determinen las demás celdas ni las acoten
    a menos de la amplitud relativa configurada. No es privacidad diferencial.
    """
    from scipy.optimize import linprog
    audit=[]
    mapping={'existente_anual':'demanda_total_OD','captada_existente_anual':'captacion_existente',
             'desde_tierra_anual':'nuevo_desde_tierra','desde_barcaza_anual':'nuevo_desde_barcaza',
             'inducida_anual':'inducida','total_con_proyecto_anual':'total_con_proyecto',
             'nuevo_inducido_anual':'nuevo_inducido','nuevo_total_anual':'nuevo_total'}
    for seg in c['segmentos']:
        m=matrix.loc[matrix.segmento.eq(seg)&matrix.ambito.eq('mercado_eleccion')].reset_index(drop=True)
        keys=list(map(tuple,m[K].to_numpy()));amount=m.demanda_total_OD.to_numpy(float)
        inequalities=[];bounds=[];equalities=[];targets=[]
        for pubrow in public.loc[public.segmento.eq(seg)].itertuples():
            tt=scenarios[pubrow.escenario]
            table=tt['diagnostico_induccion'] if pubrow.concepto in ['inducida_anual','total_con_proyecto_anual'] else tt['demanda_desviada']
            coef=[]
            for key,total in zip(keys,amount):
                rr=one(table,dict(zip(K,key)));val=float(rr[mapping[pubrow.concepto]])
                coef.append(val*rr.dias_estacion/total)
            inequalities.extend([coef,[-x for x in coef]])
            bounds.extend([pubrow.limite_superior,-pubrow.limite_inferior])
        for i,r in m.iterrows():
            if r.metodo.startswith('C_'):
                donor=(r.origen,r.destino,r.estacion_donante,seg)
            elif r.metodo.startswith('D_'):
                donor=tuple(r.od_donante.split(' → '))+ (r.estacion,seg)
            else:continue
            j=keys.index(donor);eq=np.zeros(len(keys));eq[i]=1;eq[j]=-amount[i]/amount[j]
            equalities.append(eq);targets.append(0)
        known=('Chile Chico','Coyhaique','Verano','VL')
        if known in keys:
            i=keys.index(known);eq=np.zeros(len(keys));eq[i]=1;equalities.append(eq);targets.append(amount[i])
        if seg=='VL':
            # La cuota global11B ya publicada vincula los tres mercados de su
            # soporte. Se incorpora también este dato previo al ataque conjunto.
            fits=read('calibracion_logit_11b/ajuste_recalibraciones')
            cuota=value(fits,dict(segmento='VL',escenario='central'),'cuota_predicha')
            previous=read('calibracion_logit_11b/probabilidades_base_recalibradas')
            eq=np.zeros(len(keys))
            for k in [('Chile Chico','Coyhaique','Verano','VL'),('Chile Chico','Coyhaique','Primavera','VL'),('Coyhaique','Chile Chico','Primavera','VL')]:
                eq[keys.index(k)]=value(previous,dict(zip(K,k),alternativa=ALTS[1]),'probabilidad')-cuota
            assert abs(eq@amount)<1e-8
            equalities.append(eq);targets.append(0)
        for i,key in enumerate(keys):
            if key==known:continue
            objective=np.zeros(len(keys));objective[i]=1
            args=dict(A_ub=np.array(inequalities),b_ub=np.array(bounds),
                      A_eq=np.array(equalities) if equalities else None,b_eq=np.array(targets) if targets else None,
                      bounds=[(0,None)]*len(keys),method='highs')
            lo=linprog(objective,**args);hi=linprog(-objective,**args)
            if not lo.success or not hi.success:
                raise ValueError('No se pudo auditar divulgación conjunta de intervalos')
            width=(-hi.fun-lo.fun)/amount[i]
            audit.append(dict(zip(K,key),amplitud_relativa_factible=width,
                              seguro=bool(width>=c['publicacion']['minimo_ancho_relativo_celda_reservada'])))
    audit=pd.DataFrame(audit)
    if not audit.seguro.all():
        raise ValueError('La selección pública acota demasiado celdas reservadas: ampliar intervalos antes de publicar')
    return audit


def publicar(out,c,tot,sens,assumptions,matrix,scenarios):
    pub=ROOT/c['salida_publica'];pub.mkdir(parents=True,exist_ok=True)
    cols=['existente_anual','captada_existente_anual','desde_tierra_anual','desde_barcaza_anual','inducida_anual','total_con_proyecto_anual','nuevo_inducido_anual','nuevo_total_anual']
    def intervalos(frame):
        rows=[]
        for r in frame.to_dict('records'):
            step=c['publicacion']['unidad_intervalo_anual'][r['segmento']]
            for col in cols:
                v=r[col]
                low=float(np.floor(v/step)*step) if np.isfinite(v) else NAN
                rows.append(dict(escenario=r.get('escenario','central'),segmento=r['segmento'],unidad=r['unidad'],concepto=col,
                                 limite_inferior=low,limite_superior=low+step,intervalo='[inferior,superior)',
                                 cobertura='16_mercados_vehiculares' if r['segmento']!='PEATON' else '8_mercados_Coyhaique;8_PI_sin_estimacion_eleccion'))
        return pd.DataFrame(rows)
    assert tot.mercados_estimados.ge(c['publicacion']['numero_minimo_mercados_agrupados']).all()
    annual=intervalos(tot)
    sensitivity=intervalos(sens.loc[sens.escenario.isin(c['publicacion']['escenarios_sensibilidad_publicables'])])
    audit=auditar_intervalos(pd.concat([annual,sensitivity]),matrix,scenarios,c)
    audit.to_csv(out/'auditoria_divulgacion_intervalos.csv',index=False)
    annual.to_csv(pub/'totales_anuales_intervalos.csv',index=False,encoding='utf-8-sig')
    sensitivity.to_csv(pub/'sensibilidades_intervalos.csv',index=False,encoding='utf-8-sig')
    assumptions.to_csv(pub/'supuestos_centrales.csv',index=False,encoding='utf-8-sig')
    # Detalle de un único mercado previamente divulgado, sin otras celdas ni totalescomplementarios.
    p=read('etapa12/sensibilidad_proyecto')
    p=p.loc[p.escenario.eq('central')&p.origen.eq('Chile Chico')&p.destino.eq('Coyhaique')&p.segmento.eq('VL')&p.estacion.eq('Verano')]
    detail=pd.read_csv(out/'demanda_con_proyecto.csv')
    detail=detail.loc[detail.origen.eq('Chile Chico')&detail.destino.eq('Coyhaique')&detail.segmento.eq('VL')&detail.estacion.eq('Verano')]
    detail.to_csv(pub/'ejemplo_vl_verano.csv',index=False,encoding='utf-8-sig')
    display=[]
    labels={'existente_anual':'Existente ySBO','captada_existente_anual':'Desviada al nuevo cruce',
            'inducida_anual':'Inducida, todo el mercado','total_con_proyecto_anual':'Total con proyecto',
            'nuevo_total_anual':'Total nuevo cruce'}
    for seg in c['segmentos']:
        rr={'Segmento':seg}
        for key,label in labels.items():
            ar=annual.loc[annual.segmento.eq(seg)&annual.concepto.eq(key)].iloc[0]
            rr[label]=f'{ar.limite_inferior:,.0f} a <{ar.limite_superior:,.0f}'
        display.append(rr)
    text='''# Demanda preliminar — Etapa13

Primera estimación bajo supuestos editables; sin recalibrar11B ni reconstruir atributos12. Se separan demanda existente redistribuida, inducida y total. Argentina excluida. La cobertura vehicular comprende los cuatroOD dirigidos y las cuatro estaciones. EnPEATON se estiman ocho mercadosChileChico↔Coyhaique; las ocho celdasPuertoIbáñez se mantienen como servicio observado/transferido aparte, sin inventar un bus ni forzar elección del ferry.

## Totales anuales preliminares para el equipo

Los valores se presentan por intervalos amplios, deliberadamente sin cantidades exactas porOD/sentido/estación que permitan reconstruir celdas reservadas. Cada intervalo incluye el extremo inferior y excluye el superior. No sumar conceptos: la captación es parte de la demanda existente y nuevo_total ya incluye nuevo_inducido. No sumar personas con vehículos.

'''+markdown(pd.DataFrame(display))+'''

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
'''
    (pub/'RESUMEN_DEMANDA_PRELIMINAR.md').write_text(text,encoding='utf-8')
    manifest=dict(version=c['version'],criterio='Intervalos anuales porsegmento; sin desagregacion ni exactos complementarios; únicoejemploVL ya divulgado',
                  auditoria_intervalos='LP conjunta con transferencias y ejemplo conocido; amplitud relativa de cada mercado reservado >= umbral configurado; no anonimato formal',
                  minimo_ancho_relativo=c['publicacion']['minimo_ancho_relativo_celda_reservada'],archivos=[])
    for p in sorted(pub.glob('*.csv')):
        manifest['archivos'].append(dict(archivo=str(p.relative_to(ROOT)),filas=len(pd.read_csv(p)),sha256=sha(p)))
    (pub/'manifest_publicacion.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--publicar',action='store_true');args=ap.parse_args()
    path=ROOT/'data/templates/config_etapa13.json';c=json.loads(path.read_text());out=ROOT/c['salida_local'];out.mkdir(parents=True,exist_ok=True)
    protected=[p for p in (ROOT/'outputs').rglob('*') if p.is_file() and out not in p.parents]
    before={p:sha(p) for p in protected}
    d=datos();c12=json.loads((ROOT/'data/templates/config_etapa12.json').read_text());profiles=cargar_perfiles(d,c)
    matrix=completar(d,c);tables=aplicar(matrix,profiles,c,c12);central=totales(tables)
    sensitivity=[];scenarios={};max_probability_error=0;matrices_sens=[];diag_sens=[]
    for name,ch in dict(central={},**c['sensibilidades']).items():
        cc=dict(c,**ch);m=matrix if name=='central' else completar(d,cc)
        tt=tables if name=='central' else aplicar(m,profiles,cc,c12)
        ss=totales(tt);ss['escenario']=name
        ss['celdas_P_limitadas']=[int(m.loc[m.segmento.eq(s),'limite_P_aplicado'].sum()) for s in ss.segmento]
        ss['perfiles_r_limitados']=[int(tt['diagnostico_induccion'].loc[lambda g:g.segmento.eq(s),'n_limitados'].sum()) for s in ss.segmento]
        ss['r_max']=[tt['diagnostico_induccion'].loc[lambda g:g.segmento.eq(s),'r_max'].max() for s in ss.segmento]
        sensitivity.append(ss);scenarios[name]=tt
        matrices_sens.append(m.assign(escenario=name));diag_sens.append(tt['diagnostico_induccion'].assign(escenario=name))
        # Contrastar TODAS las probabilidades de los escenarios reutilizados de12.
        for key,base in profiles.items():
            keys=dict(zip(K,key));r=evaluar_perfiles(base,keys,cc,c12)
            prior=one(d['oferta12'],dict(keys,escenario=cc['escenario_oferta12']))
            oldp=prior[['P_proyecto_tierra','P_proyecto_actual','P_proyecto_nuevo']].to_numpy(float)
            max_probability_error=max(max_probability_error,float(np.max(np.abs(r['p_proyecto']-oldp))))
    sens=pd.concat(sensitivity,ignore_index=True)
    for col in ['existente_anual','inducida_anual','nuevo_total_anual','total_con_proyecto_anual']:
        ref=dict(zip(central.segmento,central[col]));sens['variacion_pct_'+col]=[100*(v/ref[s]-1) for v,s in zip(sens[col],sens.segmento)]
    ass=supuestos(c);dg=tables['diagnostico_induccion'];dv=tables['demanda_desviada'];p=tables['demanda_con_proyecto'];a=tables['demanda_total_anual']
    matrix['dias_estacion']=[sum(calendar.monthrange(c['ano'],x)[1] for x in c['estaciones'][s]) for s in matrix.estacion]
    historic12=read('etapa12/demanda_desviada_por_alternativa')
    reproduction=scenarios['sin_imputacion_ni_induccion']['demanda_desviada']
    ref=historic12.loc[historic12.segmento.eq('VL')&historic12.alternativa.eq(ALTS[2])&historic12.demanda_proyecto.notna(),K+['demanda_proyecto']]
    comp=ref.merge(reproduction[K+['captacion_existente']],on=K,validate='one_to_one')
    checks=dict(
        matriz48celdas=len(matrix)==48,
        mercados40_completados=bool(matrix.loc[matrix.ambito.eq('mercado_eleccion'),'demanda_total_OD'].notna().all()),
        ocho_servicios_personas_separados=bool((matrix.ambito!='mercado_eleccion').sum()==8 and matrix.loc[matrix.ambito!='mercado_eleccion','demanda_total_OD'].isna().all()),
        P12_reproducidas=max_probability_error<1e-10,
        probabilidades_sum1=bool(np.allclose(p.loc[p.ambito.eq('mercado_eleccion')].groupby(K).probabilidad.sum(),1)),
        desviada_conservada=bool(np.allclose(dv.captacion_existente,dv.nuevo_desde_tierra+dv.nuevo_desde_barcaza,equal_nan=True)),
        demanda_existente_conservada=bool(np.allclose(p.loc[p.ambito.eq('mercado_eleccion')].groupby(K).existente_redistribuida.sum().sort_index(),matrix.loc[matrix.ambito.eq('mercado_eleccion')].set_index(K).demanda_total_OD.sort_index())),
        inducida_no_negativa=bool((p.inducida.dropna()>=0).all()),
        total_existente_mas_inducida=bool(np.allclose(p.total_con_proyecto,p.existente_redistribuida+p.inducida,equal_nan=True)),
        anual_dias_correctos=bool(np.allclose(a.demanda_anual,a.demanda_diaria*a.dias_estacion,equal_nan=True)),
        unidades_segmentos_coherentes=bool(all(matrix.loc[matrix.segmento.eq(s),'unidad'].eq(u).all() and a.loc[a.segmento.eq(s),'unidad'].eq(u).all() for s,u in c['segmentos'].items())),
        CG_positivo=bool(dg.cg_referencia.gt(0).all() and dg.cociente_min.gt(0).all()),
        limites_reportados=bool(dg.n_limitados.notna().all()),
        reproduccion12_sin_imputacion_induccion=bool(len(comp)==3 and np.allclose(comp.demanda_proyecto,comp.captacion_existente)),
        anteriores_intactos=all(sha(p)==h for p,h in before.items()))
    for n,table in dict(tables,matriz_od_total_completada=matrix,sensibilidad_demanda=sens,
                        matrices_sensibilidad=pd.concat(matrices_sens,ignore_index=True),
                        diagnostico_induccion_sensibilidades=pd.concat(diag_sens,ignore_index=True),
                        supuestos_estimacion_final=ass,totales_por_segmento=central,reproduccion12=comp).items():
        table.to_csv(out/(n+'.csv'),index=False,encoding='utf-8-sig',na_rep='NaN')
    (out/'validacion.json').write_text(json.dumps(dict(checks,max_error_P12=max_probability_error),indent=2))
    pd.DataFrame([dict(archivo=str(p.relative_to(ROOT)),sha256_antes=h,sha256_despues=sha(p),intacto=sha(p)==h) for p,h in before.items()]).to_csv(out/'integridad_anteriores.csv',index=False)
    (out/'config_utilizada.json').write_text(json.dumps(c,ensure_ascii=False,indent=2))
    (out/'manifiesto.json').write_text(json.dumps(dict(codigo={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),path,ROOT/'src/demanda/induccion.py']},entradas={str(p.relative_to(ROOT)):h for p,h in before.items()},sin_recalibracion=True,sin_reconstruccion_atributos=True),indent=2))
    informe_local(out,matrix,tables,central,sens,c,checks)
    print(json.dumps(checks,ensure_ascii=False,indent=2));print(central.to_string(index=False),flush=True)
    assert all(checks.values()),checks
    if args.publicar:publicar(out,c,central,sens,ass,matrix,scenarios)


if __name__=='__main__':main()
