"""Etapa12: aplicación incremental de11B. No estima parámetros ni matrices.

python scripts/14_aplicar_etapa12.py
Todas las salidas detalladas son locales. Pruebas del núcleo solo sintéticas.
"""
from pathlib import Path
import calendar
import hashlib
import json
import math
import subprocess
import sys
import platform

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from demanda.atributos import grafo_vial, camino_minimo
from demanda.proyecto import logit_anidado, desviar

K = ['origen', 'destino', 'estacion', 'segmento']
ALTS = ['terrestre_chile', 'barcaza_actual', 'bahia_jara_levican']
NAN = float('nan')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(name):
    return pd.read_csv(ROOT / 'outputs' / (name + '.csv'))


def select(d, keys):
    mask = np.ones(len(d), dtype=bool)
    for key, val in keys.items():
        mask &= d[key].eq(val)
    return d.loc[mask]


def scalar(d, column):
    if len(d) > 1:
        raise ValueError('Celda no única')
    return float(d.iloc[0][column]) if len(d) else NAN


def horario(station, cfg, historical=False):
    months = {'Verano': [12, 1, 2], 'Otoño': [3, 4, 5],
              'Invierno': [6, 7, 8], 'Primavera': [9, 10, 11]}[station]
    days = [calendar.monthrange(2026, m)[1] for m in months]
    high = 11 if historical else cfg['sbo_f_alta']
    low = 8 if historical else cfg['sbo_f_baja']
    f = [high if m in [12, 1, 2, 3, 4] else low for m in months]
    return float(np.average([cfg['w'] * 168 / x for x in f], weights=days))


def escenarios(cfg):
    yield 'central', cfg
    for name, change in cfg['sensibilidades'].items():
        yield name, dict(cfg, **change)


def red_proyecto(cfg):
    """Red existente + segmentos virtuales de proyecto con extremos explícitos.

    No simula geometría desconocida. Se fracciona el R265 en la abscisa EVALSO;
    el enlace intralocal norte está condicionado a anclaje1021 (ver informe).
    """
    source = ROOT.parent / 'Cap 7/HDM4/Costos_Red_Vial_Actual.xlsx'
    frame = pd.read_excel(source, sheet_name='Costos_Red_Vial')
    types = pd.read_excel(source, sheet_name='Tipos de arcos').set_index('Clave')
    assert not frame.RUTA.astype(str).str.contains(r'X-735|X-763').any()
    metrics = {}; evidence = []
    for seg in ['VL', 'CAM']:
        g = grafo_vial(frame, seg, 'Chile', [(1359, 1323), (1311, 1609), (1503, 1502)])
        speed = 'VEL VP' if seg == 'CAM' else 'VEL VL'
        cost = 'CO VP' if seg == 'CAM' else 'CO VL'
        northern = camino_minimo(g, 1021, 1223)
        south_route = camino_minimo(g, 1358, 1351)
        left = cfg['sur_R265_km']; south = []
        for e in south_route:
            used = min(left, e['LONGITUD'])
            if used <= 0:
                break
            south.append(dict(id=str(e['ID_Arco']), desde=str(e['desde']), hasta=str(e['hasta']) if used == e['LONGITUD'] else 'EMP_X763_REFERENCIAL',
                              km=used, h=used/e[speed], cov=used/e['LONGITUD']*e[cost],
                              fraccion=used/e['LONGITUD'], tipo=e['Clave']))
            left -= used
        assert abs(left) < 1e-9
        for destination in ['Coyhaique', 'Puerto Ibáñez']:
            north = northern if destination == 'Coyhaique' else []
            for scenario, c in escenarios(cfg):
                minor = []
                for road, length in [('X763', c['sur_X763_km']), ('X735', c['longitud_norte_km'])]:
                    tipo = c['tipo_HDM4_' + road]
                    minor.append(dict(id=road+'_'+c['variante'], desde='EMP_X763_REFERENCIAL' if road == 'X763' else 'LEVICAN_TERMINAL_PROYECTO',
                                      hasta='BAHIA_JARA_TERMINAL_PROYECTO' if road == 'X763' else '1021',
                                      km=length, h=length/c['velocidad_'+road+'_kmh'][seg],
                                      cov=length*float(types.loc[tipo, cost])*c.get('cov_factor', 1),
                                      tipo=tipo, fraccion=1))
                trunk = [dict(id=str(e['ID_Arco']), desde=str(e['desde']), hasta=str(e['hasta']), km=e['LONGITUD'],
                              h=e['LONGITUD']/e[speed], cov=e[cost], tipo=e['Clave'], fraccion=1) for e in north]
                edges = south + [minor[0], dict(id='LAGO_PROYECTO', desde='BAHIA_JARA_TERMINAL_PROYECTO',
                    hasta='LEVICAN_TERMINAL_PROYECTO', km=0, h=0, cov=0, tipo='nav_separada', fraccion=1), minor[1]] + trunk
                assert all(a['hasta'] == b['desde'] for a,b in zip(edges[:-1],edges[1:])), 'Secuencia de proyecto discontinua'
                metrics[scenario, seg, destination] = dict(
                    distancia_terrestre_km=sum(e['km'] for e in edges),
                    tiempo_conduccion_h=sum(e['h'] for e in edges),
                    COV=sum(e['cov'] for e in edges), norte_red_km=sum(e['km'] for e in trunk),
                    norte_red_h=sum(e['h'] for e in trunk),
                    sur_principal_h=sum(e['h'] for e in south),
                    secuencia_arcos=';'.join(e['id'] for e in edges),
                    secuencia_nodos=';'.join([edges[0]['desde']]+[e['hasta'] for e in edges]),
                    ruta_completa=f'Chile Chico → R265-CH ({c["sur_R265_km"]}km) → X-763 ({c["sur_X763_km"]}km) → Bahía Jara → lago → Levicán → X-735 {c["variante"]} ({c["longitud_norte_km"]}km) → Puerto Ibáñez' + (' → X-65/R7/R243-CH → Coyhaique' if destination == 'Coyhaique' else ''),
                    diferencia_referencia_162_84_km=sum(e['km'] for e in edges)-162.84 if destination == 'Coyhaique' else NAN)
                if scenario == 'central':
                    for order, e in enumerate(edges):
                        evidence.append(dict(segmento=seg, destino_norte=destination, orden_sur_norte=order, **e,
                            estado='proyecto_virtual_no_geometria_SIG' if e['id'].startswith(('X7','LAGO')) else 'arco_existente_fraccionado_segun_referencia_EVALSO' if e['fraccion'] < 1 else 'arco_existente_ARISTO'))
    return metrics, pd.DataFrame(evidence)


def perfil_medio(pair, old):
    """Mismas reglas de11; valores faltantes de perfil conservan su imputación."""
    t = pair.loc[pair.alternativa.eq(ALTS[0])].iloc[0]
    b = pair.loc[pair.alternativa.eq(ALTS[1])].iloc[0]
    seg = t.segmento; factor = old['factor_IPC_tarifa']
    if seg == 'PEATON':
        if {t.origen, t.destino} != {'Chile Chico', 'Coyhaique'}:
            return np.full((1, 2, 4), NAN)
        tv = old['navegacion_h'] + old['anticipacion_peatones_h'] + old['desembarque_central_h']
        return np.array([[[old['tarifa_bus_terrestre_supuesta']*factor, old['bus_terrestre_servicio_h'], 0, 0],
                         [(old['tarifas_equipo']['Carolina_Coyhaique_Puerto_Ibanez']+old['tarifa_barcaza_adulto'])*factor,
                          tv, b.t_horario_barcaza_potencial_h, old['bus_barcaza_servicio_h']-tv]]])
    occ = b.ocupantes_media_muestral
    if not np.isfinite(occ):
        occ = old['ocupacion_VL_fallback'] if seg == 'VL' else 1
    length = b.longitud_CAM_media_muestral_m
    if not np.isfinite(length):
        length = old['longitud_CAM_fallback_m']
    fare = old['tarifa_VL'] if seg == 'VL' else old['tarifa_metro_CAM']*length
    fare = (fare + max(occ-1, 0)*old['tarifa_barcaza_adulto'])*factor
    return np.array([[[t.COV_privado_CLP_dic2025, t.tiempo_conduccion_h, 0, 0],
                     [b.COV_privado_CLP_dic2025+fare, 4.5, b.t_horario_barcaza_potencial_h, b.tiempo_acceso_h]]])


def perfiles(pair, bases, keys, old):
    subset = select(bases[keys['segmento']], keys)
    if len(subset):
        x = np.array([[[r.c1*10000, r.t1, r.e1, r.a1], [r.c2*10000, r.t2, r.e2, r.a2]] for r in subset.itertuples()])
        weights = subset.weight.to_numpy(float)
        return x, weights/weights.sum(), 'integracion_soporte_11B_pesos_reutilizados'
    return perfil_medio(pair, old), np.ones(1), 'perfil_medio_11B_extrapolado'


def mercado(keys, b, t, temporal):
    """Mercados separados; ausencia de una ruta jamás se completa con cero."""
    seg = keys['segmento']
    qm = scalar(select(b, keys), 'demanda_diaria_24h_equivalente')
    qt10 = scalar(select(t, keys), 'demanda_expandida_viajes_diarios_promedio')
    z = select(temporal, dict(keys, caso='CC_PC1_laboral'))
    qt24 = scalar(z, 'demanda_estimada_24h')
    if seg == 'VL':
        return [dict(escenario_mercado='VL24h_exploratorio', demanda_total_OD=qm+qt24,
                     flujo_barcaza_referencia=qm, flujo_tierra_referencia=qt24,
                     unidad='vehiculos/dia_equivalente_condicional', estado='expansion_y_sensibilidad24h_NO_observado24h')]
    if seg == 'CAM':
        factor = scalar(z, 'factor_temporal_aplicado')
        if not np.isfinite(factor):
            z = select(temporal, dict(keys, segmento='VL', caso='CC_PC1_laboral'))
            factor = scalar(z, 'factor_temporal_aplicado')
        return [dict(escenario_mercado='CAM24h_imputado_factor_VL', demanda_total_OD=qm+qt10*factor,
                     flujo_barcaza_referencia=qm, flujo_tierra_referencia=qt10*factor,
                     unidad='camiones/dia_equivalente_IMPUTADO', estado='factor_temporal_VL_transferido_a_CAM_NO_validado'),
                dict(escenario_mercado='CAM_contraste10h_diario', demanda_total_OD=qm+qt10,
                     flujo_barcaza_referencia=qm, flujo_tierra_referencia=qt10,
                     unidad='indice_mixto_CAM_NO_flujo_diario', estado='contraste11B_no_homologado_NO_demanda_diaria')]
    # Imputación solicitada como escenario separado: cuota VL del mismo OD/estación.
    vlkeys = dict(keys, segmento='VL')
    qmv = scalar(select(b, vlkeys), 'demanda_diaria_24h_equivalente')
    qtv = scalar(select(temporal, dict(vlkeys, caso='CC_PC1_laboral')), 'demanda_estimada_24h')
    cuota = qmv/(qmv+qtv) if np.isfinite(qmv+qtv) and qmv > 0 else NAN
    total = qm/cuota if np.isfinite(cuota) and cuota > 0 else NAN
    return [dict(escenario_mercado='PEATON_imputado_cuota_VL', demanda_total_OD=total,
                 flujo_barcaza_referencia=qm, flujo_tierra_referencia=total-qm,
                 unidad='personas/dia_equivalente_IMPUTADO', estado='ferry_personas_dividido_por_cuota_VL_NO_mercado_personal_observado')]


def simular(cfg, attrs, bases, params, old, routes, markets):
    probs_s = []; probs_p = []; attributes_s = []; attributes_n = []; logs = []; diverted = []; sensitivity = []
    checks_old = []
    for keytuple, pair in attrs.groupby(K, sort=False):
        keys = dict(zip(K, keytuple)); seg = keys['segmento']; other = keys['destino'] if keys['origen'] == 'Chile Chico' else keys['origen']
        xold, weights, profile = perfiles(pair, bases, keys, old)
        pp = params[seg]; slopes = np.array([pp['beta_c'], pp['beta_t'], pp['beta_e'], pp['beta_a']])
        b = pair.loc[pair.alternativa.eq(ALTS[1])].iloc[0]
        for name, c in escenarios(cfg):
            r = routes[name, 'VL' if seg == 'PEATON' else seg, other]
            xs = xold.copy(); xs[:, 1, 2] = horario(keys['estacion'], c)
            n = np.empty((len(xs), 4))
            fare = xs[:, 1, 0]-b.COV_privado_CLP_dic2025 if seg != 'PEATON' else None
            busnom = NAN; busrefkm = routes[name, 'VL', 'Coyhaique']['norte_red_km']
            if seg == 'PEATON':
                busnom = c['bus_tarifa_referencia_nominal']*r['distancia_terrestre_km']/busrefkm*c['bus_factor']
                boatnom = 0 if c['bus_integrado'] else old['tarifa_barcaza_adulto']*c['tarifa_factor']
                n[:, 0] = (busnom+boatnom)*old['factor_IPC_tarifa']
                # Perfil de buses: troncal conserva residual de6h de11B, escalado
                # por red. Secundarios a40km/h supuesto, R265 a50km/h supuesto.
                fullroad = float(b.distancia_terrestre_km)
                residual = old['bus_barcaza_servicio_h']-(old['navegacion_h']+old['anticipacion_peatones_h']+old['desembarque_central_h'])
                n[:, 3] = (residual*r['norte_red_km']/fullroad if other == 'Coyhaique' else 0) + c['sur_R265_km']/50 + c['sur_X763_km']/c['velocidad_X763_kmh']['PEATON'] + c['longitud_norte_km']/c['velocidad_X735_kmh']['PEATON']
            else:
                n[:, 0] = r['COV']+fare*c['tarifa_factor']
                n[:, 3] = r['tiempo_conduccion_h']
            n[:, 1] = c['navegacion_h']+c['anticipacion_h'][seg]+c['desembarque_h']
            n[:, 2] = c['w']*168/c['nuevo_f_semana_sentido']
            xp = np.concatenate([xs, n[:, None, :]], axis=1)
            vs = xs @ slopes + [0, pp['ASC_barcaza']]
            vp = xp @ slopes + [0, pp['ASC_barcaza'], pp['ASC_barcaza']+c['delta_ASC_nuevo']]
            ps_l = []; psum = []; pr_l = []; prsum = []
            for vs_i, vp_i in zip(vs, vp):
                p, ls = logit_anidado(vs_i, c['lambda_lago']); ps_l.append(p); psum.append(ls)
                p, lp = logit_anidado(vp_i, c['lambda_lago']); pr_l.append(p); prsum.append(lp)
            ps = np.average(ps_l, axis=0, weights=weights); pr = np.average(pr_l, axis=0, weights=weights)
            ls = float(np.average(psum, weights=weights)); lp = float(np.average(prsum, weights=weights))
            probabilities_known = np.isfinite(ps).all() and np.isfinite(pr).all()
            status = 'disponibilidad_condicionada_a_operacion_y_conexion_intralocal' if probabilities_known else 'atributos_o_disponibilidad_no_identificados_NO_se_excluye_alternativa'
            if name == 'central':
                oldp = [logit_anidado(v, pp['lambda_lago'])[0][1] for v in xold@slopes+[0, pp['ASC_barcaza']]]
                checks_old.append(dict(**keys, probabilidad_barcaza11B_reproducida=np.average(oldp, weights=weights)))
                for j, alt in enumerate(ALTS):
                    common = dict(**keys, alternativa=alt, perfil=profile, estado_disponibilidad=status,
                                  unidad_probabilidad='adimensional', lambda_lago=c['lambda_lago'], escala_superior=1,
                                  ASC=0 if j == 0 else pp['ASC_barcaza'], beta_c=pp['beta_c'], beta_t=pp['beta_t'], beta_a=pp['beta_a'], beta_e=pp['beta_e'])
                    if j < 2:
                        probs_s.append(dict(common, probabilidad=ps[j]))
                    probs_p.append(dict(common, probabilidad=pr[j]))
                    avg = np.average(xp[:, j], axis=0, weights=weights)
                    row = dict(common, C_privado_CLP_dic2025=avg[0], t_viaje_h=avg[1], t_horario_h=avg[2], t_acceso_h=avg[3],
                               metodo_probabilidad='promedio_ponderado_probabilidades_individuales; NO_logit_de_atributos_medios',
                               perfil_imputado=profile, fuente='atributos10/base11B' if j < 2 else 'CITRA2/CITRA3/EVALSO/red_HDM4_ARISTO+supuestos12',
                               base_precios='CLP_dic2025; factor_tarifas109.26/109.71_heredado11B',
                               faltantes='acceso_intrazonal;terminal_y_empalme_exacto;estiba_y_restricciones;peajes_tasas_no_verificados')
                    if j < 2:
                        oldrow = pair.loc[pair.alternativa.eq(alt)].iloc[0]
                        attributes_s.append(dict(row, distancia_terrestre_km=oldrow.distancia_terrestre_km,
                            tiempo_conduccion_h=oldrow.tiempo_conduccion_h, COV=oldrow.COV_privado_CLP_dic2025,
                            navegacion_h=oldrow.tiempo_navegacion_h, secuencia_arcos=oldrow.secuencia_arcos,
                            f_alta=0 if j == 0 else c['sbo_f_alta'], f_baja=0 if j == 0 else c['sbo_f_baja'],
                            t_horario_historico_h=0 if j == 0 else horario(keys['estacion'], c, True),
                            anticipacion_h=0 if j == 0 else old['anticipacion_peatones_h'] if seg == 'PEATON' else old['anticipacion_vehiculos_h'],
                            desembarque_h=0 if j == 0 else old['desembarque_central_h']))
                    else:
                        rev = keys['origen'] != 'Chile Chico'
                        attrsroute = dict(r)
                        if rev:
                            attrsroute['secuencia_arcos'] = ';'.join(reversed(r['secuencia_arcos'].split(';')))
                            attrsroute['secuencia_nodos'] = ';'.join(reversed(r['secuencia_nodos'].split(';')))
                            attrsroute['ruta_completa'] = ' → '.join(reversed(r['ruta_completa'].split(' → ')))
                        if seg == 'PEATON':
                            # La operación del vehículo no es un desembolso personal.
                            attrsroute['COV'] = NAN
                            attrsroute['tiempo_conduccion_h'] = NAN
                            attrsroute['norte_red_h'] = NAN
                        attributes_n.append(dict(row, **attrsroute, variante=c['variante'],
                            tiempo_conduccion_perfil_h=avg[3], navegacion_h=c['navegacion_h'],
                            anticipacion_h=c['anticipacion_h'][seg], desembarque_h=c['desembarque_h'],
                            tiempo_fisico_h=avg[1]+avg[3], frecuencia_sentido_semana=c['nuevo_f_semana_sentido'],
                            tarifa_bus_nominal=busnom, distancia_bus_referencia_km=busrefkm,
                            tarifa_lacustre_nominal_media=(avg[0]-r['COV'])/old['factor_IPC_tarifa'] if seg != 'PEATON' else old['tarifa_barcaza_adulto'],
                            perfil_usuario='adulto_general_buses_acercamiento_y_barco_separados_NO_todos_los_peatones' if seg == 'PEATON' else 'mismos_pagadores_y_longitud_condicionales11B',
                            estado_geometria='tramos_virtuales_con_longitudes_documentales; conexiones_intralocales_aproximadas_NO_SIG_certificado'))
                logs.append(dict(**keys, logsum_SBO=ls, logsum_proyecto=lp, diferencia_logsum=lp-ls,
                    equivalente_CG_SBO_CLP=-ls/abs(pp['beta_c']), equivalente_CG_proyecto_CLP=-lp/abs(pp['beta_c']),
                    ganancia_equivalente_CLP=(lp-ls)/abs(pp['beta_c']),
                    unidad_logsum='utilidad_normalizada_adimensional', unidad_CG='CLP_dic2025_por_unidad_decision',
                    perfil=profile, agregacion='media_ponderada_logsum_por_perfil; NO_logsum_de_utilidad_media',
                    beta_c=pp['beta_c'], beta_t=pp['beta_t'], beta_e=pp['beta_e'], beta_a=pp['beta_a'],
                    ASC_actual=pp['ASC_barcaza'], ASC_nuevo=pp['ASC_barcaza'], ASC_tierra=0,
                    lambda_lago=c['lambda_lago'], mu_lago_Biogeme=1/c['lambda_lago'], escala_superior=1,
                    elasticidad_futura=cfg['elasticidades_siguiente_etapa_NO_aplicadas'][seg][0],
                    advertencia='CG=-logsum/abs(beta_c) incluye ASC y entropia; origen arbitrario, puede ser negativo; NO usar cociente sin justificar referencia; induccion_NO_aplicada'))
            for market in markets[keytuple]:
                total = market['demanda_total_OD']; losses = desviar(total, ps, pr) if probabilities_known else [NAN, NAN]
                if name == 'central':
                    for j, alt in enumerate(ALTS):
                        ds = total*ps[j] if j < 2 else 0 if np.isfinite(total) else NAN
                        dp = total*pr[j]
                        diverted.append(dict(**keys, **market, alternativa=alt, P_SBO=ps[j] if j < 2 else 0 if probabilities_known else NAN,
                            P_proyecto=pr[j], demanda_SBO=ds, demanda_proyecto=dp, diferencia_proyecto_menos_SBO=dp-ds,
                            captacion_desde_tierra=losses[0] if j == 2 else NAN,
                            captacion_desde_barcaza=losses[1] if j == 2 else NAN,
                            metodo_captacion='perdidas_netas_D*(P_SBO-P_proyecto); NO_matriz_transicion_individual',
                            estado_demanda='faltante_NO_cero' if not np.isfinite(total) else market['estado']))
                sensitivity.append(dict(**keys, **market, escenario=name, variante=c['variante'],
                    lambda_lago=c['lambda_lago'], delta_ASC_nuevo=c['delta_ASC_nuevo'],
                    frecuencia_nuevo=c['nuevo_f_semana_sentido'], f_SBO_alta=c['sbo_f_alta'], f_SBO_baja=c['sbo_f_baja'],
                    navegacion_h=c['navegacion_h'], P_SBO_tierra=ps[0], P_SBO_actual=ps[1],
                    P_proyecto_tierra=pr[0], P_proyecto_actual=pr[1], P_proyecto_nuevo=pr[2],
                    demanda_nuevo=total*pr[2], desde_tierra=losses[0], desde_actual=losses[1],
                    logsum_SBO=ls, logsum_proyecto=lp, ganancia_equivalente_CLP=(lp-ls)/abs(pp['beta_c'])))
    return dict(atributos_sbo=pd.DataFrame(attributes_s), atributos_bahia_jara_levican=pd.DataFrame(attributes_n),
                probabilidades_sbo=pd.DataFrame(probs_s), probabilidades_con_proyecto=pd.DataFrame(probs_p),
                demanda_desviada_por_alternativa=pd.DataFrame(diverted), logsums_sbo_proyecto=pd.DataFrame(logs),
                sensibilidad_proyecto=pd.DataFrame(sensitivity), reproduccion_11b=pd.DataFrame(checks_old))


def operacion(cfg):
    rows = []
    for name, c in escenarios(cfg):
        f = c['nuevo_f_semana_sentido']; cycles = math.ceil(f/c['dias_operacion_semana'])
        hours = 2*cycles*c['navegacion_h']+(2*cycles+1)*c['maniobra_operativa_h']
        rows.append(dict(escenario=name, f_sentido_semana=f, ciclos_dia_max=cycles,
                         horas_dia_max=hours, ventana_h=c['ventana_operativa_h_dia'],
                         factible_condicional=hours <= c['ventana_operativa_h_dia'],
                         condicion='nave_adicional_independiente_SBO; tripulacion_meteo_mantenimiento_y_rampas_no_certificados'))
    return pd.DataFrame(rows)


def md(d):
    def fmt(v):
        if pd.isna(v):
            return 'NaN'
        if isinstance(v, (float, np.floating)):
            return f'{v:.6g}'
        return str(v).replace('|', '/').replace('\n', ' ')
    return '\n'.join(['| '+' | '.join(d.columns)+' |', '| '+' | '.join(['---']*len(d.columns))+' |']+
                     ['| '+' | '.join(fmt(v) for v in row)+' |' for row in d.itertuples(index=False, name=None)])


def informe(out, cfg, tables, checks):
    d = tables['demanda_desviada_por_alternativa']; p = tables['probabilidades_con_proyecto']
    flows = d.loc[d.alternativa.eq(ALTS[2])]
    example = flows.loc[flows.origen.eq('Chile Chico') & flows.destino.eq('Coyhaique')]
    s = tables['sensibilidad_proyecto']; s = s.loc[s.origen.eq('Chile Chico') & s.destino.eq('Coyhaique') & s.estacion.eq('Verano') & s.segmento.eq('VL')]
    attrs = tables['atributos_bahia_jara_levican']; attrs = attrs.loc[attrs.origen.eq('Chile Chico') & attrs.destino.eq('Coyhaique') & attrs.estacion.eq('Verano')]
    central = tables['sensibilidad_proyecto']
    central = central.loc[central.escenario.eq('central')].drop_duplicates(K)
    principal = central.loc[central.origen.eq('Chile Chico') & central.destino.eq('Coyhaique')]
    coverage = flows.groupby(['segmento','escenario_mercado','unidad'], sort=False).agg(
        mercados=('demanda_total_OD','size'), totales_identificados=('demanda_total_OD','count'),
        captaciones_calculadas=('demanda_proyecto','count')).reset_index()
    text = f'''# Etapa12 — SBO y Bahía Jara–Levicán, aplicación exploratoria para revisión

Se ejecutó `python scripts/14_aplicar_etapa12.py`. Configuración: `data/templates/config_etapa12.json`.
No se recalibraron ASC, betas ni lambda; no se reconstruyeron matrices ni se calculó demanda inducida. Todos los resultados completos son locales/reservados en `outputs/etapa12/`, ignorados por Git. Sin commit/push. No publicar esta tabla completa ni recuperar celdas suprimidas en results mediante estos totales.

## Fuentes y parámetros conservados

Entradas vigentes: `outputs/calibracion_logit_11b/parametros_logit_recalibrados.csv`, `base_reutilizada_VL/CAM/PEATON.csv`; `outputs/atributos_logit_actualizados/atributos_logit_actualizados.csv`; matrices intactas en `outputs/matrices_od_referencia/` y sensibilidades en `outputs/expansion_temporal_terrestre/`. No se usan CSV suprimidos de results para reconstruir demanda.

Utilidad ASC + beta_c C + beta_t viaje + beta_e horario + beta_a acceso; costo privado CLP diciembre2025, horas. Betas exploratorios -0.00002, -0.20, -0.30, -0.30; ASC calibradas condicionalmente por segmento, copiadas con precisión completa a `parametros_reutilizados.csv`. ASC tierra0; nuevo=actual. Lambda0.70 supuesto, mu Biogeme=1/lambda, escala superior1. Nido terrestre singleton y nido lago con dos servicios coexistentes. Argentina y desconocidos excluidos sin redistribución.

`I_lago=lambda*logsumexp(V_lago/lambda)`; `L=logsumexp(V_tierra,I_lago)`; P(lago)=exp(I_lago-L), P(r|lago)=exp(V_r/lambda-logsumexp(V_lago/lambda)). Implementación matemática equivalente, sin optimizador. Dentro del soporte se integran probabilidades sobre los mismos perfiles/pesos11B; fuera del soporte se usa el mismo perfil medio/imputado11B. No se aplica logit al promedio de los atributos para sustituir esa integración. `reproduccion_11b.csv` verifica la predicción histórica antes de cambiar frecuencia.

## SBO y operación del proyecto

SBO central14 zarpes por sentido/semana dic–abr y12 may–nov: antecedente `sbo_actualizada/C_D_oferta_y_ocupacion_SBO.csv`, escenario baja_12_alta_14, navegación2h. Histórica11/8; sensibilidad SBO20. Otoño pondera marzo/abril y mayo por días de2026: se promedian penalizaciones, no se inventa una frecuencia estacional fija. Las dos naves son Tehuelche30VL/80ml/250pax y contratada44veh/252ml/300pax; cifras aproximadas del equipo. Se conserva discrepancia documental Tehuelche164ml en etapas anteriores. Agregar oferta no duplica mercado.

Nuevo14 por sentido/semana, siete días, dos ciclos/día. Una nave adicional independiente es requisito del escenario: las dos naves de SBO no se asignan simultáneamente a ambos cruces. No hay flota nueva financiada/contratada acreditada. Navegación80min CITRA Informe3 corregido §28.6.2 (ver páginas y extracto en evidencia_documental.json), sensibilidad40min EVALSO §2.0.2. Ventana12h y maniobra0.5h/terminal son supuestos heredados de SBO; central requiere {float(tables['operacion_nuevo'].iloc[0].horas_dia_max):.3f}h/día. 7/14/21 son escenarios de diseño, NO frecuencias CITRA ni óptimos. Anticipación2h vehículo/1h peatón, desembarque0.5h (sens0.25/0.75); se agrupan con navegación bajo beta_t. Presentación del pasajero no es tiempo de ocupación de nave. Horario0.25*168/f es desajuste, no espera física ni nuevo tiempo de embarque. No se resuelve asignación capacitada ni rechazos: logit es distribución sin restricción de cupos, pendiente verificar estiba/servicio punta.

## Recorridos y costos del proyecto

CITRA Informe2 corregido pp403–414 documenta conexión X763–R265 y X735–X65. X763 es pavimentada, operación60km/h (p406); X735 es ripio con puentes/angosturas. No se aplica indiscriminadamente ripio a ambas. La red ARISTO no contiene X735/X763; se crean segmentos virtuales de proyecto, sin afirmar que existan geometrías SIG verificadas. Secuencia por arco y fracción en `tramos_proyecto.csv`; sentidos reversos explícitos en atributos, sin diferencias direccionales no documentadas.

Sur: referencia EVALSO6.7km R265+10km X763=16.7km. Se fracciona R265 desde1358 a esa abscisa; la ubicación exacta del empalme y terminal no está certificada. CITRA3 cuadro de cartera muestra P27a10.90km/P27b9.29km, distintos de10km referenciales: no se sustituyen silenciosamente ni se simula P27a como geometría validada. Norte P20a31.14km (P20b22.60/P20d24.62, CITRA3 cartera). Enlace virtual al anclaje público1021 de Puerto Ibáñez: aproximación intralocal, no empalme exacto X735–X65. Desde allí se recorre toda la red real hasta Coyhaique1223. La diferencia frente a162.84km de EVALSO aparece en atributos; la referencia115km norte se conserva como contraste, sin corregirla ocultamente.

P20a mejorado:50km/h supuesto EVALSO cuadro8.8, sensibilidad40/60, no velocidad actual igualada al estándar futuro. X76360VL/50CAM y bus40 son hipótesis diferenciadas. COV se calcula como longitud por costo privado/km de Tipos de arcos ARISTO, dic2025: X735 análogo I1RBM1 (VL216/CAM1103 CLP/km), X763 I1PBM1 (VL169/CAM713). Son transferencias de tipos HDM4, sin recalcular motor HDM4 ni acreditar pendientes/curvatura del proyecto. COV proyecto ±20% sensibiliza estos tramos virtuales; R265 y norte conservan costos existentes. Fracciones de arco conservan costo proporcional, sin redondear tramo a CLP entero. No se suma CostGen monetizado ni precios sociales.

Tarifas nominales copiadas:21270VL,2550adulto,7310CLP/mCAM; factor109.26/109.71 heredado11B. Conductor liberado condicional, acompañantes y longitudes de los mismos perfiles11B; sin tarifa nueva oficial. Fecha enero2026 imputada, no comprobada. Tasas/peajes adicionales cero solo por continuidad del escenario11B, no ausencia comprobada.

{md(attrs[['segmento','distancia_terrestre_km','diferencia_referencia_162_84_km','tiempo_conduccion_perfil_h','COV','navegacion_h','C_privado_CLP_dic2025','t_viaje_h','t_horario_h','tarifa_bus_nominal']])}

PEATON: perfil adulto general de buses de acercamiento y barco pagados separadamente, NO todos los peatones. Bus nominal=10000*(km terrestres proyecto/km red Puerto Ibáñez–Coyhaique), sensibilidad ±20%; terminal sur también requiere bus, incluido en km totales. Referencias8000 CerroCastillo/7000Horquetas se conservan en configuración11, no se mezclan denominadores ni se inventan distancias adicionales. Descuentos TNE30%/mayores50% no aplicados al perfil adulto general. Alternativa integrada: precio proxy por km se supone completo y no se añade2550; no tarifa comercial observada. Tramo troncal de bus usa residuo2.5h del itinerario6h de11B proporcional a km; secundarios usan velocidades de bus supuestas. Se construye el nuevo itinerario sumando esos accesos, navegación y operaciones una sola vez; no se añade otra vez el viaje6h. La penalización horaria es una sola proxy del itinerario coordinado. ChileChico↔PuertoIbáñez peatón conserva elección desconocida por falta de alternativa terrestre identificada; no se finge indisponibilidad para forzar probabilidad1. En sus atributos nuevos puede describirse el acceso, pero las probabilidades permanecenNaN.

## Mercados y conservación

1. VL: suma ferry diario y tierra24h CC_PC1_laboral solo donde ambos existen. Demanda diaria equivalente exploratoria, NO observación24h. Invierno y otras celdas sin total quedanNaN. Otoño no imputa el mercado estacional desde mayo.
2. CAM24h_imputado_factor_VL: tierra10h multiplicada por factor temporalVL del mismo OD/estación, más ferry diario. Transferencia exploratoria de clase, NO mercado observado ni factorCAM validado; separada deVL. Sin factor se mantieneNaN.
3. CAM_contraste10h_diario: reproducción del contraste temporal de11B (tierra10h+ferry diario). Se muestran números en un índice mixto, NO como camiones/día, ni total estacional de otoño.
4. PEATON_imputado_cuota_VL: total hipotético=personas ferry/cuota ferryVL del mismo OD-estación; tierra hipotética=total−ferry. Es la hipótesis proxy de elecciónVL extendida explícitamente al tamaño del mercado; NO personas terrestres observadas ni inferencia validada. Sin cuota/ferry no se completa. Revisar este supuesto antes de usar volúmenes personales.

Estos escenarios no se suman entre sí, entre segmentos ni entre días representativos de estaciones. No se anualiza. Todos conservan su total enSBO/proyecto. Las pérdidas netas de cada alternativa existente D*(P_SBO−P_proyecto) suman captación nueva. Esta descomposición describe cambios agregados bajo parámetros fijos, NO identifica trayectorias individuales ni un flujo causal observado entre rutas.

## Probabilidades y captación: Chile Chico → Coyhaique

Probabilidades sin mezclar los distintos escenarios del tamaño de mercado:

{md(principal[K+['P_SBO_tierra','P_SBO_actual','P_proyecto_tierra','P_proyecto_actual','P_proyecto_nuevo']])}

{md(example[['estacion','segmento','escenario_mercado','unidad','demanda_total_OD','P_proyecto','demanda_proyecto','captacion_desde_tierra','captacion_desde_barcaza']])}

Cobertura efectiva (16 celdas por segmento y escenario: cuatroOD dirigidos por cuatro estaciones). No existe actualmente ninguna celda CAM con los dos flujos y factor24h compatible; por ello el escenario imputadoCAM24h queda enteroNaN. Sus dos resultados de otoño son solamente índices temporales mixtos, no volúmenes diarios de proyecto. ParaPuertoIbáñez no existe un mercado total de elección identificado; las probabilidades vehiculares sí pueden simularse con atributos condicionados. La aplicación numérica está ejecutada, pero la cobertura completa solicitada de demanda por todos los segmentos/estaciones sigue pendiente de estos datos.

{md(coverage)}

Todas las probabilidadesSBO/proyecto (48 mercados, incluyendo faltantes) en los CSV respectivos. Demanda por los cuatroOD, estación, segmento, escenario de mercado y alternativa en demanda_desviada_por_alternativa.csv. Tabla completa del nuevo cruce, ordenada por volumen dentro de cada segmento y escenario (no ranking mixto de personas/vehículos):

{md(flows.sort_values(['segmento','escenario_mercado','demanda_proyecto'], ascending=[True, True, False])[K+['escenario_mercado','unidad','demanda_total_OD','P_SBO','P_proyecto','demanda_proyecto','captacion_desde_tierra','captacion_desde_barcaza']])}

## Sensibilidades de un factor: VL verano Chile Chico → Coyhaique

{md(s[['escenario','P_SBO_actual','P_proyecto_tierra','P_proyecto_actual','P_proyecto_nuevo','demanda_nuevo','desde_tierra','desde_actual','ganancia_equivalente_CLP']])}

ASC existentes permanecen fijas también al variar lambda/tarifa/frecuencia/ASC nueva. Diferencia ASC nueva±0.5 es supuesto sin estimación empírica. P20b/d cambian solo longitud, NO acreditan el mismo estándar ni una evaluación completa de obra. Escenarios no son intervalos de confianza. sensibilidad_proyecto.csv contiene todos los mercados y escenarios, incluidosNaN.

## Logsums y siguiente etapa

{md(tables['logsums_sbo_proyecto'].loc[lambda z: z.origen.eq('Chile Chico') & z.destino.eq('Coyhaique'), K+['logsum_SBO','logsum_proyecto','ganancia_equivalente_CLP']])}

logsums_sbo_proyecto.csv contiene media ponderada de logsum por perfil, unidades/normalización, parámetros y equivalente CG=-L/abs(beta_c). La ganancia (L_proyecto−L_SBO)/abs(beta_c) es una medida monetaria exploratoria de mejora. El nivel deCG incluyeASC y entropía y puede ser negativo: NO aplicar automáticamente ratios deCG ni elasticidades a un origen arbitrario. Conservar distribución de perfiles para cualquier fórmula no lineal posterior; promedio de logsum no implica promedio de inducción.

Elasticidades transferidas/supuestas, NO estimadas ARISTO:VL−0.354 (0 a−0.60),CAM−0.106 (0 a−0.30),PEATON−0.80 (−0.50 a−1.20). Solo registradas; no se aplicaron. Antes de inducción: revisar totalesCAM/personas, estaciones faltantes, perfiles/estándares, terminales y conexiones, oferta y capacidad con flota adicional, precios y definición positiva/comparable delCG que utilizará la elasticidad.

## Verificación de la ejecución

`validacion.json`: {json.dumps(checks, ensure_ascii=False)}.
Hashes antes/después de resultados previos y fuentes usadas en integridad_anteriores.csv; manifiesto de código/entradas en manifiesto.json. Esta ejecución sí aplicó el modelo a escenarios reales/condicionales: las pruebas sintéticas adicionales no se presentan como recalibración o validación empírica. Los resultados son una aplicación exploratoria condicionada a conexiones/operación/mercados pendientes, no una predicción certificada de proyecto ni evaluación económica terminada.
'''
    (out/'resumen_etapa12.md').write_text(text, encoding='utf-8')


def main():
    cfgpath = ROOT/'data/templates/config_etapa12.json'
    cfg = json.loads(cfgpath.read_text()); out = ROOT/cfg['salida']
    out.mkdir(parents=True, exist_ok=True)
    protected = [p for p in (ROOT/'outputs').rglob('*') if p.is_file() and out not in p.parents]
    originals = [ROOT.parent/'Cap 7/HDM4/Costos_Red_Vial_Actual.xlsx', ROOT.parent/'INFORME_2_EVALSO-1.pdf',
                 ROOT.parent/'Estudios de consultoras/Informe 2c - MOP aysen vf.pdf', ROOT.parent/'Estudios de consultoras/Informe 3c - MOP aysen vf.pdf']
    before = {p: sha(p) for p in protected+originals}
    attrs = read('atributos_logit_actualizados/atributos_logit_actualizados')
    old = json.loads((ROOT/'outputs/calibracion_logit/config_utilizada.json').read_text())
    pars = read('calibracion_logit_11b/parametros_logit_recalibrados'); pars = pars.loc[pars.escenario.eq('central')]
    params = {s: dict(zip(g.parametro, g.valor)) for s, g in pars.groupby('segmento')}
    for p in params.values():
        assert np.allclose([p[k] for k in ['beta_c','beta_t','beta_a','beta_e','lambda_lago','ASC_terrestre']], [-.00002,-.2,-.3,-.3,.7,0])
    bases = {s: read('calibracion_logit_11b/base_reutilizada_'+s) for s in ['VL','CAM','PEATON']}
    b = read('matrices_od_referencia/matriz_od_barcaza'); t = read('matrices_od_referencia/matriz_od_terrestre')
    temporal = read('expansion_temporal_terrestre/matrices_24h_sensibilidades')
    markets = {keys: mercado(dict(zip(K,keys)), b, t, temporal) for keys, _ in attrs.groupby(K, sort=False)}
    routes, edges = red_proyecto(cfg)
    tables = simular(cfg, attrs, bases, params, old, routes, markets)
    tables['tramos_proyecto'] = edges; tables['parametros_reutilizados'] = pars
    tables['operacion_nuevo'] = operacion(cfg)
    prev_sbo = read('sbo_actualizada/C_D_oferta_y_ocupacion_SBO')
    tables['oferta_SBO_previa_reutilizada'] = prev_sbo.loc[prev_sbo.escenario.eq(cfg['sbo_escenario_previo']) & prev_sbo.navegacion_h.eq(2)].copy()
    oldprob = read('calibracion_logit_11b/probabilidades_base_recalibradas')
    comparison = oldprob.loc[oldprob.alternativa.eq(ALTS[1]), K+['probabilidad']].merge(tables['reproduccion_11b'], on=K, validate='one_to_one')
    comparison['diferencia'] = comparison.probabilidad_barcaza11B_reproducida-comparison.probabilidad
    tables['reproduccion_11b'] = comparison
    ps = tables['probabilidades_sbo']; pp = tables['probabilidades_con_proyecto']; d = tables['demanda_desviada_por_alternativa']
    new = d.loc[d.alternativa.eq(ALTS[2])]
    conservation = d.groupby(K+['escenario_mercado']).agg(total=('demanda_total_OD','first'), sbo=('demanda_SBO',lambda v:v.sum(min_count=3)), proyecto=('demanda_proyecto',lambda v:v.sum(min_count=3)))
    sens = tables['sensibilidad_proyecto']; known = sens.P_proyecto_nuevo.notna()
    checks = dict(
        parametros11B_intactos=True,
        reproduccion_probabilidades11B=bool(np.allclose(comparison.probabilidad, comparison.probabilidad_barcaza11B_reproducida, atol=1e-11, equal_nan=True)),
        probabilidades_rango=bool(ps.probabilidad.dropna().between(0,1).all() and pp.probabilidad.dropna().between(0,1).all()),
        suma_probabilidades=bool(np.allclose(ps.groupby(K).probabilidad.sum(min_count=2).dropna(),1) and np.allclose(pp.groupby(K).probabilidad.sum(min_count=3).dropna(),1)),
        conservacion_demanda=bool(np.allclose(conservation.total,conservation.sbo,equal_nan=True) and np.allclose(conservation.total,conservation.proyecto,equal_nan=True)),
        captacion_suma=bool(np.allclose(new.demanda_proyecto,new.captacion_desde_tierra+new.captacion_desde_barcaza,equal_nan=True)),
        sensibilidad_normalizada=bool(np.allclose(sens.loc[known,['P_proyecto_tierra','P_proyecto_actual','P_proyecto_nuevo']].sum(axis=1),1)),
        logsums_no_empeoran=bool((tables['logsums_sbo_proyecto'].diferencia_logsum.dropna() >= -1e-10).all()),
        no_demanda_invierno_imputada=bool(d.loc[d.estacion.eq('Invierno'),'demanda_total_OD'].isna().all()),
        frecuencias_nuevo_factibles_condicionales=bool(tables['operacion_nuevo'].factible_condicional.all()),
        frecuencia_SBO_en_antecedentes=bool(len(tables['oferta_SBO_previa_reutilizada'])>0 and tables['oferta_SBO_previa_reutilizada'].itinerario_constructible_condicionado.all()),
        anteriores_y_originales_intactos=all(sha(p)==h for p,h in before.items()))
    for name, table in tables.items():
        table.to_csv(out/(name+'.csv'), index=False, encoding='utf-8-sig', na_rep='NaN')
    integrity = pd.DataFrame([dict(archivo=str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p), sha256_antes=h, sha256_despues=sha(p), intacto=sha(p)==h) for p,h in before.items()])
    integrity.to_csv(out/'integridad_anteriores.csv', index=False)
    evidence = []
    needles = {'Informe 2c - MOP aysen vf.pdf': ['60 km/h','ripio','Ruta X-65 y la Ruta X-735'],
               'Informe 3c - MOP aysen vf.pdf': ['hora 20 minutos','31,14','22,60','24,62'],
               'INFORME_2_EVALSO-1.pdf': ['6,7 km','50 km/h','40 y 80 minutos']}
    for p in originals[1:]:
        txt = subprocess.check_output(['pdftotext','-layout',str(p),'-'], text=True)
        for number, page in enumerate(txt.split('\f'), 1):
            for term in needles[p.name]:
                if term in page:
                    pos = page.index(term)
                    evidence.append(dict(archivo=str(p), pagina_pdf_1=number, termino=term, extracto=page[max(0,pos-240):pos+280]))
    (out/'evidencia_documental.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2))
    (out/'config_utilizada.json').write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
    (out/'validacion.json').write_text(json.dumps(checks, indent=2))
    manifest = dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
                    codigo={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),cfgpath,ROOT/'src/demanda/proyecto.py']},
                    entradas={str(p):h for p,h in before.items()}, parametros_no_reestimados=True, induccion_aplicada=False)
    (out/'manifiesto.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    informe(out,cfg,tables,checks)
    print(json.dumps(checks, ensure_ascii=False, indent=2), flush=True)
    assert all(checks.values()), checks
    print('Salida:',out, flush=True)


if __name__ == '__main__':
    main()
