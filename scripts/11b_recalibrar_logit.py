"""Etapa11B incremental. Lee base, objetivos proxy y atributos existentes.

.venv/bin/python scripts/11b_recalibrar_logit.py
"""
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import modelo_biogeme_11b as model
from modelo_biogeme import probabilidades
sp=importlib.util.spec_from_file_location('etapa11',ROOT/'scripts/11_calibrar_logit.py');prev=importlib.util.module_from_spec(sp);sp.loader.exec_module(prev)
OUT=ROOT/'outputs/calibracion_logit_11b';K=['origen','destino','estacion','segmento']


def save(d,n):pd.DataFrame(d).to_csv(OUT/f'{n}.csv',index=False,encoding='utf-8-sig',na_rep='NaN')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def escenarios(cfg):
    central=dict(escenario='central',VST=cfg['VST_central_CLP_h_unidad_decision'],ra=cfg['ratio_acceso_central'],re=cfg['ratio_horario_central'],lam=cfg['lambda_central'],factor='referencia')
    yield central
    for key,values,field in [('ra',cfg['ratios_acceso'],'ratio_acceso'),('re',cfg['ratios_horario'],'ratio_horario'),('VST',cfg['VST_CLP_h'],'VST'),('lam',cfg['lambdas'],'lambda')]:
        for x in values:
            if x!=central[key]:yield dict(central,**{key:x},escenario=f'{field}_{x}',factor=field)


def fuente_calibracion(base,proxy,cfg):
    result={}
    for seg in ['VL','CAM']:
        case=cfg['ponderacion_'+seg]
        d=base.loc[base.segmento.eq(seg)&base.ponderacion.eq(case)&base.apta_estimacion.eq(True)].copy()
        assert set(d.choice)=={1,2} and not d.duplicated('fila_local').any()
        result[seg]=d
    # Q_T/Q_M son cuotas de VL transferidas como objetivo, NO flujos peatonales.
    result['PEATON']=proxy.drop(columns=['choice'],errors='ignore').copy()
    return result


def ajuste(d,params,proxy=False):
    p=np.asarray(probabilidades(d,params));w=np.asarray(d.weight)
    y=np.asarray(d.cuota_aproximada_barcaza if proxy else d.choice.eq(2),float)
    q=float(np.average(y,weights=w));pred=float(np.average(p,weights=w))
    ll=float(np.sum(w*(y*np.log(p)+(1-y)*np.log1p(-p)))) if not proxy else np.nan
    ll0=float(w.sum()*(q*np.log(q)+(1-q)*np.log1p(-q))) if not proxy else np.nan
    return dict(cuota_objetivo=q,cuota_predicha=pred,n_filas=len(d),tipo_filas='celdas_proxy_VL;NO_personas' if proxy else 'encuestas_individuales',
        n_efectivo_Kish=np.nan if proxy else w.sum()**2/(w*w).sum(),log_likelihood=ll,LL_solo_ASC=ll0,rho2=1-ll/ll0 if not proxy else np.nan)


def calcular(cfg):
    prior=ROOT/cfg['entrada_etapa11']
    base=pd.read_csv(prior/'base_calibracion_logit.csv');proxy=pd.read_csv(prior/'objetivos_ASC_peaton.csv')
    a=pd.read_csv(ROOT/'outputs/atributos_logit_actualizados/atributos_logit_actualizados.csv')
    cfg11=json.loads((prior/'config_utilizada.json').read_text())
    grid=prev.celdas_prediccion(a,cfg11)
    datasets=fuente_calibracion(base,proxy,cfg)
    central_cache={};pars=[];predictions=[];fits=[];diagnostics=[]
    for s in escenarios(cfg):
        slopes=model.coeficientes(cfg['beta_c_por_CLP'],s['VST'],s['ra'],s['re'])
        for seg,d in datasets.items():
            isproxy=seg=='PEATON';name=f"{seg}_{s['escenario']}"
            if s['factor']=='lambda':
                params,diag=central_cache[seg];diag=dict(diag,metodo='ASC central conservada por invariancia singleton; lambda supuesto, no estimado')
            else:
                params,diag=model.calibrar_ASC(d,slopes,name,s['lam'],isproxy)
                if s['escenario']=='central':central_cache[seg]=(params,diag)
            assert diag['convergio'],name
            stat=ajuste(d,params,isproxy)
            assert abs(stat['cuota_objetivo']-stat['cuota_predicha'])<1e-5,name
            print(name,params['ASC_barcaza'],stat['cuota_predicha'],flush=True)
            source='Objetivos proxy VL24h Etapa11; no cuota de personas' if isproxy else 'Misma base/pesos Etapa11; VL24h exploratorio' if seg=='VL' else 'Misma base/pesos Etapa11; CAM tierra10h vs ferry diario sin homologacion'
            fits.append(dict(segmento=seg,**s,**stat,ASC_barcaza=params['ASC_barcaza'],fuente_objetivo=source,convergio=diag['convergio']))
            diagnostics.append(dict(segmento=seg,**s,**diag))
            for p,value in dict(params,ASC_terrestre=0,lambda_lago=s['lam']).items():
                fixed=p!='ASC_barcaza';cost=p=='beta_c';v=value/10000 if cost else value
                pars.append(dict(segmento=seg,escenario=s['escenario'],parametro=p,valor=v,valor_escala_Biogeme=value,
                    unidad='utilidad_por_CLP' if cost else 'utilidad_por_hora' if p.startswith('beta') else 'adimensional',
                    metodo='supuesto' if fixed else 'calibrado',condicion='Normalizacion' if p=='ASC_terrestre' else 'Parametro no identificable con un cruce lacustre' if p=='lambda_lago' else cfg['metodo_pendientes'] if fixed else cfg['metodo_ASC_PEATON'] if isproxy else cfg['metodo_ASC_VL_CAM'],
                    fuente=cfg['fuente_numeros'] if fixed else source,referencias_conceptuales='Wardman2004;OECD/ITF2014, sin validacion numerica local' if p in ['beta_a','beta_e'] else 'EVALSO utilidad3.3; escenarios del estudio',
                    error_estandar=np.nan if fixed or isproxy else diag.get('SE_condicional',{}).get('ASC_barcaza',np.nan),
                    alcance_error='Condicional al modelo y pesos, NO diseno muestral' if not fixed and not isproxy else 'No corresponde',
                    unidad_decision=cfg['unidades_decision'][seg],VST_CLP_h=s['VST'],ratio_acceso=s['ra'],ratio_horario=s['re'],
                    ponderacion=cfg.get('ponderacion_'+seg,'proxy_VL24h'),recalibrada=s['factor']!='lambda' and not fixed))
            for _,r in grid.loc[grid.segmento.eq(seg)].iterrows():
                selected=d
                for k in K:selected=selected.loc[selected[k].eq(r[k])]
                rep=float(probabilidades(pd.DataFrame([r]),params,s['lam']).iloc[0]) if r.atributos_completos else np.nan
                pm=float(np.average(probabilidades(selected,params,s['lam']),weights=selected.weight)) if len(selected) else rep
                type_prediction='objetivo_proxy;NO_elecciones_personales' if len(selected) and isproxy else 'integracion_microdatos_soporte_calibracion' if len(selected) else 'extrapolacion_condicionada_fuera_soporte' if r.atributos_completos else 'NaN_falta_alternativa_peatonal_OD'
                for alternative,p in [('barcaza_actual',pm),('terrestre_chile',1-pm)]:
                    predictions.append(dict(**{k:r[k] for k in K},alternativa=alternative,probabilidad=p,probabilidad_atributo_medio=rep if alternative=='barcaza_actual' else 1-rep,
                        **s,ASC_barcaza=params['ASC_barcaza'],beta_c_por_CLP=slopes['beta_c']/10000,beta_t_por_h=slopes['beta_t'],beta_a_por_h=slopes['beta_a'],beta_e_por_h=slopes['beta_e'],
                        tipo=type_prediction,fuente_objetivo=source,unidad_decision=cfg['unidades_decision'][seg],supuestos_atributos=r.supuestos_atributos))
    return pd.DataFrame(pars),pd.DataFrame(predictions),pd.DataFrame(fits),diagnostics,datasets


def report(cfg,pars,pred,fit,checks):
    old=ROOT/cfg['entrada_etapa11']
    p11=pd.read_csv(old/'parametros_logit.csv');p11=p11.loc[p11.escenario.eq('central'),['segmento','parametro','valor','metodo']]
    pc=pars.loc[pars.escenario.eq('central'),['segmento','parametro','valor','metodo','error_estandar','unidad_decision']]
    cmp=p11.merge(pc,on=['segmento','parametro'],suffixes=('_11','_11B'),validate='one_to_one')
    save(cmp,'comparacion_parametros_etapas')
    q11=pd.read_csv(old/'probabilidades_situacion_actual.csv');q11=q11.loc[q11.escenario.eq('central')]
    q=pred.loc[pred.escenario.eq('central')&pred.alternativa.eq('barcaza_actual')].merge(q11[K+['P_barcaza']],on=K,validate='one_to_one')
    q['diferencia_puntos_porcentuales']=100*(q.probabilidad-q.P_barcaza);save(q,'comparacion_probabilidades_etapas')
    centrales=fit.loc[fit.escenario.eq('central')]
    main=q[q.origen.eq('Chile Chico')&q.destino.eq('Coyhaique')]
    ranges=pred.loc[pred.alternativa.eq('barcaza_actual')].groupby(K,dropna=False).probabilidad.agg(['min','max']).reset_index()
    ranges=ranges.loc[ranges.origen.eq('Chile Chico')&ranges.destino.eq('Coyhaique')]
    md=prev.md
    text=f'''# Etapa11B — Recalibración con pendientes de referencia y respaldo conceptual

Se conservaron intactos resultados, fuentes y matrices anteriores. Se reutilizó la base individual de11 y sus ponderaciones; no se reestimaron rutas ni expansiones. Se calibraron únicamente constantes en Biogeme3.3.2 para VL/CAM y un objetivo agregado proxy para PEATON. Cuatro OD dirigidos y cuatro estaciones; solo terrestre_chile/barcaza_actual. No se calcula nuevo cruce, SBO ni inducción.

## Parámetros numéricos y comparación

{md(cmp[['segmento','parametro','valor_11','metodo_11','valor_11B','metodo_11B','error_estandar']])}

Central solicitado: beta_c=-0,00002/CLP; beta_t=-0,20/h; beta_a=beta_e=-0,30/h; lambda0,70. **Todas las pendientes y lambda son supuestos de transferencia exploratoria del estudio; ninguna fue estimada aquí ni atribuida como estimación numérica de literatura**. Solo ASC se recalibra, con ASC_tierra0 y escala superior1. Biogeme recibe C/10000CLP y beta_c=-0,20 en esa escala; el CSV conserva ambas unidades. La antigua beta_e VL estimada condicionalmente se sustituye por la pendiente fija solicitada, sin sobrescribirla. El cambio de ASC compensa las nuevas pendientes; no demuestra un cambio observado de preferencias.

Errores estándar solo para ASC de VL/CAM: condicionales al modelo/ponderaciones normalizadas, no precisión poblacional ni diseño de interceptaciones. No se informa error para ASC proxy de personas ni parámetros fijados. Las sensibilidades lambda conservan ASC central por identidad algebraica, no se anuncian como nuevas calibraciones.

## Bibliografía: qué respalda y qué no

[Wardman2004, Transport Policy11(4),363–377, DOI10.1016/j.tranpol.2004.05.001](https://doi.org/10.1016/j.tranpol.2004.05.001); [manuscrito primario verificado](https://eprints.whiterose.ac.uk/id/eprint/3393/2/Public_Transport_Values_of_Time_secure.pdf), §2.2 y conclusiones. Revisa valoraciones diferenciadas de viaje, acceso, caminata, espera y frecuencia, con variación contextual. No proporciona coeficientes locales ni valida1,5 para La Tehuelche. No se transfieren sus montos monetarios británicos a Chile.

[OECD/ITF2014, Valuing Convenience in Public Transport](https://www.oecd.org/content/dam/oecd/en/publications/reports/2014/12/valuing-convenience-in-public-transport_g1g4525d/9789282107683-en.pdf), DOI10.1787/9789282107683-en, capítulo1pp33–43. Distingue componentes de conveniencia y cambios de horario; subraya diferencias entre headway y desplazamiento respecto de salida deseada. Respalda separar términos, no este multiplicador específico ni calibración de camiones lacustres. Los valores del estudio quedan parametrizados como supuestos.

El acceso del modelo vehicular es conducción hasta/desde la barcaza, no caminata a una parada. El desajuste0,25H no es espera aleatoria. Por tanto, los ratios de literatura sobre caminata/espera no son automáticamente ratios de estos atributos. No se aplica dos veces0,25 ni un multiplicador de headway a un tiempo ya transformado sin explicitarlo.

## Unidad de decisión y valor del tiempo

El cociente beta_t/beta_c es10000CLP/h **por unidad modelada**, no un VST social ni una medición local:

- VL: viaje de vehículo, con dinero total del grupo. No son10000por cada ocupante ni se multiplica por ocupación. Si hayvarios ocupantes, la equivalencia por persona depende de quién decide/paga y de agregar sus tiempos, no identificados.
- CAM: viaje de camión. No por tonelada, tripulante o valor de mercancía; no incluye un costo de demora comercial demostrado. El COV privado de fuente se conserva sin añadir otra vez salarios o CostGen.
- PEATON: viaje individual de pasajero general bajo un perfil de transporte público de referencia. La constante sigue condicionada a proxy de cuota VL, sin nueva evidencia de cuotas personales.

La igualdad numérica inicial es **prueba de referencia solicitada**, no igualdad económica demostrada entre segmentos. Cada segmento se recalibra separadamente a5000/10000/15000CLP por unidad-h, manteniendo beta_c=-0,00002/CLP: beta_t=-0,10/−0,20/−0,30 y ratios de acceso/horario centrales1,5. No se comparan ASCs de segmentos distintos como preferencias intrínsecas.

## Muestra, ponderaciones y objetivo

{md(centrales[['segmento','n_filas','tipo_filas','n_efectivo_Kish','cuota_objetivo','cuota_predicha','ASC_barcaza','log_likelihood','rho2','fuente_objetivo']])}

VL conserva61entrevistas en3estratos con ambas elecciones y expansión24h de sensibilidadCC_PC1_laboral: verano Chile Chico→Coyhaique, primavera ambos sentidos. No es cobertura anual ni completa del área. CAM conserva9entrevistas de mayo; tierra10h frente ferry diario sigue temporalmente no homologado. Sus cuotas no se elevan a flujos diarios verificados. Los pesos de11 se reutilizan exactamente, no se reemplazan por recuentos simples.

PEATON conserva3celdas objetivo de cuota/distribución VL como supuesto, **no3entrevistas ni elecciones terrestres de personas**. Biogeme maximiza `s*log(P_M)+(1−s)*log(P_T)` ponderado por celda, con s=cuota proxy y pesos normalizados a3. Es calibración contra un objetivo agregado, no MLE de elecciones personales; no se convierten sus fracciones en encuestas falsas. La condición de primer orden reproduce la cuota proxy global; no impone reproducir cada celda. Se conserva la base individual original sin modificarla.

## Probabilidades comparadas: Chile Chico → Coyhaique

Probabilidades de barcaza; tierra=1−barcaza. En celdas con muestra se integra sobre atributos individuales y pesos, no sobre un usuario promedio. Fuera del soporte se mantienen perfiles medios/imputaciones de11 y se etiqueta extrapolación. NaN no se reemplaza por0.

{md(main[['estacion','segmento','P_barcaza','probabilidad','diferencia_puntos_porcentuales','tipo']])}

El CSV central incluye ambas alternativas por separado, cuatro estaciones y los dos sentidos. PEATON Chile Chico↔Puerto Ibáñez sigueNaN cuando falta el servicio terrestre; no se infiere indisponibilidad confirmada ni se amplía el área.

## Sensibilidades, una a la vez

Acceso/viaje1/1,5/2; horario/viaje0,5/1/1,5; VST5000/10000/15000; lambda0,5/0,7/0,9. Todas se evalúan por segmento con idénticas filas/pesos. Se recalibra ASC cuando cambia una pendiente; para lambda se conserva la constante porque los nidos singleton no cambian probabilidades. No se combina la base de escenarios como una nueva muestra.

{md(fit[['segmento','escenario','VST','ra','re','lam','ASC_barcaza','cuota_predicha','rho2']])}

Rangos de probabilidad de barcaza para Chile Chico→Coyhaique entre sensibilidades, **no intervalos de confianza**:

{md(ranges)}

La cuota global queda fijada por recalibrar ASC: su estabilidad no es validación independiente. Importa cómo se redistribuyen probabilidades por OD/estación y fuera de soporte. Cuando una diferencia de acceso es constante dentro del soporte, variar beta_a se absorbe en ASC y no identifica su efecto. Puede cambiar la extrapolación a Puerto Ibáñez. El nuevo beta_e fijo reduce la libertad para reproducir contrastes estacionales que la pendiente de11 capturaba; aquella pendiente también podía recoger cambios de mercado omitidos. El coeficiente no se vuelve causal al citar literatura.

Los rho2 negativos respecto de una sola constante indican peor ajuste por restricciones impuestas, no fallas de convergencia. No se ocultan. Para peatones no se interpreta ajuste proxy como validación empírica. Las probabilidades de invierno son extrapolación de oferta, no demanda invernal observada ni anualización.

## Fórmula operacional heredada, sin duplicaciones

Se conserva íntegra la construcción de11: vehículos barco t_viaje=navegación+anticipación2h+desembarque0,5h; t_acceso=conducción de todos los tramos terrestres. Tierra t_viaje=conducción y acceso0. Peatones bimodal6h se divide en viaje3,5h y acceso residual2,5h como supuesto, sin volver a sumar esas operaciones; terrestre bus8h. Frecuencia11diciembre–abril y8mayo–noviembre, t_horario0,25×168/f y otoño mensual ponderado. Son atributos construidos/supuestos de11, no nuevas mediciones.

Se conservan dinero privado, tarifas del equipo y supuestos de pagadores, fecha/IPC, cargos y longitudes de11. No se sustituye C por CG HDM4 ni se suma tiempo monetizado a C. El dato bibliográfico no resuelve vigencia tarifaria, itinerarios de bus o facturación faltantes.

## Jerarquía y reproducción

Escala superior1; mu_lagoBiogeme=1/lambda. Con un solo cruce en el nido lago, `lambda*log(exp(V_M/lambda))=V_M`: lambda no es estimable y sus sensibilidades actuales son invariantes. Queda preparado para etapa posterior, sin incorporar ahora otro cruce ni estimar su ASC.

Ejecutar `.venv/bin/python scripts/11b_recalibrar_logit.py`. Configuración: `data/templates/config_calibracion_logit_11b.json`. Modelo Biogeme: `scripts/modelo_biogeme_11b.py`, copia de revisión en esta carpeta; reutiliza `scripts/modelo_biogeme.py` inmutable. Código y versiones registradas; no requiere repetir fuentes/matrices.

Entregables: parametros_logit_recalibrados.csv; probabilidades_base_recalibradas.csv (central); sensibilidades_parametros.csv (variaciones por OD/estación/alternativa); comparacion_calibraciones.md. Adicionales: ajuste_recalibraciones.csv; comparaciones numéricas con11; objetivos/base realmente utilizados; referencias y hashes. Los archivos derivados quedan excluidos deGit y no se publican.

Verificaciones: `{json.dumps(checks,ensure_ascii=False)}`. Integridad_anteriores.csv conserva hashes de matrices y resultados07–11. Esta etapa no abre ni modifica los microdatos originales, sino la base derivada y objetivos previos. No se modificaron fuentes ni resultados previos. Sin commit/push.
'''
    (OUT/'comparacion_calibraciones.md').write_text(text,encoding='utf-8')


def main():
    cfg=json.loads((ROOT/'data/templates/config_calibracion_logit_11b.json').read_text())
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'biogeme').mkdir(exist_ok=True)
    protected=[p for name in ['matrices_od_referencia','expansion_temporal_terrestre','atributos_alternativas','atributos_logit_actualizados','calibracion_logit'] for p in (ROOT/'outputs'/name).rglob('*') if p.is_file()]
    # Las entradas originales ya están fuera del repo; esta etapa solo lee resultados previos.
    before={p:sha(p) for p in protected}
    os.chdir(OUT/'biogeme')
    pars,pred,fit,diag,sets=calcular(cfg)
    save(pars,'parametros_logit_recalibrados');save(pred.loc[pred.escenario.eq('central')],'probabilidades_base_recalibradas')
    center=pred.loc[pred.escenario.eq('central'),K+['alternativa','probabilidad']].rename(columns={'probabilidad':'probabilidad_central'})
    sens=pred.loc[~pred.escenario.eq('central')].merge(center,on=K+['alternativa'],validate='many_to_one')
    sens['diferencia_puntos_porcentuales']=100*(sens.probabilidad-sens.probabilidad_central);save(sens,'sensibilidades_parametros')
    save(fit,'ajuste_recalibraciones')
    for seg,g in sets.items():save(g,f'base_reutilizada_{seg}')
    save(cfg['referencias'],'referencias_parametros')
    (OUT/'diagnosticos_biogeme.json').write_text(json.dumps(diag,ensure_ascii=False,indent=2,default=float))
    (OUT/'config_utilizada.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2))
    source=ROOT/'scripts/modelo_biogeme_11b.py';shutil.copyfile(source,OUT/source.name)
    import platform
    from importlib.metadata import version
    (OUT/'entorno_ejecucion.json').write_text(json.dumps(dict(python=platform.python_version(),biogeme=version('biogeme'),codigo={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),source,ROOT/'scripts/modelo_biogeme.py']}),indent=2))
    central=pars.loc[pars.escenario.eq('central')]
    checks=dict(betas_centrales_correctos=bool(np.allclose(central.loc[central.parametro.eq('beta_c'),'valor'],-.00002)&np.allclose(central.loc[central.parametro.eq('beta_t'),'valor'],-.2)&np.allclose(central.loc[central.parametro.isin(['beta_a','beta_e']),'valor'],-.3)),
        signos_correctos=bool(pars.loc[pars.parametro.str.startswith('beta'),'valor'].lt(0).all()),ASC_tierra0=bool(pars.loc[pars.parametro.eq('ASC_terrestre'),'valor'].eq(0).all()),
        suma_probabilidades1=bool(np.allclose(pred.groupby(K+['escenario'],dropna=False).probabilidad.sum(min_count=2).dropna(),1)),
        probabilidades_en_rango=bool(pred.probabilidad.dropna().between(0,1).all()),
        no_SE_parametros_fijos=bool(pars.loc[pars.metodo.eq('supuesto'),'error_estandar'].isna().all()),
        cuotas_globales_reproducidas=bool(np.allclose(fit.cuota_objetivo,fit.cuota_predicha,atol=1e-5)),
        muestras_VL61_CAM9=bool(len(sets['VL'])==61 and len(sets['CAM'])==9),
        lambda_singleton_invariante=bool(sens.loc[sens.factor.eq('lambda'),'diferencia_puntos_porcentuales'].fillna(0).abs().lt(1e-10).all()),
        datos_previos_intactos=all(sha(p)==h for p,h in before.items()))
    save([dict(archivo=str(p.relative_to(ROOT)),sha256_antes=h,sha256_despues=sha(p),intacto=sha(p)==h) for p,h in before.items()],'integridad_anteriores')
    (OUT/'validacion.json').write_text(json.dumps(checks,indent=2))
    report(cfg,pars,pred,fit,checks)
    assert all(checks.values()),checks
    print('CENTRALES',fit.loc[fit.escenario.eq('central')].to_json(orient='records'),flush=True)
    print('VALIDACION',checks,flush=True)


if __name__=='__main__':main()
