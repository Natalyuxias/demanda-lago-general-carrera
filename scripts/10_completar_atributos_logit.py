"""Actualización incremental de atributos: dos alternativas, sin calibración.

Reutiliza paso09 y caches comprobados contra el Excel original. No ejecuta 07/08/09.
"""
from pathlib import Path
import calendar
import hashlib
import importlib.util
import json
import math
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from demanda.preparacion_logit import homologar,tiempo_vehiculo,tarifa_personas,tiempo_servicio_completo
from demanda.atributos import comprobar_secuencia
BASE=ROOT.parent
CACHE=ROOT/'data/interim/estimacion_preliminar'
OUT=ROOT/'outputs/atributos_logit_actualizados'
NAN=math.nan
KEY=['origen','destino','segmento','estacion','alternativa']
NECESIDADES={
    'VST_privado_no_identificado':('Solo impide CG valorizado previo; no impide estimar betas de tiempo y costo si el diseño lo permite','Justificar VST privado externo o derivarlo posteriormente de beta_t/beta_c identificado'),
    'longitud_facturable_y_regla_redondeo':('Condiciona tarifa CAM','Tickets o protocolo: longitud total con accesorios/remolque, decimales y unidad de cobro'),
    'condicion_conductor_por_ticket':('Condiciona costo monetario','Ticket/contrato por fecha que confirme servicio subvencionado y conductor liberado'),
    'edades_y_exenciones_acompanantes':('Condiciona numero de pagadores','Ocupantes por categoría tarifaria y comprobante de pago, sin inferir edades desde encuestado'),
    'fecha_exacta_tarifa':('Condiciona homologación, no el valor nominal publicado','Mes de vigencia del tarifario tabla52'),
    'itinerario_bus_y_desfase_propio':('Condiciona horario y disponibilidad de alternativa pública','Calendario de bus por sentido/campaña y salida deseada; confirmar integración con ferry'),
    'desembarque_supuesto_no_medido':('Sensibilidad operacional, no bloqueo aritmético','Medir inicio/fin de desembarque por zarpe y categoría'),
    'modo_bus_no_asignable_a_todos_peatones':('Condiciona asignación individual de atributos','Operador, servicio y billete utilizado por pasajero'),
    'tarifa_integrada_actual_no_identificada':('Condiciona costo peatonal','Tarifa pública histórica bus más ferry, detalle de inclusión y exenciones'),
    'tasas_peajes_cargos_no_verificados':('Condiciona costo completo','Comprobantes y tarifas de cargos efectivamente aplicables por ruta/fecha'),
    'accesos_intrazonales_individuales':('Limita precisión espacial de la reconstrucción','Vincular origen/destino puntual de EOD a red; no sustituir comuna por localidad')}


def load_script(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/f'scripts/{name}.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


prev=load_script('07_matrices_od_referencia')


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(d,name):pd.DataFrame(d).to_csv(OUT/f'{name}.csv',index=False,encoding='utf-8-sig',na_rep='NaN')
def md(d):
    def f(x):
        if pd.isna(x):return 'Pendiente'
        if isinstance(x,(float,np.floating)):return f'{x:,.3f}'
        return str(x).replace('|','/').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(d.columns)+' |','| '+' | '.join(['---']*len(d.columns))+' |']+['| '+' | '.join(f(x) for x in row)+' |' for row in d.itertuples(index=False,name=None)])


def datos(cfg):
    path=BASE/'Cap 6/BBDD EOD/Base de datos agregada.xlsx';digest=sha(path)
    def cache(key):
        assert (CACHE/f'{key}.sha256').read_text()==digest,f'Cache desactualizado: {key}'
        return pd.read_pickle(CACHE/f'{key}.pkl')
    a=cache('eod_original_seleccion');b=cache('eod_valida_seleccion')
    more=cache('eod_ubicacion_fronteras_matrices');geo=cache('eod_direcciones_horario_matrices')
    # Única lectura nueva: variables de modos, edad, carga y ocupación, sin exportar registros.
    extra=prev.prev.cache_frame(path,'BBDD-1','eod_modos_pasajeros_atributos',digest,False,
        usecols=lambda c:c in ['ID 2','Edad','Ocupantes del vehículo','Tamaño del Grupo','Longitud en metros','Tipo de vehículo de carga','Número de ejes'] or str(c).startswith('Modo '))
    d=a.merge(b,on='ID 2',validate='one_to_one').merge(more,on='ID 2',validate='one_to_one').merge(geo,on='ID 2',validate='one_to_one').merge(extra,on='ID 2',validate='one_to_one')
    mc=json.loads((ROOT/'data/templates/config_matrices_od.json').read_text())
    rules=json.loads((ROOT/'data/templates/config_rutas_terrestres.json').read_text())
    d['estacion']=d['Versión'].str.strip().map(mc['estacion_campana'])
    d['segmento']=d['Tipo usuario'].map(mc['segmentos']).fillna('OTRO_PASAJERO')
    for side in ['origen','destino']:
        z=d.apply(lambda r:prev.resolver_lugar(r,side,mc),axis=1)
        d[side]=z.map(lambda v:v[0]);d['nivel_'+side]=z.map(lambda v:v[1])
    fs=[c for c in a if 'transbordador' in c.lower()];bs=[c for c in more if 'fronterizo' in c.lower()]
    flags=d.apply(lambda r:pd.Series(prev.clasificar(r,fs,bs,mc,rules)),axis=1)
    d=pd.concat([d,flags],axis=1)
    d['en_cruce']=d['Lugar encuestado'].map(prev.prev.es_lago)
    d['sentido_cruce']=d['Sentido Viaje'].map(lambda s:prev.prev.sentido(s) if prev.prev.es_lago(s) else '')
    d['longitud_num']=pd.to_numeric(d['Longitud en metros'],errors='coerce')
    d['ocupantes_num']=pd.to_numeric(d['Ocupantes del vehículo'],errors='coerce')
    return d,digest


def estadisticas(d,cfg):
    cam=d.loc[d.segmento.eq('CAM')].copy();rows=[]
    universes={'cruce_actual_19':cam.loc[cam.en_cruce],
               'Cerro_Castillo_extremo_Chile_Chico_complemento':cam.loc[cam['Lugar encuestado'].str.contains('Cerro Castillo',na=False)&(cam.origen.eq('Chile Chico')|cam.destino.eq('Chile Chico'))]}
    for universe,g in universes.items():
        groups=[('total',{},g)]
        for cols in [['estacion','sentido_cruce'],['Tipo de vehículo de carga'],['Tipo de vehículo de carga','Número de ejes']]:
            for key,z in g.groupby(cols,dropna=False):
                key=key if isinstance(key,tuple) else (key,)
                groups.append(('_'.join(cols),dict(zip(cols,key)),z))
        for level,meta,z in groups:
            val=z.loc[z.longitud_num.gt(0)&np.isfinite(z.longitud_num),'longitud_num']
            rows.append(dict(universo=universe,nivel=level,**meta,registros_validos=len(z),n_longitud_numerica_positiva=len(val),
                n_longitud_faltante_o_no_positiva=len(z)-len(val),longitud_media_m=val.mean(),longitud_mediana_m=val.median(),
                longitud_min_m=val.min(),longitud_max_m=val.max(),n_longitud_hasta5_5m=int(val.le(5.5).sum()),
                tarifa_lineal_media_nominal_CLP=val.mean()*cfg['tarifas_ARISTO']['metro_lineal'],
                tarifa_lineal_mediana_nominal_CLP=val.median()*cfg['tarifas_ARISTO']['metro_lineal'],
                tarifa_min_nominal_CLP=val.min()*cfg['tarifas_ARISTO']['metro_lineal'],tarifa_max_nominal_CLP=val.max()*cfg['tarifas_ARISTO']['metro_lineal'],
                tarifa_media_redondeando_metro_superior_sens_CLP=np.ceil(val).mean()*cfg['tarifas_ARISTO']['metro_lineal'],
                unidad='m por vehiculo; CLP por viaje sujeto a tarifa lineal',
                fuente='Cap6/BBDD EOD/Base de datos agregada.xlsx; BBDD-1 longitud/categoria/ejes; BBDD-2 validas',
                estado='declaracion_numerica_observada; facturacion_no_verificada',
                limitacion='No ponderado; no representatividad poblacional; valores y categorias discordantes se conservan como alertas en salida local. Tarifa7310*L solo si sujeto a cobro lineal; sin prueba redondeo; no extrapolar Cerro a flota lacustre'))
    stats=pd.DataFrame(rows);save(stats,'camiones_longitudes_tarifas')
    occup=[]
    vl=d.loc[d.segmento.eq('VL') & d.ruta.isin(cfg['alternativas'])].copy()
    for universe,g in [('VL_cruce_completo',vl.loc[vl.en_cruce]),('VL_rutas_confirmadas_extremo_Chile_Chico',vl.loc[vl.origen.eq('Chile Chico')|vl.destino.eq('Chile Chico')])]:
        groups=[('total',{},g)]
        for cols in [['estacion','sentido_cruce'],['estacion','origen','destino','ruta']]:
            for k,z in g.groupby(cols,dropna=False):
                k=k if isinstance(k,tuple) else (k,);groups.append(('_'.join(cols),dict(zip(cols,k)),z))
        for level,meta,z in groups:
            val=z.loc[z.ocupantes_num.ge(1)&(z.ocupantes_num%1).eq(0),'ocupantes_num'];limited=val[val.le(cfg['ocupacion_control_sensibilidad_max_VL'])]
            occup.append(dict(universo=universe,nivel=level,**meta,n_encuestas=len(z),n_ocupantes_validos=len(val),ocupantes_media=val.mean(),ocupantes_mediana=val.median(),
                ocupantes_min=val.min(),ocupantes_max=val.max(),n_sobre_control=int(val.gt(cfg['ocupacion_control_sensibilidad_max_VL']).sum()),ocupantes_media_sin_sobre_control=limited.mean(),
                fuente='BBDD-1 Ocupantes del vehiculo; unidad vehiculo con conductor; no sumar como peatones',limitacion='Muestra sin ponderacion; edad del encuestado no describe edades de todos los ocupantes; no identifica exenciones ni pagos'))
    save(occup,'ocupantes_vehiculos')
    return stats


def modos_peatones(d,cfg):
    p=d.loc[d.en_cruce & d.segmento.eq('PEATON')].copy();rows=[]
    for label,g in [('cruce_completo',p),('OD_Chile_Chico_Coyhaique',p.loc[((p.origen.eq('Chile Chico')&p.destino.eq('Coyhaique'))|(p.origen.eq('Coyhaique')&p.destino.eq('Chile Chico')))])]:
        for keys,z in g.groupby(['estacion','origen','destino'],dropna=False):
            cols=['Modo 1 para llegar al transbordador','Modo 2 para llegar al transbordador','Modo 3 para llegar al transbordador','Modo 1 para llegar a destino','Modo 2 para llegar a destino','Modo 3 para llegar a destino']
            # Una fila agregada por patron, nunca multiplicar por Tamaño del Grupo.
            gg=z.fillna({c:'no_declarado' for c in cols}).groupby(cols,dropna=False).size()
            for modes,n in gg.items():
                rows.append(dict(tipo='modos_observados',universo=label,estacion=keys[0],origen=keys[1],destino=keys[2],
                    servicio='operador_no_identificado',alternativa='barcaza_actual',encuestas=int(n),
                    modos_acceso=' > '.join(modes[:3]),modos_egreso=' > '.join(modes[3:]),
                    tiempo_publicado_h=NAN,tarifa_historica_confirmada_CLP=NAN,fuente='BBDD-1 Modos 1/2/3 para llegar al transbordador y a destino',
                    limitaciones='Declarar Bus no identifica Carolina, bus coordinado ni tarifa; caminata puede ser primer tramo, no todo el acceso; muestra de personas/grupos no expandida'))
    for s in cfg['servicios']:
        rows.append(dict(tipo='servicio_publicado',universo='referencia_servicio_no_asignada_a_personas',servicio=s['servicio'],alternativa=s['alternativa'],
                         origen_destino=s['OD'],tiempo_publicado_h=s['tiempo_publicado_h'],tarifa_historica_confirmada_CLP=NAN,fuente=s['fuente'],limitaciones=s['alcance']))
    ref=cfg['referencia_tarifa_Carolina_OC']; factor=cfg['ipc'][cfg['mes_base_privado']]/cfg['ipc'][ref['mes']]
    rows.append(dict(tipo='precio_institucional_sensibilidad',servicio='Carolina',alternativa='barcaza_actual',origen_destino='Coyhaique <-> Chile Chico',
        tarifa_referencia_nominal_CLP=ref['precio_CLP'],fecha_precio=ref['mes'],tarifa_referencia_CLP_dic2025=ref['precio_CLP']*factor,
        tarifa_historica_confirmada_CLP=NAN,fuente=ref['fuente'],limitaciones=ref['estado']+'; no sumar otro pasaje barco si se interpreta paquete'))
    rows.append(dict(tipo='contraste_CITRA',servicio='carga',origen_destino='area_estudio_CITRA_no_flota_barcaza',encuestas=431,fuente='CITRA Informe2 corregido pp86-87 seccion6.1.2',
        limitaciones='53% dos ejes;47% mas de dos;63% con carga37% vacio. Sin longitudes; no combinar microdatos ni transferir proporciones'))
    save(rows,'transporte_publico_peatones')
    summaries=[]
    for c in ['Modo 1 para llegar al transbordador','Modo 1 para llegar a destino']:
        for m,n in p[c].fillna('no_declarado').value_counts().items():summaries.append(dict(campo=c,modo=m,encuestas=int(n),universo='99 peatones interceptados; no personas expandidas'))
    save(summaries,'resumen_modos_peatones')
    other=d.loc[d.en_cruce & d['Tipo usuario'].str.contains('bus|van|transfer',case=False,na=False)]
    save(other.groupby(['estacion','Tipo usuario'],dropna=False).size().reset_index(name='encuestas'),'otros_pasajeros_transporte_publico_observados')


def perfil(g,field):
    v=g[field];v=v.loc[np.isfinite(v)&v.gt(0)]
    return len(v),v.mean()


def construir(a,d,cfg):
    rows=[];cost=[];sens=[];missing=[]
    factor=cfg['ipc'][cfg['mes_base_privado']]/cfg['ipc'][cfg['mes_referencia_tarifas_imputado']]
    for r in a.to_dict('records'):
        base={k:r[k] for k in KEY};boat=r['alternativa']=='barcaza_actual';seg=r['segmento'];station=r['estacion']
        dr=r['tiempo_conduccion_terrestre_h'];nav=r['tiempo_navegacion_h'];cov=r['COV_terrestre_privado_ARISTO_CLP']
        direction='Chile Chico a Ibanez' if r['origen']=='Chile Chico' else 'Ibanez a Chile Chico'
        sample=d.loc[d.en_cruce & d.segmento.eq(seg)&d.estacion.eq(station)&d.sentido_cruce.eq(direction)]
        exact=sample.loc[sample.origen.eq(r['origen'])&sample.destino.eq(r['destino'])]
        op=exact if len(exact) else sample
        nocc,occ=perfil(op,'ocupantes_num');nlen,lmean=perfil(op,'longitud_num')
        origin_profile='OD_estacion_sentido_exacto' if len(exact) else 'cruce_estacion_sentido_transferido_a_OD_no_observado'
        months=cfg['estaciones'][station];days=[calendar.monthrange(cfg['ano_ponderacion_dias'],m)[1] for m in months]
        h=sum(n*168/cfg['frecuencia_mensual_por_sentido'][str(m)] for m,n in zip(months,days))/sum(days) if boat else NAN
        wh=cfg['w_horario']*h if boat else 0.0
        prior=cfg['anticipacion_h'][seg] if boat else 0.0;deb=cfg['desembarque_h']['central'] if boat else 0.0
        tariff=0.0 if not boat else cfg['tarifas_ARISTO']['vehiculo_hasta_5_5m'] if seg=='VL' else cfg['tarifas_ARISTO']['metro_lineal']*lmean if seg=='CAM' else cfg['tarifas_ARISTO']['adulto']
        person=0.0 if not boat else NAN
        if boat and seg in ['VL','CAM']:person=tarifa_personas(occ,cfg['tarifas_ARISTO']['adulto'],True)
        profile='vehiculo_privado' if seg in ['VL','CAM'] else 'modo_acceso_no_identificado'
        bus=NAN;busfare=NAN;totalmoney=NAN;cg=NAN
        physical,withschedule=tiempo_vehiculo(dr,nav,prior,deb,wh) if seg!='PEATON' else (NAN,NAN)
        access=r['t_acceso_modelo_h'];travel=r['t_viaje_modelo_h'];prevadd=prior;debadd=deb
        issues=['accesos_intrazonales_individuales','tasas_peajes_cargos_no_verificados','VST_privado_no_identificado']
        if seg=='PEATON':
            access=NAN;travel=NAN;dr=NAN;cov=NAN;prevadd=prior;debadd=deb
            if set([r['origen'],r['destino']])=={'Chile Chico','Coyhaique'}:
                profile='bus_Carolina_condicional' if boat else 'bus_Interlagos_condicional'
                bus=cfg['servicios'][0 if boat else 1]['tiempo_publicado_h']
                physical=tiempo_servicio_completo(bus);travel=bus
                # Desglose desconocido dentro del tiempo total: NaN NO implica sumarlo de nuevo.
                access=NAN;prevadd=0.0;debadd=0.0
                withschedule=NAN
                if boat:
                    nav=NAN;deb=NAN;wh=NAN
                    issues+=['desglose_interno_6h_no_identificado','itinerario_bus_y_desfase_propio','tarifa_integrada_actual_no_identificada','modo_bus_no_asignable_a_todos_peatones']
                else:issues+=['itinerario_bus_y_desfase_propio','tarifa_bus_no_identificada','servicio_referencia_no_asignado_a_todos_peatones']
            else:issues+=['modo_y_tiempo_acceso_egreso_peaton','tarifa_transporte_publico_si_corresponde']
            knownmoney=tariff if boat else NAN;centralmoney=NAN
            # Tarifa barco del servicio coordinado tampoco se suma: integrada/no integrada desconocido.
            if boat and profile=='bus_Carolina_condicional':tariff=NAN;knownmoney=NAN
        else:
            knownmoney=cov+(tariff*factor if boat and pd.notna(tariff) else 0)
            centralmoney=cov+(tariff+person)*factor if boat and pd.notna(tariff) and pd.notna(person) else cov if not boat else NAN
            if boat:
                issues+=['condicion_conductor_por_ticket','edades_y_exenciones_acompanantes','fecha_exacta_tarifa','desembarque_supuesto_no_medido']
                if seg=='CAM':issues+=['longitud_facturable_y_regla_redondeo','tarifa_lineal_para_categoria_de_carga','costo_VP_mixto_no_CAM_individual']
                if not len(exact):issues+=['perfil_ocupacion_longitud_transferido_desde_cruce']
                if pd.isna(tariff):issues+=['sin_longitud_en_estrato']
        row=dict(**base,ruta_id=r['ruta_id'],secuencia_arcos=r['secuencia_arcos'],secuencia_nodos=r['secuencia_nodos'],perfil_acceso=profile,
            unidad_decision='persona_pasajera' if seg=='PEATON' else 'viaje_vehiculo',
            unidad_costos='CLP_por_persona_viaje' if seg=='PEATON' else 'CLP_por_vehiculo_viaje_con_ocupantes_del_grupo',
            unidad_tiempos='horas_por_viaje; horario_es_indice_no_duracion_fisica',
            alcance_OD=r['alcance_OD'],origen_anclaje=r['origen_anclaje'],destino_anclaje=r['destino_anclaje'],
            distancia_terrestre_km=r['distancia_terrestre_total_km'],tiempo_conduccion_h=dr,tiempo_bus_servicio_completo_h=bus,
            tiempo_navegacion_h=nav,tiempo_acceso_h=access,tiempo_previo_zarpe_referencia_h=prior,tiempo_previo_adicional_a_servicio_h=prevadd,
            tiempo_desembarque_central_h=deb,desembarque_adicional_a_servicio_h=debadd,
            t_viaje_modelo_h=travel,H_central_168_f_h=h,t_horario_barcaza_potencial_h=cfg['w_horario']*h if boat else 0,
            penalizacion_horario_central_h=wh,H_calendario_sensibilidad_h=r['H_h'] if boat else NAN,
            t_horario_bus_propio_h=NAN if seg=='PEATON' else 0,
            tiempo_fisico_escenario_central_h=physical,tiempo_con_horario_escenario_central_h=withschedule,
            alcance_tiempo_fisico='servicio_bus_completo_sin_acceso_externo_identificado' if profile.startswith('bus_') else 'entre_anclajes_red; acceso_intrazonal_individual_no_identificado',
            tiempo_fisico_puerta_a_puerta_confirmado_h=NAN,
            COV_privado_CLP_dic2025=cov,tarifa_bus_confirmada_CLP=busfare,tarifa_barcaza_principal_nominal_CLP=tariff,
            tarifa_personas_esc_conductor_liberado_acompanantes_adultos_CLP=person,
            costo_componentes_identificados_CLP_dic2025=knownmoney,costo_monetario_escenario_central_CLP_dic2025=centralmoney,
            costo_monetario_privado_total_confirmado_CLP=totalmoney,costo_generalizado_privado_CLP=cg,VST_privado_CLP_h=NAN,
            n_perfil=(nocc if seg=='VL' else nlen if seg=='CAM' else NAN) if boat else NAN,ocupantes_media_muestral=occ if boat and seg in ['VL','CAM'] else NAN,
            longitud_CAM_media_muestral_m=lmean if boat and seg=='CAM' else NAN,fuente_perfil=origin_profile if boat else 'no_aplica_al_COV_terrestre',
            factor_IPC_tarifa_convencion_enero2026_a_dic2025=factor,base_precios='CLP diciembre2025; tarifa enero2026 imputada solo escenario',
            fuente_ruta=r['fuente_distancia'],fuente_tiempos='ARISTO red L/V; bus tabla61 pp127-128; condiciones2025 anticipacion; supuestos usuario desembarque',
            fuente_costos='ARISTO HDM4 Q/R privados dic2025; tabla52 p121; EOD ocupantes/longitud; SII IPC',
            fuente_horario='Usuario f11/8; EVALSO w0.25; escenario central168/f ponderado por dias',
            confianza='reconstruccion_verificada; tiempos_y_dinero_completos_condicionados_a_supuestos' if seg!='PEATON' else 'servicio_bus_condicional_y_modo_personal_no_identificado',
            supuestos='Vias y COV de09 estaticos; desembarque0.5h vehiculos; exencion chofer condicional; acompanantes adultos pagadores; tasa adicional0 SOLO escenario; fecha tarifa enero2026 imputada; no VST',
            faltantes=';'.join(issues),preparado_calibracion_con_atributos_observados_completos=False)
        rows.append(row)
        cost.append(dict(**base,perfil_acceso=profile,COV_CLP_dic2025=cov,tarifa_vehiculo_o_peaton_nominal_CLP=tariff,
            conductor_adicional_confirmado_CLP=NAN if boat and seg!='PEATON' else 0 if not boat else NAN,
            conductor_liberado_escenario_CLP=0 if boat and seg!='PEATON' else NAN,
            conductor_paga_sensibilidad_CLP=cfg['tarifas_ARISTO']['adulto'] if boat and seg!='PEATON' else NAN,
            acompanantes_adultos_escenario_nominal_CLP=person,numero_ocupantes_media_muestral=occ if seg!='PEATON' else NAN,
            n_ocupantes_validos=nocc if seg!='PEATON' else NAN,perfil=origin_profile,
            tarifa_bus_confirmada_CLP=busfare,tasa_embarque_confirmada_CLP=NAN if boat else 0,otros_cargos_confirmados_CLP=NAN,
            exenciones_acompanantes_observadas=NAN,componente_personas_min_escenario_CLP=0 if boat else 0,
            componente_personas_max_sin_exenciones_conductor_paga_CLP=tarifa_personas(occ,cfg['tarifas_ARISTO']['adulto'],False) if boat and seg!='PEATON' else NAN,
            factor_IPC=factor if boat else 1,costo_central_condicional_CLP_dic2025=centralmoney,costo_total_confirmado_CLP=NAN,
            costo_central_si_conductor_paga_CLP_dic2025=centralmoney+cfg['tarifas_ARISTO']['adulto']*factor if boat and seg!='PEATON' else NAN,
            costo_central_si_acompanantes_exentos_CLP_dic2025=cov+tariff*factor if boat and seg!='PEATON' and pd.notna(tariff) else NAN,
            estado='Costos y sumas de escenarios NO equivalen a desembolso efectivamente pagado; no doble IVA; COV privado, no CostGen',
            fuente=cfg['fuente_tarifas'],fecha_tarifa='2026-01 supuesto; mes real no identificado',regla_conductor=cfg['regla_conductor']))
        for scenario,duration in cfg['desembarque_h'].items():
            sd=duration if boat else 0;pp=prior
            if seg=='PEATON' and profile in ['bus_Carolina_condicional','bus_Interlagos_condicional']:
                phy=bus;tot=NAN;sd=NAN if boat else 0
                method='Tiempo completo bus sin volver a sumar anticipacion/navegacion/desembarque; no aplicar automatico wH de barcaza'
            else:
                phy,tot=tiempo_vehiculo(dr,nav,pp,sd,wh)
                method='Conduccion_total+nav+previo+desembarque; acceso ya incluido en conduccion; wH separado'
            sens.append(dict(**base,perfil_acceso=profile,escenario_desembarque=scenario,desembarque_h=sd,anticipacion_exigida_h=prior,
                tiempo_fisico_h=phy,horario_central_168f_h=wh,tiempo_con_horario_h=tot,
                horario_calendario_sensibilidad_h=r['t_horario_h'] if boat else 0,
                metodo=method,fuente_desembarque=cfg['fuente_desembarque'],estado='supuesto_exploratorio; no medicion ni precision operacional'))
        for issue in issues:
            importance,needed=NECESIDADES.get(issue,('Condiciona precisión o representatividad; no resolver como cero',issue.replace('_',' ')))
            missing.append(dict(**base,atributo=issue,importancia=importance,dato_requerido=needed,
                efecto='VST no es necesario para utilidad con tiempo y costo separados' if issue=='VST_privado_no_identificado' else 'distinguir escenario condicional de observación'))
    attrs=pd.DataFrame(rows);save(attrs,'atributos_logit_actualizados');save(cost,'costos_monetarios_desglosados')
    save(sens,'sensibilidad_tiempos_operacionales');save(missing,'faltantes_logit_actualizados')
    return attrs


def diagnostico(a,d,cfg):
    core=set(map(tuple,a[['origen','destino']].drop_duplicates().values.tolist()))
    scope=d.loc[[(o,t) in core for o,t in zip(d.origen,d.destino)]].copy()
    selected=scope.loc[scope.ruta.isin(cfg['alternativas'])&scope.segmento.isin(cfg['segmentos'])]
    counts=selected.groupby(['estacion','origen','destino','segmento','ruta'],dropna=False).size().reset_index(name='encuestas_eleccion_identificada')
    counts['unidad']='encuestas_validas; no cuotas poblacionales';counts['ponderador_individual_verificado']=NAN
    counts['advertencia']='Interceptacion condicionada a ruta/punto; no mezclar recuentos simples ni pesos10h/24h con barcaza como pesos inclusion certificados'
    save(counts,'observaciones_eleccion_identificada')
    coverage=a[['origen','destino','segmento','estacion']].drop_duplicates().copy()
    for route in cfg['alternativas']:
        n=counts.loc[counts.ruta.eq(route),['origen','destino','segmento','estacion','encuestas_eleccion_identificada']].rename(columns={'encuestas_eleccion_identificada':'n_'+route})
        coverage=coverage.merge(n,how='left',on=['origen','destino','segmento','estacion'],validate='one_to_one')
        # Cero significa ninguna entrevista confirmada, nunca demanda nula.
        coverage['n_'+route]=coverage['n_'+route].fillna(0).astype(int)
    coverage['ambas_elecciones_muestrales']=coverage.n_terrestre_chile.gt(0)&coverage.n_barcaza_actual.gt(0)
    coverage['alcance']='Cobertura muestral; ninguna entrevista no equivale a demanda cero; no probabilidades de eleccion'
    save(coverage,'cobertura_elecciones_por_OD')
    excl=[dict(universo='OD_focal_resuelto_y_segmentos_modelo',total=int((scope.segmento.isin(cfg['segmentos'])).sum()),incluidas=len(selected),
        excluidas_sin_ruta_modelo=int((scope.segmento.isin(cfg['segmentos'])&~scope.ruta.isin(cfg['alternativas'])).sum()),
        motivo='Rutas fuera del alcance y desconocidas excluidas, sin redistribucion')]
    save(excl,'control_seleccion_muestra')
    design=[];ranks=[]
    for seg in ['VL','CAM']:
        z=a[a.segmento.eq(seg)]
        for _,g in z.groupby(['origen','destino','estacion'],sort=False):
            if len(g)!=2:continue
            t=g[g.alternativa.eq('terrestre_chile')].iloc[0];b=g[g.alternativa.eq('barcaza_actual')].iloc[0]
            design.append(dict(origen=t.origen,destino=t.destino,estacion=t.estacion,segmento=seg,ASC_barcaza=1,
                delta_COV_CLP=b.COV_privado_CLP_dic2025-t.COV_privado_CLP_dic2025,
                delta_t_viaje_h=b.t_viaje_modelo_h-t.t_viaje_modelo_h,
                delta_t_acceso_h=b.tiempo_acceso_h-t.tiempo_acceso_h,
                delta_t_horario_h=b.penalizacion_horario_central_h-t.penalizacion_horario_central_h,
                alcance='diagnostico_diseno_COV_sin_tarifas; no matriz final de estimacion'))
        dd=pd.DataFrame([x for x in design if x['segmento']==seg]);cols=['ASC_barcaza','delta_COV_CLP','delta_t_viaje_h','delta_t_acceso_h','delta_t_horario_h']
        x=dd[cols].to_numpy(float);scaled=x/np.maximum(np.linalg.norm(x,axis=0),1e-12)
        ranks.append(dict(segmento=seg,filas=len(dd),columnas=len(cols),rango_escalado=int(np.linalg.matrix_rank(scaled)),
            perfiles_diferenciales_unicos=len(dd[cols].drop_duplicates()),min_singular=float(np.linalg.svd(scaled,compute_uv=False)[-1]),
            conclusion='Rango sobre diseno COV parcial, no prueba identificacion con costo completo; precios/perfiles asumidos no agregan variacion observada'))
    save(design,'diagnostico_variacion_atributos');save(ranks,'diagnostico_rango_diseno')
    return counts,pd.DataFrame(ranks),excl


def report(a,stats,counts,ranks,cfg,checks):
    pair=a[a.origen.eq('Chile Chico')&a.destino.eq('Coyhaique')&a.estacion.eq('Verano')]
    cols=['segmento','alternativa','tiempo_conduccion_h','tiempo_bus_servicio_completo_h','tiempo_previo_zarpe_referencia_h','tiempo_desembarque_central_h','penalizacion_horario_central_h','tiempo_fisico_escenario_central_h','tiempo_con_horario_escenario_central_h','COV_privado_CLP_dic2025','tarifa_barcaza_principal_nominal_CLP','costo_monetario_escenario_central_CLP_dic2025','n_perfil']
    cols2=['origen','destino','estacion','segmento','alternativa','tiempo_fisico_escenario_central_h','tiempo_con_horario_escenario_central_h','costo_monetario_escenario_central_CLP_dic2025','n_perfil']
    reverse=a[a.origen.eq('Coyhaique')&a.destino.eq('Chile Chico')]
    stat=stats[stats.universo.eq('cruce_actual_19')]
    total=stat[stat.nivel.eq('total')].iloc[0]
    occ=pd.read_csv(OUT/'ocupantes_vehiculos.csv');occ0=occ[occ.universo.eq('VL_cruce_completo')&occ.nivel.eq('total')].iloc[0]
    factor=cfg['ipc'][cfg['mes_base_privado']]/cfg['ipc'][cfg['mes_referencia_tarifas_imputado']]
    ref=cfg['referencia_tarifa_Carolina_OC'];pc=homologar(ref['precio_CLP'],cfg['ipc'][ref['mes']],cfg['ipc'][cfg['mes_base_privado']])
    coverage=pd.read_csv(OUT/'cobertura_elecciones_por_OD.csv')
    coverage=coverage.loc[coverage.ambas_elecciones_muestrales]
    pv=pair.loc[pair.segmento.eq('VL')&pair.alternativa.eq('barcaza_actual')].iloc[0]
    pt=pair.loc[pair.segmento.eq('VL')&pair.alternativa.eq('terrestre_chile')].iloc[0]
    hs={st:a.loc[a.origen.eq('Chile Chico')&a.destino.eq('Coyhaique')&a.segmento.eq('VL')&a.estacion.eq(st)&a.alternativa.eq('barcaza_actual'),'penalizacion_horario_central_h'].iloc[0] for st in cfg['estaciones']}
    text=f'''# Atributos actualizados para preparar el logit exploratorio

## Alcance y resultado

Se conserva el paso09 y se deriva una matriz de {len(a)} filas: cuatro OD dirigidos × tres segmentos × cuatro estaciones × **dos alternativas: terrestre_chile y barcaza_actual**. Argentina queda fuera de atributos y elecciones de esta etapa. Las rutas desconocidas o fuera del alcance no se redistribuyen. No se recalculan OD, expansión temporal, SBO ni probabilidades.

Las rutas completas de09 se reutilizan entre anclajes públicos, con secuencia continua de nodos/arcos y sin duplicaciones. Puerto Ibáñez es el acceso a la rampa nodo1021, no la comuna Río Ibáñez. Los anclajes de Chile Chico1358 y Coyhaique1223 son puntos representativos de red, no domicilios ni centros urbanos validados. Los conectores convencionales de10km no se convierten en distancia física. La localización intrazonal individual permanece pendiente.

## Chile Chico → Coyhaique: comparación numérica

Km/h/CLP se indican en nombres. Costos COV son privados diciembre2025, **no CostGen**. La tarifa principal es nominal ARISTO; la columna de costo central está en CLP diciembre2025 bajo la convención de fecha explicada más abajo. El total temporal con horario es un índice en horas, no duración física del viaje. Los tiempos de conducción se mantienen estáticos por estación como en09.

{md(pair[cols])}

VL barcaza: {pv.distancia_terrestre_km:.3f}km terrestres, {pv.tiempo_conduccion_h:.3f}h conducción, {pv.tiempo_navegacion_h:.3f}h navegación, {pv.tiempo_previo_zarpe_referencia_h:.3f}h anticipación y {pv.tiempo_desembarque_central_h:.3f}h desembarque supuesto: **{pv.tiempo_fisico_escenario_central_h:.3f}h físicas entre anclajes**, más {pv.penalizacion_horario_central_h:.3f}h de desajuste en verano = **{pv.tiempo_con_horario_escenario_central_h:.3f}h de índice temporal**. Tierra VL: {pt.distancia_terrestre_km:.3f}km y {pt.tiempo_conduccion_h:.3f}h conducción. El índice con horario no es tiempo transcurrido observado.

Camiones usan velocidad y COV VP de ARISTO, una mezcla de camiones simples/articulados; no equivalen a un vehículo individual. Para verano Chile Chico→Puerto Ibáñez no existen CAM interceptados en ese sentido: no se imputa la media de19 como valor observado del estrato. La tarifa y costo central correspondientes pueden quedar NaN; el escenario agregado de19 está en la tabla de longitudes para contraste.

### Coyhaique → Chile Chico, cuatro estaciones

{md(reverse[cols2])}

La coincidencia de conducción/costos viales inversos proviene de las velocidades y costos bidireccionales de fuente, no de una igualdad observada. Los perfiles de ocupación y longitud son específicos de OD/estación/sentido si hay muestra; si se toma perfil del cruce completo del mismo sentido/estación se marca como transferencia. No se trasladan perfiles entre estaciones sin datos. Invierno sigue sin perfiles muestrales.

En el piloto VL verano, los {pv.n_perfil:.0f} registros de barcaza del OD Chile Chico→Coyhaique declaran una media de {pv.ocupantes_media_muestral:.6f} ocupantes. La suma `COV + (tarifa_vehiculo + tarifa_adulto × (ocupantes_media−1)) × factor_IPC` da **{pv.costo_monetario_escenario_central_CLP_dic2025:,.3f}CLP**. Conductor liberado, acompañantes adultos pagadores y cargos adicionales0 son condiciones de esta suma, no pagos observados. No se usa esa ocupación para recalcular la demanda de personas.

## Longitudes de carga verificadas

Los19 camiones/furgones válidos del cruce tienen19 longitudes numéricas positivas. Media **{total.longitud_media_m:.6f}m**, mediana **{total.longitud_mediana_m:.3f}m**, mínimo **{total.longitud_min_m:.3f}m**, máximo **{total.longitud_max_m:.3f}m**. La distribucion detallada por categoria se conserva solo en la salida local. {int(total.n_longitud_hasta5_5m)} declaraciones son≤5,5m: la categoría, no solo longitud, debe cotejarse con el cobro real. Se conservan valores y categorias discordantes como alertas locales; no se corrigen silenciosamente.

{md(stat[['nivel','estacion','sentido_cruce','Tipo de vehículo de carga','Número de ejes','registros_validos','n_longitud_numerica_positiva','longitud_media_m','longitud_mediana_m','longitud_min_m','longitud_max_m','tarifa_lineal_media_nominal_CLP']])}

`Tarifa=7310×L_declarada` da **{total.tarifa_lineal_media_nominal_CLP:,.2f}CLP** para la media y **{total.tarifa_lineal_mediana_nominal_CLP:,.2f}CLP** para la mediana de19. Son referencias condicionales para categorías sujetas a tarifa lineal, no tarifas facturadas observadas ni la flota poblacional. El PDF de condiciones2025 exige dimensiones exactas y puede cobrar diferencias; el extracto web actual especifica incluir accesorios. No se verificó unidad mínima de cobro, redondeo, largo con remolque/accesorios ni concordancia declarada/facturada. Se entrega aparte redondeo al metro superior como sensibilidad supuesta, no regla del operador. No se adopta16m.

Se conserva aparte el complemento de7 camiones interceptados en Cerro Castillo con extremo Chile Chico, sin agregarlo a los19 del cruce. CITRA, Informe2 corregido §6.1.2 pp86–87, publica431 encuestas de carga,53% de2ejes y47% de más de2,63% con carga y37% vacíos. No publica longitudes en ese apartado; no se combinan muestras ni se transfieren porcentajes a la barcaza.

## Ocupantes, personas y costos

En el cruce hay **{int(occ0.n_ocupantes_validos)} VL con ocupantes declarados**, media **{occ0.ocupantes_media:.6f} por vehículo**, mediana{occ0.ocupantes_mediana:.1f}, rango{occ0.ocupantes_min:.0f}–{occ0.ocupantes_max:.0f}. Incluye al conductor conforme a definición del campo; no se suma a peatones. Un registro declara12: se conserva y se informa sensibilidad con control configurable≤9 (media{occ0.ocupantes_media_sin_sobre_control:.6f}); este filtro es de calidad supuesto, no límite legal. Ni la edad del encuestado ni el total de ocupantes identifica quién es estudiante, mayor o tiene discapacidad. No se fabrican pagadores individuales.

ARISTOtabla52p121: vehículo≤5,5m21270CLP, adulto2550CLP, metro7310CLP, estudiantes en período escolar gratis y mayores/discapacidad gratis. La tarifa de vehículo no acredita por sí sola un pasaje de conductor incluido. El [extracto comercial de la web actual]({cfg['fuente_tarifario_actual']}) distingue conductor liberado en servicio subvencionado de conductor pagador en comercial, sin vigencia historica acreditada. El PDF Condiciones2025 no contiene esta regla: respalda anticipacion y dimensiones, no gratuidad del conductor. La OC1403-638-AG24 acredita servicio marítimo subvencionado, pero no cada ticket2025/26; el catastro SIG de09 decía sin subsidio. Por eso **conductor liberado es una condición del escenario central, no exención observada individualmente**. Se entrega sensibilidad conductor pagador. Acompañantes adultos pagadores es otro supuesto; también se entrega el caso de acompañantes exentos. En tierra no hay tarifa de barco, pero otros cargos/intrazonales no verificados permanecen faltantes.

La [página del operador]({cfg['fuente_tarifario_actual']}) publica impuestos incluidos y advierte tasas no incluidas, sin monto verificado; **no se agrega IVA nuevamente** ni se declara tasa real0. El escenario central fija cargos adicionales0 solamente para sumar componentes, marcado como supuesto. El costo monetario total confirmado permaneceNaN si falta algún pago o condición; la suma central condicional se entrega en columna separada y no es desembolso observado.

### Homologación monetaria

Base común: diciembre2025. `C_base=C_nominal×IPC_base/IPC_origen`. IPC oficial difundido por SII: agosto2024=104,45; diciembre2025=109,26; enero2026=109,71 (base2023=100). Fuentes: {', '.join(cfg['fuentes_ipc'])}. La tabla52 no identifica mes exacto: **enero2026 es convención exploratoria**, factor{factor:.9f}. Se conservan tarifas nominales y fecha pendiente; la homologación no queda certificada. El COV de diciembre2025 no cambia; no se añade tiempo valorizado. Para una fecha distinta basta cambiar configuración, no código.

## Pasajeros a pie y servicios de referencia

ARISTOtabla61pp127–128 y nota(b) publican **Carolina6h Coyhaique–Puerto Ibáñez–Chile Chico**, **Interlagos8h Coyhaique–Cerro Castillo–Río Tranquilo–Puerto Guadal–Chile Chico** y **Freddy5h Aeropuerto Balmaceda–Puerto Ibáñez–Chile Chico**. Las6/8h se usan como tiempos completos publicados del servicio en ambos sentidos, al no existir tiempos separados por sentido; no son tiempos individuales medidos. Freddy es antecedente, no sustituto del OD Coyhaique.

Las6h contienen un itinerario bimodal pero su desglose interno (navegación, presentación, transbordo, desembarque) no se publica. **No se les vuelve a sumar2h navegación,1h anticipación ni0,5h desembarque**. Se conservan referencias de operación en columnas aparte y los adicionales al servicio se fijan0 por inclusión asumida, no por maniobras inexistentes. El acceso fuera del servicio está pendiente. En el perfil genérico sin bus, el tiempo completo sigueNaN si falta acceso/egreso. Los pasajeros del OD Puerto Ibáñez no heredan las6h de Coyhaique.

Las referencias de6/8h son perfiles condicionales de servicio público, **no asignaciones de todos los peatones a esos operadores**. De99 peatones válidos interceptados, los modos primarios observados son:

{md(pd.read_csv(OUT/'resumen_modos_peatones.csv')[['campo','modo','encuestas']])}

Las secuencias de modos1/2/3 por OD/estación se conservan agregadas. Bus no prueba Carolina ni coordinación. Caminata inicial no descarta otro modo posterior. Se conservan separados otros6 pasajeros tipificados como bus/van/transfer/turismo; no se multiplican entrevistas por tamaño de grupo ni se suman con viajeros dentro de vehículos.

No se encontró tarifa pública histórica verificable de Carolina/Interlagos/Freddy en las tablas y textos locales revisados. Una [orden institucional de2024]({ref['fuente']}) registra11100CLP/unidad para suministro terrestre y marítimo: homologado deagosto2024 a diciembre2025 equivale a **{pc:,.2f}CLP**. Se entrega como referencia de sensibilidad contractual, no tarifa pública vigente ni prueba de integración por ticket. Si se interpreta paquete, no sumar otra tarifa de barcaza. No se transfieren los10000CLP de Puerto Cisnes. Interlagos/Freddy mantienen tarifa faltante; no se inventa precio para completar columnas.

## Anticipación, desembarque y horario

Condiciones2025art12: presentación1h peatones y2h rodados. Es exigencia, no medición física de embarque ni coeficiente de desutilidad. Se considera que contiene las operaciones previas; no se agrega otro embarque. Desembarque vehicular15/30/45min proviene del supuesto solicitado por usuario: no se ha entregado una referencia operacional específica que permita validarlo como transferencia empírica. Para peatones no se encontró medición propia; se conserva el mismo rango solo como sensibilidad exploratoria del perfil genérico. No se suma sobre las6h de bus completo.

Central: `t_horario=0.25×168/f`, con11salidas diciembre–abril y8mayo–noviembre por sentido. Verano {hs['Verano']:.6f}h; invierno {hs['Invierno']:.6f}h y primavera {hs['Primavera']:.6f}h. Otoño distingue los regímenes de marzo/abril y mayo; promedio ponderado por días del año configurado **{hs['Otoño']:.6f}h**. Se guarda detalle mensual. No es espera en muelle. Los H ponderados de calendario de09 quedan en sensibilidad, con su vigencia/discrepancia alta12frente11, sin reinterpretarlos como caso central. Para tierra vehicular0. En buses la frecuencia propia y coordinación siguen pendientes: **no sumar automáticamente penalización de barcaza ni suponer que las8h contienen desajuste con salida deseada**. La columna de horario total central del bus quedaNaN; tiempo físico publicado6/8h disponible.

## Compatibilidad EVALSO y diagnóstico previo a calibración

Versión local de Informe2: §3.2eq3.2, §3.3eq3.3 y §3.3.1eq3.8 (la sección de demanda no es el capítulo5 en este PDF). Se conserva:

`CG_privado=C_privado+VST_privado×(t_acceso+t_viaje+t_previo+t_desembarque+t_horario)`.

Para vehículos barcaza, t_acceso=conducción terrestre completa y t_viaje=navegación. Para tierra t_acceso0 y t_viaje=conducción. No sumar además conducción descriptiva. Para servicio de bus completo no se usa la suma de componentes internos desconocidos: se utiliza el total publicado, con acceso fuera del servicio y desfase propios pendientes. Las variables valorizadas permanecenNaN: no existe un VST privado numérico justificado por segmento y no se adopta VST social ni10000 de CostGen ARISTO.

La utilidadeq3.3 tiene coeficientes de costo, viaje, horario y acceso, pero omite explícitamente embarque. **Decisión metodológica a validar antes de calibrar**: agrupar previo/desembarque con viaje bajo el mismo beta_t; no crear un beta nuevo. Para buses usar el tiempo completo una sola vez. Una alternativa equivalente bajo restricción común es tiempo total físico, pero cambia la separación acceso/viaje declarada; no se impone silenciosamente. No incluir simultáneamenteCG y sus componentes colineales.

La falta de un VST privado externo impide calcular un CG valorizado justificado, **pero no impide por sí misma estimar coeficientes de tiempo y dinero por separado**. Si estos se identifican posteriormente, su cociente puede informar una valoración implícita; todavía no se calcula.

La unidad de costo es viaje de vehículo (incluidos pagos de sus ocupantes en el escenario) para VL/CAM y viaje de persona para peatones. No sumar estas unidades. Antes de transferir un VST por persona al modelo de vehículo hay que definir quién toma/paga la decisión y cómo se agregan los tiempos de los ocupantes; no multiplicar automáticamente por ocupación media.

### Elecciones identificadas, sin cuotas poblacionales

{md(counts)}

Solo se cuentan observaciones cuya clasificación confirmada de07 pertenece a las dos alternativas, en los cuatro OD puntuales. Registros comunales Río Ibáñez no resueltos como Puerto Ibáñez quedan sin emparejamiento con ese OD. No se usan observaciones de Argentina, país no demostrado o ruta desconocida. No se deduce tierra de carretera ni del solo no uso de barcaza.

Los siguientes estratos tienen entrevistas de ambas elecciones. Los restantes se conservan en `cobertura_elecciones_por_OD.csv`; cero entrevistas no significa cero viajes:

{md(coverage[['origen','destino','segmento','estacion','n_terrestre_chile','n_barcaza_actual']])}

VL/CAM tienen atributos viales reconstruidos en ambas alternativas. La parte temporal vehicular está cuantificada bajo escenarios operacionales; dinero completo requiere perfiles/pagos. Peatones disponen de servicios publicados para Coyhaique, pero faltan modo/operador individual, tarifas y acceso externo. No existe un segmento con todos los atributos completos observados por individuo. Los agregados permiten explorar diferencias de oferta, no iniciar aún una calibración individual validada.

### Variación e identificabilidad

{md(ranks)}

El diagnóstico usa diferencias barco−tierra de ASC, COV, viaje, acceso y horario, escaladas antes de calcular rango. Es COV parcial, **no costo total final**. Los cuatro OD dirigidos contienen solo dos pares geográficos y varios atributos inversos coinciden. Repetir estaciones no crea variación vial nueva; H cambia solo por régimen. La anticipación y desembarque constantes por alternativa se confunden con ASC si se intenta estimar su efecto separadamente. La variación de ocupantes/longitud ayuda a construir escenarios monetarios, pero promedios imputados no equivalen a covariables individuales exógenas. Repetir pesos de sensibilidades no aumenta muestra efectiva. H=168/f central no cambia por sentido; calendario sí podría hacerlo bajo otra sensibilidad.

La EOD intercepta carretera y barcaza en marcos distintos. Los recuentos simples no son cuotas de elección; eq3.8 requiere ponderadores/diseño justificables. Expansión carretera10h y escenarios24h no son probabilidades de inclusión certificadas, ni comparables automáticamente con medias por zarpe. Falta vinculación individual a ambas ofertas y corrección de muestreo dependiente de alternativa. Con una sola barcaza histórica no se identifica lambda del nido lacustre ni ASC del futuro cruce. No se ejecutó Biogeme ni estimación.

## Archivos, reproducción y control

Reproducir con `python scripts/10_completar_atributos_logit.py`. Parámetros, transcripciones verificadas y sus fuentes: `data/templates/config_logit_actualizado.json`. Los7productos solicitados están en esta carpeta; además se entregan perfiles agregados de ocupación, detalle de modos, elecciones identificadas, diseño/rango, fuentes y verificación de integridad. No se exportan identificadores individuales. Las salidas quedan excluidas deGit, incluidas celdas pequeñas; revisar antes de compartir.

Las fuentes originales se leen fuera del repositorio. Se verifican por hash los caches de EOD; se conservan por hash todos los archivos anteriores de matrices, sensibilidades temporales y atributos09. Verificaciones: `{json.dumps(checks,ensure_ascii=False)}`. No se modifica ni ejecuta ningún generador anterior; sin commit/push.
'''
    (OUT/'resumen_atributos_actualizados.md').write_text(text,encoding='utf-8')


def main():
    cfg=json.loads((ROOT/'data/templates/config_logit_actualizado.json').read_text())
    OUT.mkdir(parents=True,exist_ok=True)
    protected=[p for folder in ['matrices_od_referencia','expansion_temporal_terrestre','atributos_alternativas'] for p in (ROOT/'outputs'/folder).glob('*') if p.is_file()]
    before={p:sha(p) for p in protected}
    d,digest=datos(cfg)
    original=pd.read_csv(ROOT/cfg['fuente_rutas']/'atributos_alternativas.csv')
    a=original.loc[original.alternativa.isin(cfg['alternativas']) & original.segmento.isin(cfg['segmentos'])].copy()
    stats=estadisticas(d,cfg);modos_peatones(d,cfg);attrs=construir(a,d,cfg)
    counts,ranks,excluded=diagnostico(attrs,d,cfg)
    routes=pd.read_csv(ROOT/cfg['fuente_rutas']/'rutas_od.csv');routes=routes[routes.ruta_id.isin(attrs.ruta_id)]
    for rid,g in routes.groupby('ruta_id',sort=False):
        rr=attrs[attrs.ruta_id.eq(rid)].iloc[0]
        edges=[dict(desde=int(x.nodo_desde),hasta=int(x.nodo_hasta),ID_Arco=x.ID_Arco) for x in g.itertuples()]
        comprobar_secuencia(edges,int(str(rr.secuencia_nodos).split(';')[0]),int(str(rr.secuencia_nodos).split(';')[-1]))
    save(routes,'rutas_reutilizadas_dos_alternativas')
    monthly=pd.read_csv(ROOT/cfg['fuente_rutas']/'horario_mensual.csv')
    save(monthly[['estacion','mes','dias','sentido_cruce','f_ordinario','H_168_f_h','t_horario_168_f_h','estado']],'horario_mensual_central')
    save([dict(archivo=str(p.relative_to(ROOT)),sha256_antes=h,sha256_despues=sha(p),intacto=h==sha(p)) for p,h in before.items()],'integridad_anteriores')
    checks=dict(solo_dos_alternativas=set(attrs.alternativa)==set(cfg['alternativas']),claves_unicas=not attrs.duplicated(KEY).any(),
        cuatro_estaciones=set(attrs.estacion)==set(cfg['estaciones']),rutas_continuas=True,
        no_COV_peaton=bool(attrs.loc[attrs.segmento.eq('PEATON'),'COV_privado_CLP_dic2025'].isna().all()),
        no_VST_inventado=bool(attrs.costo_generalizado_privado_CLP.isna().all()),
        no_total_confirmado_con_faltantes=bool(attrs.costo_monetario_privado_total_confirmado_CLP.isna().all()),
        camion_19_longitudes=bool(stats.loc[stats.universo.eq('cruce_actual_19')&stats.nivel.eq('total'),'n_longitud_numerica_positiva'].iloc[0]==19),
        horarios_terrestres_barcaza_cero=bool(attrs.loc[attrs.alternativa.eq('terrestre_chile'),'penalizacion_horario_central_h'].eq(0).all()),
        historicos_intactos=all(sha(p)==h for p,h in before.items()))
    (OUT/'validacion.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2))
    (OUT/'config_utilizada.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2))
    source=[dict(fuente='EOD original',archivo='Cap6/BBDD EOD/Base de datos agregada.xlsx',sha256=digest,hojas='BBDD-1; BBDD-2 (solo validas)',variables='ocupantes,longitud,categoria,ejes,modos,edad,ruta,OD; caches hash controlado'),
        dict(fuente='EVALSO',archivo='INFORME_2_EVALSO-1.pdf',hojas='secciones3.2-3.3 eq3.2,3.3,3.8',variables='CG privado; utilidad; ponderadores'),
        dict(fuente='ARISTO',archivo='Informe ARISTO.pdf',hojas='tabla52 p121; tabla61 pp127-128',variables='tarifas; servicios y tiempos completos'),
        dict(fuente='CITRA',archivo='Estudios de consultoras/Informe 2c - MOP aysen vf.pdf',hojas='6.1.2 pp86-87',variables='contraste431camiones;ejes53/47%;sin longitudes'),
        dict(fuente='Condiciones2025',archivo=cfg['fuente_condiciones'],hojas='art12 y15',variables='anticipacion; dimensiones exactas. No establece conductor liberado'),
        dict(fuente='Operador actual',archivo=cfg['fuente_tarifario_actual'],hojas='tarifas y condiciones',variables='exenciones,conductor liberado condicionado a subsidio,tasas,IVA,adulto2510 discrepante de2550')]
    source += [dict(fuente='IPC oficial difundido SII',archivo=url,hojas='indice base2023',variables='homologacion') for url in cfg['fuentes_ipc']]
    source += [dict(fuente='Precio institucional NO tarifa publica',archivo=cfg['referencia_tarifa_Carolina_OC']['fuente'],hojas='OC1403-638-AG24 seccion6',variables='11100CLP/unidad; agosto2024; solo sensibilidad')]
    for x in source:x['consulta']='2026-10-25'
    save(source,'fuentes_actualizacion')
    report(attrs,stats,counts,ranks,cfg,checks)
    assert all(checks.values()),checks
    print(json.dumps(dict(filas_atributos=len(attrs),rutas=routes.ruta_id.nunique(),controles=checks,observaciones_eleccion=int(counts.encuestas_eleccion_identificada.sum())),ensure_ascii=False))


if __name__=='__main__':main()
