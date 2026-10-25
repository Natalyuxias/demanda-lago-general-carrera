"""Calibración exploratoria EVALSO. Reutiliza pasos07–10, sin nuevos flujos.

Ejecutar .venv/bin/python scripts/11_calibrar_logit.py
Resultados locales excluidos deGit. Ningún identificador EOD se exporta.
"""
from pathlib import Path
import hashlib,importlib.util,json,math,os,shutil,sys
import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.special import expit,logit

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import modelo_biogeme as model
OUT=ROOT/'outputs/calibracion_logit'
K=['origen','destino','estacion','segmento']
NAN=math.nan


def loadscript(name):
    sp=importlib.util.spec_from_file_location(name,ROOT/f'scripts/{name}.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(d,n):pd.DataFrame(d).to_csv(OUT/f'{n}.csv',index=False,encoding='utf-8-sig',na_rep='NaN')
def md(d):
    def f(v):
        if pd.isna(v):return 'NaN'
        if isinstance(v,(float,np.floating)):return f'{v:.6g}'
        return str(v).replace('|','/').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(d.columns)+' |','| '+' | '.join(['---']*len(d.columns))+' |']+['| '+' | '.join(f(v) for v in row)+' |' for row in d.itertuples(index=False,name=None)])


def fuente_celdas(cfg):
    a=pd.read_csv(ROOT/'outputs/atributos_logit_actualizados/atributos_logit_actualizados.csv')
    t=pd.read_csv(ROOT/'outputs/matrices_od_referencia/matriz_od_terrestre.csv')
    b=pd.read_csv(ROOT/'outputs/matrices_od_referencia/matriz_od_barcaza.csv')
    ts=pd.read_csv(ROOT/'outputs/expansion_temporal_terrestre/matrices_24h_sensibilidades.csv')
    return a,t,b,ts


def par_atributos(pair,cfg,ocup=None,longitud=None,desembarque=None,driver=False,exentos=False,tarifa_t=None):
    """Cuatro atributos distintos; anticipación y desembarque imputados a viaje."""
    tt=pair.loc[pair.alternativa.eq('terrestre_chile')].iloc[0]
    bb=pair.loc[pair.alternativa.eq('barcaza_actual')].iloc[0]
    seg=tt.segmento;deb=cfg['desembarque_central_h'] if desembarque is None else desembarque
    factor=cfg['factor_IPC_tarifa'];note=[]
    if seg=='PEATON':
        if {tt.origen,tt.destino}!={'Chile Chico','Coyhaique'}:
            return {**{f'{x}{j}':NAN for j in [1,2] for x in ['c','t','e','a']},'atributos_completos':False,'supuestos_atributos':'PEATON sin servicio terrestre OD identificado; disponibilidad no demostrada'}
        fare=cfg['tarifa_bus_terrestre_supuesta'] if tarifa_t is None else tarifa_t
        tv=cfg['navegacion_h']+cfg['anticipacion_peatones_h']+deb
        out=dict(c1=fare*factor/10000,c2=(cfg['tarifas_equipo']['Carolina_Coyhaique_Puerto_Ibanez']+cfg['tarifa_barcaza_adulto'])*factor/10000,
            t1=cfg['bus_terrestre_servicio_h'],t2=tv,e1=0,e2=bb.t_horario_barcaza_potencial_h,a1=0,a2=cfg['bus_barcaza_servicio_h']-tv)
        note=['Perfil de servicio bus referencia, no modo individual confirmado','Bus+ferry separados; sin prueba tarifa integrada; todos adultos generales','Tierra9000 supuesto no confirmado Interlagos','Descomposicion6h residual; no sumar otra vez nav/anticipacion/desembarque','wH ferry como proxy bus coordinado; desfase propio bus tierra0 supuesto','Fecha bus imputada a enero2026 solo homologacion; vigencia equipo pendiente']
    else:
        occ=ocup if ocup is not None and np.isfinite(ocup) and ocup>=1 else bb.ocupantes_media_muestral
        if not np.isfinite(occ):occ=cfg['ocupacion_VL_fallback'] if seg=='VL' else 1;note.append('ocupacion transferida; CAM1 conductor supuesto si falta')
        length=longitud if longitud is not None and np.isfinite(longitud) and longitud>0 else bb.longitud_CAM_media_muestral_m
        if seg=='CAM' and not np.isfinite(length):length=cfg['longitud_CAM_fallback_m'];note.append('longitud CAM media19 transferida, no medicion de celda')
        main=cfg['tarifa_VL'] if seg=='VL' else cfg['tarifa_metro_CAM']*length
        payers=(1 if driver else 0) if exentos else max(occ-1,0)+(1 if driver else 0)
        fare=(main+payers*cfg['tarifa_barcaza_adulto'])*factor
        out=dict(c1=tt.COV_privado_CLP_dic2025/10000,c2=(bb.COV_privado_CLP_dic2025+fare)/10000,
            t1=tt.tiempo_conduccion_h,t2=cfg['navegacion_h']+cfg['anticipacion_vehiculos_h']+deb,
            e1=0,e2=bb.t_horario_barcaza_potencial_h,a1=0,a2=bb.tiempo_acceso_h)
        note+=['Conductor liberado condicional; acompanantes adultos pagadores salvo sensibilidad','Sin cargos adicionales; acceso intrazonal no identificado','Tarifa lineal CAM condicional a categoria; longitud declarada no facturada','Precios base dic2025 con convencion tarifa enero2026 de10']
    return {**out,'atributos_completos':bool(np.isfinite(list(out.values())).all()),'supuestos_atributos':'; '.join(note)}


def microdatos(a,cfg):
    stage10=loadscript('10_completar_atributos_logit');d,digest=stage10.datos(json.loads((ROOT/'data/templates/config_logit_actualizado.json').read_text()))
    ods=set(map(tuple,a[['origen','destino']].drop_duplicates().values.tolist()))
    allscope=d.loc[np.array([(o,t) in ods for o,t in zip(d.origen,d.destino)]) & d.segmento.isin(['VL','CAM','PEATON'])]
    z=allscope.loc[allscope.ruta.isin(['barcaza_actual','terrestre_chile'])].copy()
    rows=[]
    for i,(_,r) in enumerate(z.iterrows(),1):
        pair=a.loc[a.origen.eq(r.origen)&a.destino.eq(r.destino)&a.estacion.eq(r.estacion)&a.segmento.eq(r.segmento)]
        x=par_atributos(pair,cfg,r.ocupantes_num,r.longitud_num)
        rows.append(dict(fila_local=i,**{k:r[k] for k in K},choice=cfg['alternativas'][r.ruta],ruta_elegida=r.ruta,
            av1=1 if x['atributos_completos'] else NAN,av2=1 if x['atributos_completos'] else NAN,
            ocupantes_declarados=r.ocupantes_num if r.segmento!='PEATON' else NAN,longitud_declarada_m=r.longitud_num if r.segmento=='CAM' else NAN,
            modo_acceso_primario=r.get('Modo 1 para llegar al transbordador') if r.segmento=='PEATON' else 'vehiculo',
            modo_egreso_primario=r.get('Modo 1 para llegar a destino') if r.segmento=='PEATON' else 'vehiculo',
            evidencia_eleccion=r.grado_evidencia,**x))
    save([dict(encuestas_OD_segmentos=len(allscope),eleccion_dos_rutas=len(z),excluidas=len(allscope)-len(z),sha256_EOD=digest,
               regla='Se excluyen rutas fuera de modelo y desconocidas; no se redistribuyen; fila_local no es ID original')],'control_muestra')
    return pd.DataFrame(rows)


def flujos(t,b,ts,case):
    land=t.loc[t.ruta.eq('terrestre_chile')].copy() if case=='jornada10h' else ts.loc[ts.caso.eq(case)&ts.ruta.eq('terrestre_chile')].copy()
    land['QT']=land.demanda_expandida_viajes_diarios_promedio if case=='jornada10h' else land.demanda_estimada_24h
    land=land.loc[land.QT.gt(0),K+['QT']]
    lake=b.loc[b.demanda_diaria_24h_equivalente.gt(0),K+['demanda_diaria_24h_equivalente']].rename(columns={'demanda_diaria_24h_equivalente':'QM'})
    assert not land.duplicated(K).any() and not lake.duplicated(K).any()
    controls=land.merge(lake,on=K,validate='one_to_one');controls['cuota_aproximada_barcaza']=controls.QM/(controls.QT+controls.QM)
    controls['ponderacion']=case;controls['tipo_total']='T10h frente ferry diario; unidades temporales no homologadas, SOLO contraste' if case=='jornada10h' else 'T24h sensibilidad08 frente ferry diario; representatividad exploratoria'
    return controls


def ponderar(micro,t,b,ts,cfg):
    rows=[];controls=[]
    cases=[cfg['central_ponderacion_VL']]+cfg['sensibilidades_ponderacion']+['muestral_jornada10h']
    for case in cases:
        sourcecase='CC_PC1_laboral' if case=='muestral_mismo_soporte' else 'jornada10h' if case=='muestral_jornada10h' else case
        target=flujos(t,b,ts,sourcecase)
        # Solo celdas con observaciones validas de ambas elecciones; ausencia no equivale a cero.
        groups=[]
        for keys,g in micro.groupby(K,sort=False):
            match=target
            for k,v in zip(K,keys):match=match.loc[match[k].eq(v)]
            if len(match)!=1:continue
            ng=g.loc[g.atributos_completos]
            if set(ng.choice)!={1,2}:continue
            c=match.iloc[0].to_dict();c['encuestas_T']=int(ng.choice.eq(1).sum());c['encuestas_M']=int(ng.choice.eq(2).sum())
            c['ponderacion']=case;controls.append(c)
            ng=ng.copy();ng['ponderacion']=case
            ng['peso_sin_normalizar']=1.0 if case.startswith('muestral') else np.where(ng.choice.eq(1),c['QT']/c['encuestas_T'],c['QM']/c['encuestas_M'])
            ng['QT_control']=c['QT'];ng['QM_control']=c['QM'];ng['fuente_peso']=c['tipo_total']
            groups.append(ng)
        if groups:
            combined=pd.concat(groups,ignore_index=True)
            for seg,g in combined.groupby('segmento',sort=False):
                g=g.copy();g['weight']=g.peso_sin_normalizar*len(g)/g.peso_sin_normalizar.sum();g['apta_estimacion']=True;rows.append(g)
    base=pd.concat(rows,ignore_index=True)
    # No se fabrica ninguna observacion terrestre de peatones; conservar sus elecciones fuera de MLE.
    others=micro.copy();others['ponderacion']='sin_soporte_pareado';others['weight']=NAN;others['peso_sin_normalizar']=NAN;others['apta_estimacion']=False
    save(pd.concat([base,others],ignore_index=True),'base_calibracion_logit')
    save(controls,'controles_expandidos_ponderaciones')
    return base,pd.DataFrame(controls)


def fijos(cfg,ra=None,re=None,bc=None,bt=None):
    tt=cfg['beta_t_fijo_por_h'] if bt is None else bt
    return dict(beta_c=cfg['beta_c_fijo_por_10000CLP'] if bc is None else bc,beta_t=tt,
        beta_e=(cfg['ratio_horario_central'] if re is None else re)*tt,beta_a=(cfg['ratio_acceso_central'] if ra is None else ra)*tt)


def score_ASC(d,params,target=None,w=None):
    pp=dict(params,ASC_barcaza=0)
    v=model.utilidades(d,pp);offset=np.asarray(v[2]-v[1],float)
    weight=np.asarray(d.weight if w is None else w,float)
    mean=np.average(np.asarray(d.choice.eq(2),float),weights=weight) if target is None else target
    asc=brentq(lambda x:np.average(expit(x+offset),weights=weight)-mean,-200,200,xtol=1e-12)
    return dict(params,ASC_barcaza=float(asc))


def intento(d,fixed,free,name,tries,cfg):
    try:
        vals,diag=model.estimar(d,fixed,free,name,cfg['lambda_central']);diag.update(nombre=name,segmento=d.segmento.iloc[0],ponderacion=d.ponderacion.iloc[0])
        tries.append(diag);print(f'{name}: convergio={diag["convergio"]}, rango={diag["rango"]}/{len(free)}, betas={vals}',flush=True)
        return vals,diag
    except Exception as e:
        tries.append(dict(nombre=name,error=str(e),libres=free));print(name,type(e).__name__,str(e)[:200],flush=True);return None,None


def aceptar(vals,diag,param):
    return vals is not None and diag['convergio'] and diag['rango']==diag['columnas'] and -19.99<vals[param]<-1e-5


def estimaciones(base,cfg):
    tries=[];models=[]
    for seg in ['VL','CAM']:
        case=cfg['central_ponderacion_VL'] if seg=='VL' else cfg['central_ponderacion_CAM']
        d=base[base.segmento.eq(seg)&base.ponderacion.eq(case)].copy();fixed=fijos(cfg)
        if seg=='VL':
            intento(d,{},model.PARAMS,'VL_intento_cinco_libres',tries,cfg)
            vals,diag=intento(d,{'beta_t':fixed['beta_t'],'beta_a':fixed['beta_a']},['ASC_barcaza','beta_c','beta_e'],'VL_reducido_costo_horario',tries,cfg)
            if aceptar(vals,diag,'beta_c') and aceptar(vals,diag,'beta_e'):
                params=vals;free=['ASC_barcaza','beta_c','beta_e']
            else:
                vals,diag=intento(d,{k:v for k,v in fixed.items() if k!='beta_e'},['ASC_barcaza','beta_e'],'VL_condicional_costo_fijado',tries,cfg)
                if aceptar(vals,diag,'beta_e'):params=vals;free=['ASC_barcaza','beta_e']
                else:
                    params,diag=intento(d,fixed,['ASC_barcaza'],'VL_ASC_condicional',tries,cfg);free=['ASC_barcaza']
        else:
            vals,diag=intento(d,{k:v for k,v in fixed.items() if k!='beta_c'},['ASC_barcaza','beta_c'],'CAM_intento_costo',tries,cfg)
            if aceptar(vals,diag,'beta_c'):params=vals;free=['ASC_barcaza','beta_c']
            else:params,diag=intento(d,fixed,['ASC_barcaza'],'CAM_ASC_condicional',tries,cfg);free=['ASC_barcaza']
        if params is None:raise RuntimeError(f'Biogeme no produjo modelo central {seg}')
        models.append(dict(nombre='central',segmento=seg,ponderacion=case,params=params,free=free,diag=diag,base=d,
                           fuente='Biogeme3.3.2 MLE ponderada condicional; pesos normalizados; no diseño probabilistico'))
    # Ponderaciones alternativas, misma utilidad con pendientes centrales fijadas; recalibracion ASC.
    for m in models.copy():
        seg=m['segmento'];cases=cfg['sensibilidades_ponderacion'] if seg=='VL' else ['muestral_jornada10h']
        for case in cases:
            g=base[base.segmento.eq(seg)&base.ponderacion.eq(case)].copy()
            if g.empty:continue
            pars,di=intento(g,{k:v for k,v in m['params'].items() if k!='ASC_barcaza'},['ASC_barcaza'],f'{seg}_pesos_{case}',tries,cfg)
            if pars is not None:models.append(dict(nombre='ponderacion_'+case,segmento=seg,ponderacion=case,params=pars,free=['ASC_barcaza'],diag=di,base=g,fuente='Biogeme: ASC recalibrada; pendientes fijadas al modelo central para aislar ponderacion'))
    return models,tries


def celdas_prediccion(a,cfg,**changes):
    rows=[]
    for keys,g in a.groupby(K,sort=False):rows.append(dict(zip(K,keys))|par_atributos(g,cfg,**changes))
    return pd.DataFrame(rows)


def calibrar_peaton(a,controls,cfg):
    ref=controls.loc[controls.segmento.eq('VL')&controls.ponderacion.eq(cfg['central_ponderacion_VL'])].copy()
    attrs=celdas_prediccion(a,cfg);ref['segmento']='PEATON'
    p=ref.merge(attrs,on=K,validate='one_to_one');p['choice']=2;p['weight']=p.QT+p.QM
    target=float(p.QM.sum()/(p.QT+p.QM).sum())
    params=score_ASC(p,fijos(cfg),target=target)
    save(p.assign(cuota_proxy=target,tipo='Cuotas y distribucion de VL transferidas como supuesto a peatones; NO elecciones individuales ficticias'),'objetivos_ASC_peaton')
    return dict(nombre='central',segmento='PEATON',ponderacion='proxy_VL24h_no_cuota_personas',params=params,free=[],diag=dict(cuota_proxy=target),base=p,
        fuente='ASC calibrada por momento contra proxy VL expandida; betas supuestos; no MLE peatones ni cuota observada de personas')


def sensibilidad(models,a,cfg):
    extras=[]
    variants=[]
    variants += [(f'ratio_acceso_{x}',dict(ra=x),{}) for x in cfg['ratios_sensibilidad'] if x!=cfg['ratio_acceso_central']]
    variants += [(f'ratio_horario_{x}',dict(re=x),{}) for x in cfg['ratios_sensibilidad'] if x!=cfg['ratio_horario_central']]
    variants += [(f'beta_c_fijo_{x}',dict(bc=x),{}) for x in cfg['beta_c_sensibilidad_por_10000CLP'] if x!=cfg['beta_c_fijo_por_10000CLP']]
    variants += [(f'desembarque_{x}',{},dict(desembarque=x)) for x in cfg['desembarque_sensibilidades_h'] if x!=cfg['desembarque_central_h']]
    variants += [('conductor_paga',{},dict(driver=True)),('acompanantes_exentos',{},dict(exentos=True))]
    for original in [x for x in models if x['nombre']=='central']:
        seg=original['segmento']
        vv=variants if seg!='PEATON' else [(x,y,z) for x,y,z in variants if x not in ['conductor_paga','acompanantes_exentos']]+[(f'tarifa_tierra_{fare}',{},dict(tarifa_t=fare)) for fare in cfg['tarifa_bus_terrestre_sensibilidades'] if fare!=cfg['tarifa_bus_terrestre_supuesta']]+[('bus_integrado_sin_pasaje_barco_adicional',{},dict(integrado=True))]
        for name,paramchanges,changes in vv:
            d=original['base'].copy();changes=changes.copy();integrated=changes.pop('integrado',False)
            if changes:
                for idx,r in d.iterrows():
                    g=a.loc[a.origen.eq(r.origen)&a.destino.eq(r.destino)&a.estacion.eq(r.estacion)&a.segmento.eq(seg)]
                    attrs=par_atributos(g,cfg,ocup=r.get('ocupantes_declarados'),longitud=r.get('longitud_declarada_m'),**changes)
                    for x in [f'{v}{j}' for j in [1,2] for v in ['c','t','e','a']]:d.loc[idx,x]=attrs[x]
            if integrated:d['c2']-=cfg['tarifa_barcaza_adulto']*cfg['factor_IPC_tarifa']/10000
            pars={k:v for k,v in original['params'].items() if k!='ASC_barcaza'}
            if 'ra' in paramchanges:pars['beta_a']=paramchanges['ra']*pars['beta_t']
            if 're' in paramchanges:pars['beta_e']=paramchanges['re']*pars['beta_t']
            if 'bc' in paramchanges:pars['beta_c']=paramchanges['bc']
            pars=score_ASC(d,pars,target=original['diag'].get('cuota_proxy'))
            extras.append(dict(nombre=name,segmento=seg,ponderacion=original['ponderacion'],params=pars,free=[],diag={},base=d,
                fuente='Sensibilidad condicional: pendientes adoptadas y ASC recalibrada por score; no nueva estimacion de pendientes',changes=changes,integrado=integrated))
    return extras


def resultados(models,a,cfg):
    pars=[];probs=[];comp=[];fit=[];lambda_rows=[]
    for m in models:
        seg=m['segmento'];params=m['params'];d=m['base'];esc=m['nombre']
        for p,v in params.items():
            method='estimado' if p in m['free'] and p!='ASC_barcaza' else 'calibrado' if p=='ASC_barcaza' else 'supuesto'
            source=m['fuente'] if method!='supuesto' else 'Supuesto del estudio/pendiente central fijada; no transferencia empirica'
            scaled=v/10000 if p=='beta_c' else v
            pars.append(dict(segmento=seg,parametro=p,valor=scaled,valor_escala_modelo=v,unidad='utilidad_por_CLP' if p=='beta_c' else 'utilidad_por_hora' if p.startswith('beta') else 'utilidad',
                escala_modelo='C/10000CLP; tiempos horas; escala superior1',metodo=method,fuente=source,
                error_estandar=(m['diag'].get('SE_condicional',{}).get(p,NAN)/(10000 if p=='beta_c' else 1)) if p in m['free'] and m['diag'].get('rango')==m['diag'].get('columnas') else NAN,
                alcance_error='Modelo condicional con pesos normalizados; NO error de encuesta ni correccion de diseño',escenario=esc,ponderacion=m['ponderacion']))
        for p,v in [('ASC_terrestre',0),('lambda_lago',cfg['lambda_central'])]:pars.append(dict(segmento=seg,parametro=p,valor=v,valor_escala_modelo=v,unidad='adimensional',metodo='supuesto',fuente='Normalizacion ASC tierra0' if p=='ASC_terrestre' else 'Supuesto usuario; muBiogeme=1/lambda; no identificable con singleton',error_estandar=NAN,escenario=esc,ponderacion=m['ponderacion']))
        pr=model.probabilidades(d,params);w=d.weight.to_numpy(float)
        target=m['diag'].get('cuota_proxy',np.average(d.choice.eq(2),weights=w))
        pp=np.asarray(pr,float);observed=d.choice.to_numpy(int)==2
        ll=float(np.sum(w*(observed*np.log(np.maximum(pp,1e-300))+(~observed)*np.log(np.maximum(1-pp,1e-300))))) if seg!='PEATON' else NAN
        fit.append(dict(segmento=seg,escenario=esc,ponderacion=m['ponderacion'],n_filas=len(d),tipo_filas='celdas_proxy; NO encuestas de personas' if seg=='PEATON' else 'encuestas_individuales',peso_total=w.sum(),n_efectivo_Kish=w.sum()**2/np.sum(w*w) if seg!='PEATON' else NAN,
            cuota_objetivo=target,cuota_predicha=np.average(pp,weights=w),log_verosimilitud=ll,
            tipo_objetivo='proxy_VL_NO_observacion_personas' if seg=='PEATON' else 'cuota_muestra' if m['ponderacion'].startswith('muestral') else 'expansion_exploratoria',
            convergio=m['diag'].get('convergio',True),metodo=m['fuente']))
        grid=celdas_prediccion(a,cfg,**m.get('changes',{}));grid=grid[grid.segmento.eq(seg)].copy()
        if m.get('integrado'):grid.c2-=cfg['tarifa_barcaza_adulto']*cfg['factor_IPC_tarifa']/10000
        for _,g in grid.iterrows():
            keys={k:g[k] for k in K};same=d
            for k in K:same=same.loc[same[k].eq(g[k])]
            representative=float(model.probabilidades(pd.DataFrame([g]),params).iloc[0]) if g.atributos_completos else NAN
            integrated=float(np.average(model.probabilidades(same,params),weights=same.weight)) if len(same) else representative
            probs.append(dict(**keys,escenario=esc,ponderacion=m['ponderacion'],P_barcaza=integrated,P_terrestre=1-integrated,
                P_barcaza_atributo_medio=representative,metodo_promedio=('celda_objetivo_proxy_sin_microdatos_terrestres_personas' if seg=='PEATON' else 'integracion_sobre_microdatos_y_pesos_del_modelo') if len(same) else 'atributos_medio_y_fallback_supuesto_fuera_soporte',
                uso=('calibracion_condicionada_cuota_proxy_NO_personas_observadas' if seg=='PEATON' else 'calibracion_en_soporte') if len(same) else 'extrapolacion_oferta_NO_demanda_observada' if g.atributos_completos else 'no_calculable; falta_servicio_peatonal_OD',
                supuestos=g.supuestos_atributos))
        if seg!='PEATON':
            for keys,g in d.groupby(K,sort=False):
                obs=float(np.average(g.choice.eq(2),weights=g.weight));pred=float(np.average(model.probabilidades(g,params),weights=g.weight))
                comp.append(dict(zip(K,keys))|dict(escenario=esc,ponderacion=m['ponderacion'],cuota_barcaza_aproximada=obs,cuota_barcaza_predicha=pred,diferencia=pred-obs,
                    flujo_T_control=g.QT_control.iloc[0],flujo_M_control=g.QM_control.iloc[0],n_T=int(g.choice.eq(1).sum()),n_M=int(g.choice.eq(2).sum()),tipo='recuentos_muestrales' if m['ponderacion'].startswith('muestral') else 'expandidos_exploratorios_NO_cuota_poblacional_verificada'))
        else:
            for _,g in d.iterrows():comp.append({k:g[k] for k in K}|dict(escenario=esc,ponderacion=m['ponderacion'],cuota_barcaza_aproximada=g.QM/(g.QM+g.QT),cuota_barcaza_predicha=float(model.probabilidades(pd.DataFrame([g]),params).iloc[0]),
                tipo='PROXY_VL_TRANSFERIDA_NO_OBSERVACION_PEATON',n_T=NAN,n_M=NAN))
        if esc=='central':
            for lam in cfg['lambda_sensibilidades']:
                pred=model.probabilidades(d,params,lam)
                lambda_rows.append(dict(segmento=seg,lambda_lago=lam,mu_lago_Biogeme=1/lam,P_barcaza_promedio=np.average(pred,weights=w),
                    maxima_diferencia_con_central=float(np.max(np.abs(np.asarray(pred)-pp))),estado='supuesto; singleton actual invariancia exacta'))
    save(pars,'parametros_logit');save(probs,'probabilidades_situacion_actual');save(comp,'comparacion_observado_predicho');save(fit,'ajuste_modelos');save(lambda_rows,'sensibilidad_lambda')
    return pd.DataFrame(pars),pd.DataFrame(probs),pd.DataFrame(comp),pd.DataFrame(fit)


def completar_ajuste(fit):
    fit=fit.copy()
    for i,r in fit.iterrows():
        if r.segmento=='PEATON':continue
        q=r.cuota_objetivo
        ll0=r.peso_total*(q*np.log(q)+(1-q)*np.log1p(-q))
        fit.loc[i,'LL_referencia_solo_ASC']=ll0
        fit.loc[i,'rho2_frente_solo_ASC']=1-r.log_verosimilitud/ll0
        fit.loc[i,'mejora_LL_frente_solo_ASC']=r.log_verosimilitud-ll0
    return fit


def report(pars,probs,comp,fit,tries,cfg,checks):
    central=pars[pars.escenario.eq('central')]
    comparative=comp[comp.escenario.eq('central')]
    summary=fit[fit.escenario.eq('central')]
    pilot=probs[probs.escenario.eq('central')&probs.origen.eq('Chile Chico')&probs.destino.eq('Coyhaique')]
    txt=f'''# Etapa11: calibración numérica exploratoria EVALSO

## Resultado y normalización

Se ejecutó Biogeme3.3.2 local. La especificación conserva **cuatro coeficientes distintos**:
`V_r=ASC_r+beta_c*C_r+beta_t*t_viaje_r+beta_e*t_horario_r+beta_a*t_acceso_r`.
ASC_terrestre=0; escala superior=1. En código C se divide por10000CLP y tiempos se expresan en horas; el CSV entrega beta_c porCLP y su valor en la escala del modelo. Los costos son privados y no incluyen CostGen HDM4 ni precios sociales. No se calcula el cruce futuro.

Solo terrestre_chile/barcaza_actual. EOD excluye rutas fuera de alcance y desconocidas; no se generan elecciones falsas. La base exporta fila local secuencial, sin identificadores personales ni coordenadas. Las matrices07–10 no se modifican.

### Parámetros centrales numéricos

{md(central[['segmento','parametro','valor','valor_escala_modelo','unidad','metodo','error_estandar','ponderacion']])}

Las filas supuesto NO son estimaciones estadísticas ni transferencias empíricas. Valores fijos de escala beta_c=-0,2por10000CLP y beta_t=-0,2/h implican VST privado10000CLP/h **supuesto del estudio**, no uso del10000 de CostGen ARISTO ni VST social. Si se aceptó un beta_c estimado, ese cociente cambia; el valor numérico de cada escenario está en el CSV. Los coeficientes fijados beta_a/beta_e se relacionan explícitamente con beta_t; ratios0,5/1/2 son supuestos, sin referencia suficientemente comparable para transferir valores numéricos. La bibliografía sustenta el método, no estos números.

Los errores estándar presentes son condicionales del modelo Biogeme con pesos normalizados. **No son errores de diseño muestral ni significancias poblacionales**. No se informan errores para parámetros fijados, lambda ni ASC de peatones por cuota proxy. Los intentos no identificados no se convierten en estimaciones centrales.

## Atributos y regla operacional

Vehículos: tierra t_viaje=conducción completa y t_acceso=0; barcaza t_viaje=navegación+anticipación2h+desembarque0,5h, y t_acceso=conducción de todos los accesos/egresos. La conducción descriptiva no vuelve a sumarse. Anticipación contiene operaciones previas, sin embarque adicional. Así se imputan previo y desembarque a beta_t, **sin crear otro coeficiente**. Desembarque0,25/0,75h son sensibilidades no medidas.

Peatones: servicios de referencia Coyhaique–Chile Chico de6h bimodal y8h tierra. Se descompone6h como viaje=2hnav+1hprevio+desembarque, acceso=6−viaje: el residuo es una imputación de tiempo del servicio terrestre/bordes, **no conducción VL ni medición desagregada**. La suma siempre es6h; no se agregan nuevamente navegación y operaciones. Con desembarque distinto cambia el reparto interno, no las6h publicadas. No se atribuye Carolina a todos los peatones encuestados; es perfil de referencia para la calibración por proxy. Para Chile Chico–Puerto Ibáñez peatonal no se inventa una alternativa de bus terrestre: probabilidad quedaNaN.

Horario:0,25×168/f, f11diciembre–abril y8mayo–noviembre, sin carga peligrosa. Otoño conserva marzo/abril y mayo mediante los valores mensuales agregados por días de10. En el bus coordinado se adopta wH de ferry como proxy adicional al tiempo físico, y desfase del bus terrestre0 como supuesto por falta de horario deseado/calendario común. Se sensibiliza beta_e; no se presenta como espera en terminal ni como frecuencia medida del bus. Estos supuestos permiten ejecutar, pero deben validarse.

VL utiliza ocupantes declarados individualmente para ambas ofertas. Se asume conductor liberado y acompañantes adultos pagadores; se prueban conductor pagador/acompañantes exentos. No se suma ocupación al flujo de peatones. CAM usa longitudes individuales positivas para tarifa7310×L; cuando falta perfil de una celda de predicción, media19=8,657895m como transferencia exploratoria. No se impone16m. La correspondencia longitud declarada/facturada y tasa efectiva permanecen pendientes. Los cargos adicionales0 solo son supuesto operacional monetario del escenario.

## Nuevas tarifas de equipo y fecha de precios

Carolina: Coyhaique–Puerto Ibáñez10000, Cruce Cerro Castillo8000, Horquetas7000; descuentos TNE30%, mayores50%. Lukas: Puerto Ibáñez10000 y Cruce Cerro Castillo8000. Fuente: equipo, instrucción Etapa11, incorporación2026-10-25, **documento/fecha de vigencia pendientes**. Se registran en configuración sin ampliar OD; descuentos se ilustran en tarifas, no se aplican a acompañantes de VL ni a todo pasajero sin categoría identificada.

Bimodal general: bus10000+barcaza2550=12550CLP nominales bajo cobro separado. No se verificó tarifa integrada en fuentes previas; la OC2024 era institucional y no prueba tarifa pública por pasajero. Sensibilidad integrada: total10000 sin añadir otro pasaje barco, **supuesto**, no precio integrado confirmado. Tierra completa9000 es referencia supuesta, no tarifa confirmada Interlagos; sensibilidades7200/10800.

Se conserva la homologación exploratoria de10 a diciembre2025 mediante factor{cfg['factor_IPC_tarifa']:.9f}=IPC109,26/109,71. Enero2026 para tarifas, incluso las del equipo, es convención pendiente, no vigencia verificada. Valores nominales están documentados aparte. No se agrega IVA nuevamente. Las probabilidades dependen de estos supuestos; la incertidumbre de fecha no desaparece por convertirlas a una base común.

## Ponderaciones y soporte

`w_n=Q_celda,ruta/N_encuestas_elegibles_celda,ruta`, normalizado para sumarN dentro de segmento y escenario. Así no se transforma el número de vehículos expandidos en tamaño de muestra estadístico. Representatividad de jornadas, OD y no respuesta se adopta exploratoriamente, no se verifica como diseño probabilístico. No se atribuyen pesos de inclusión certificados.

Central VL: sensibilidad24h CC_PC1_laboral de08, solo estratos con controles positivos y encuestas de ambas alternativas. Otoño queda fuera de ese ajuste24h por falta de factor, no por demanda nula. Se comparan tres perfiles24h alternativos, recuentos simples en el mismo soporte y jornada10h. El contraste10h no se presenta como cuota diaria24h.

Central CAM: solo mayo con pares observados; tierra10h frente ferry promedio diario, **unidades temporales no homologadas**. Se conserva como calibración condicionada a este contraste, no cuota poblacional diaria defendida. No se fabricó un factor24h de camiones ni uno otoñal. Sensibilidad muestral compara recuentos, no resuelve el problema de cobertura.

PEATON: no hay elecciones terrestres confirmadas comparables; una MLE de ASC sola tendería a infinito. No se limita artificialmente para anunciar estimación. Se calibra una ASC finita mediante momento de participación: **cuota VL24h y distribución OD/estación de VL transferidas como proxy supuesta a peatones**. No es participación observada/expandida de personas. Los objetivos se conservan en objetivos_ASC_peaton.csv; no se insertan viajes terrestres ficticios en base_calibracion_logit.csv.

### Ajuste global central

{md(summary[['segmento','ponderacion','n_filas','n_efectivo_Kish','cuota_objetivo','cuota_predicha','log_verosimilitud','tipo_objetivo']])}

La igualdad global de cuota por ASC es una condición del ajuste/calibración, **no validación independiente**. Para sensibilidades de ponderación se fijan pendientes del central y se recalibra ASC con Biogeme, aislando el efecto de pesos/soporte. Otras sensibilidades fijan pendientes explícitamente y recalibran ASC resolviendo el score exacto de una constante, equivalente a MLE condicional en este caso; no se etiquetan como nuevas pendientes estimadas.

Contraste de ajuste con un modelo de solo constante sobre los mismos registros y pesos:

{md(summary[['segmento','log_verosimilitud','LL_referencia_solo_ASC','rho2_frente_solo_ASC','mejora_LL_frente_solo_ASC']])}

Un rho2 negativo significa que las pendientes impuestas ajustan peor que la sola constante; no es un error numérico y no se oculta. Esta situación requiere revisar los supuestos antes de usar ese segmento para predicción del proyecto. No se calcula ese indicador como ajuste empírico de peatones, porque su cuota es proxy. La mezcla de celdas/estaciones pondera sus flujos diarios equivalentes, sin anualización ni ponderación por días de cada estación.

### Comparación por OD/estación

{md(comparative[['origen','destino','estacion','segmento','cuota_barcaza_aproximada','cuota_barcaza_predicha','tipo']])}

Las probabilidades de celdas con microdatos se integran sobre sus atributos individuales y pesos, no se sustituyen por probabilidad del atributo promedio (no equivalen por no linealidad). Ambas están en probabilidades_situacion_actual.csv. Fuera del soporte se utilizan perfiles de celda o medias transferidas marcadas, incluida oferta de invierno: **son extrapolaciones condicionales de oferta, no demanda invernal observada**. No usar mezcla de escenarios como muestra adicional.

### Chile Chico → Coyhaique: probabilidades centrales

{md(pilot[['estacion','segmento','P_terrestre','P_barcaza','metodo_promedio','uso']])}

## Identificación y coherencia

Se intentó estimación libre de las cinco cantidades ASC/beta_c/beta_t/beta_e/beta_a en Biogeme y luego especificaciones restringidas. Los resultados completos, convergencia, rango y parámetros de cada intento están en intentos_estimacion.json. Rango deficiente, frontera de signo o ausencia de variación impiden declarar pendientes como estimadas: se fijan explícitamente. La normalización de error logit no identifica por sí sola una beta que esté confundida con ASC. Se conserva beta_c,beta_t negativos; beta_e/beta_a son negativos por estimación restringida o relación supuesta.

Con el soporte focal, diferencias de viaje/acceso casi constantes se confunden con ASC. Costos individuales permiten variación por ocupación/longitud, pero no garantizan independencia respecto a elección, ingreso o tamaño del grupo. Un costo que alcanza la frontera cero es intento no retenido; fijarlo negativo no lo convierte en estimado. Beta_e estacional puede absorber variaciones de mercado omitidas, y no debe interpretarse como efecto causal de frecuencia.

La EOD de barcaza/carretera proviene de interceptaciones distintas. La ponderación exploratoria no elimina selección por alternativa, cobertura horaria, no respuesta ni repetición de jornadas. Los errores Biogeme no corrigen estos sesgos. Las predicciones por medias para OD sin soporte no validan transferencia espacial. Precio de bus supuesto y cuota proxy de personas hacen que sus parámetros sean de aplicación condicional, no calibración empírica completa.

## Estructura jerárquica y lambda

En Biogeme `mu_lago=1/lambda`: central0,7→1,428571 y sensibilidades0,5→2 /0,9→1,111111. Se conserva escala superior1 y ASC_tierra0. Hay un único elemento por nido actual: `lambda*log(exp(V_M/lambda))=V_M`. Por tanto cambiar lambda **no cambia ninguna probabilidad actual**; comprobar sensibilidad_lambda.csv. No puede estimarse libremente ni interpretarse una constancia actual como validación de0,7.

ASC del cruce futuro permanece sin cálculo; igualdad inicial con ASC existente queda como supuesto para etapa posterior, no como nueva constante estimada. No se simula Jara–Levicán ni SBO/inducción.

## Reproducción y entregables

`.venv/bin/python scripts/11_calibrar_logit.py`. Modelo ejecutable Biogeme: scripts/modelo_biogeme.py y copia en esta carpeta. Entorno local Biogeme3.3.2 instalado desde wheel en caché al fallar DNS de descarga; no se subieron datos. Configuración: data/templates/config_calibracion_logit.json.

Base_calibracion_logit.csv conserva elecciones reales y los atributos de ambas alternativas, con ponderaciones y flag apta_estimacion; fila_local no es ID EOD. Una elección puede repetirse en escenarios: nunca combinar filas entre escenarios como observaciones independientes. Costos c1/c2 están en10000CLP, t1/t2 viaje, e1/e2 horario, a1/a2 acceso en horas; choice1tierra/2barcaza. Disponibilidad1 refleja factibilidad modelada de los dos recorridos, condicionada a restricciones de la fuente. En peatones sin servicio completo se mantieneNaN, no indisponibilidad confirmada0.

parametros_logit.csv diferencia estimado/calibrado/supuesto y unidad. probabilidades_situacion_actual.csv conserva medias y extrapolaciones. comparacion_observado_predicho.csv identifica controles expandidos, muestrales y proxy. Tarifas_equipo.csv registra las tarifas y descuentos sin precios de tramos ajenos aplicados al OD focal. Sensibilidades mantienen una modificación por vez, no todas las combinaciones.

Verificaciones: `{json.dumps(checks,ensure_ascii=False)}`. Fuentesprevias/integridad_anteriores.csv prueba conservación por hash. Resultados/microdatos derivados quedan excluidos deGit. Sin commit/push.
'''
    (OUT/'diagnostico_calibracion.md').write_text(txt,encoding='utf-8')


def main():
    cfg=json.loads((ROOT/'data/templates/config_calibracion_logit.json').read_text())
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'biogeme').mkdir(exist_ok=True)
    protected=[p for folder in ['matrices_od_referencia','expansion_temporal_terrestre','atributos_alternativas','atributos_logit_actualizados'] for p in (ROOT/'outputs'/folder).glob('*') if p.is_file()]
    before={p:sha(p) for p in protected}
    a,t,b,ts=fuente_celdas(cfg);micro=microdatos(a,cfg);base,controls=ponderar(micro,t,b,ts,cfg)
    os.chdir(OUT/'biogeme')
    models,tries=estimaciones(base,cfg);models.append(calibrar_peaton(a,controls,cfg));models+=sensibilidad(models,a,cfg)
    pars,probs,comp,fit=resultados(models,a,cfg)
    fit=completar_ajuste(fit);save(fit,'ajuste_modelos')
    (OUT/'intentos_estimacion.json').write_text(json.dumps(tries,ensure_ascii=False,indent=2,default=float))
    (OUT/'config_utilizada.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2))
    import platform
    from importlib.metadata import version
    (OUT/'entorno_ejecucion.json').write_text(json.dumps(dict(python=platform.python_version(),paquetes={p:version(p) for p in ['biogeme','biogeme-optimization','pandas','numpy','scipy','jax','jaxlib']}),indent=2))
    save([dict(parametro=k,valor=v,fuente=cfg['fuente_tarifas_equipo'],vigencia='pendiente') for k,v in cfg['tarifas_equipo'].items()],'tarifas_equipo')
    lambda_check=pd.read_csv(OUT/'sensibilidad_lambda.csv')
    checks=dict(alternativas_solo_dos=set(micro.ruta_elegida)=={'terrestre_chile','barcaza_actual'},
        probabilidades_suman1=bool(np.allclose((probs.P_terrestre+probs.P_barcaza).dropna(),1)),
        probabilidades_en_rango=bool(probs.P_barcaza.dropna().between(0,1).all()),
        signos_costo_tiempo=bool(pars.loc[pars.parametro.isin(['beta_c','beta_t']),'valor'].lt(0).all()),
        SE_solo_parametros_ajustados=bool(pars.loc[pars.metodo.eq('supuesto'),'error_estandar'].isna().all()),
        sin_peatones_terrestres_ficticios=bool(micro.loc[micro.segmento.eq('PEATON'),'choice'].eq(2).all()),
        lambda_singleton_invariante=bool(lambda_check.maxima_diferencia_con_central.eq(0).all()),
        cuotas_globales_centrales_reproducidas=bool(np.allclose(fit.loc[fit.escenario.eq('central'),'cuota_objetivo'],fit.loc[fit.escenario.eq('central'),'cuota_predicha'],atol=1e-5)),
        archivos_previos_intactos=all(sha(p)==v for p,v in before.items()))
    save([dict(archivo=str(p.relative_to(ROOT)),sha256_antes=v,sha256_despues=sha(p),intacto=sha(p)==v) for p,v in before.items()],'integridad_anteriores')
    (OUT/'validacion.json').write_text(json.dumps(checks,indent=2))
    shutil.copyfile(ROOT/'scripts/modelo_biogeme.py',OUT/'modelo_biogeme.py')
    report(pars,probs,comp,fit,tries,cfg,checks)
    assert all(checks.values()),checks
    print('CENTRALES',fit.loc[fit.escenario.eq('central')].to_json(orient='records'),flush=True)
    print('VALIDACIONES',json.dumps(checks),flush=True)


if __name__=='__main__':main()
