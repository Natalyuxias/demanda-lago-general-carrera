"""SBO de frecuencia y demanda atendida historica, cuatro estaciones y meses.

Reutiliza las extracciones verificadas del paso03, comprobando hashes.
No ejecuta captaciones ni anualizaciones incompletas del paso historico.
"""
from pathlib import Path
import sys,json,hashlib,calendar,math,importlib.util
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from demanda.capacidad import (limite_ciclos_dia,asignaciones,evaluar,
                              frecuencia_minima,horario_ciclos,documento_legible)
spec=importlib.util.spec_from_file_location('anterior',ROOT/'scripts/03_estimar_demanda_local.py')
prev=importlib.util.module_from_spec(spec);spec.loader.exec_module(prev)
OUT=ROOT/'outputs/sbo_actualizada'
OLD=ROOT/'outputs/historico/estimacion_preliminar_2026-10-24'


def save(df,name):df.to_csv(OUT/f'{name}.csv',index=False,encoding='utf-8-sig',na_rep='NaN')


def main():
    OUT.mkdir(exist_ok=True,parents=True)
    cfg=json.loads((ROOT/'data/templates/config_sbo.json').read_text())
    annex=ROOT.parent
    # Comprobar que el cache original y las participaciones corresponden a fuentes intactas.
    man=pd.read_csv(OLD/'fuentes_integridad.csv')
    for name in ['Base de datos agregada.xlsx','Consolidado Flujos.xlsx']:
        r=man.loc[man.fuente.map(lambda x:Path(x).name==name)].iloc[0]
        assert hashlib.sha256((annex/r.fuente).read_bytes()).hexdigest()==r.sha256
    cache=ROOT/'data/interim/estimacion_preliminar'
    raw=pd.read_pickle(cache/'conteos.pkl')
    raw['fila_excel']=raw.index+2
    raw=raw.loc[raw.Ruta.map(prev.es_lago)].copy()
    raw['campana']=raw.Temporada.str.strip()
    raw['sentido']=raw['Sentido de viaje'].map(prev.sentido)
    # Agregar categorias originales conservando vacios cuando no hay valores.
    raw['VL']=raw[['vehículos livianos','Camioneta','Minivan','Van','Casa Rodante']].sum(axis=1,min_count=1)
    raw['CAM']=raw['Camiones'];raw['PEATON']=raw['Peatones']
    raw['MOTO']=raw['Motos'];raw['BICI']=raw['Bicicletas']
    save(raw[['fila_excel','FECHA ','campana','sentido','VL','CAM','PEATON','MOTO','BICI']],'conteos_clases_separadas')
    means=raw.groupby(['campana','sentido'])[['VL','CAM','PEATON','MOTO','BICI']].agg(lambda s:s.mean(skipna=False)).reset_index()
    counts=raw.groupby(['campana','sentido']).size().reset_index(name='filas_zarpes_supuesto')
    means=means.merge(counts)
    save(means,'medias_por_zarpe_reutilizadas')
    # Participaciones vehiculares sin convertir pasajeros de bus/van en vehiculos.
    a=pd.read_pickle(cache/'eod_original_seleccion.pkl')
    b=pd.read_pickle(cache/'eod_valida_seleccion.pkl')
    d=a.merge(b,on='ID 2',validate='one_to_one')
    lake=d.loc[d['Lugar encuestado'].map(prev.es_lago)].copy()
    lake['sentido']=lake['Sentido Viaje'].map(prev.sentido)
    lake['campana']=lake['Versión'].str.strip()
    cats={'Auto':'VL','Camioneta':'VL','Vehículo privado':'VL','Moto':'MOTO','Camión o furgón de carga':'CAM','Pasajero (peatón)':'PEATON'}
    lake['segmento']=lake['Tipo usuario'].map(cats)
    parts=lake.dropna(subset=['segmento']).groupby(['campana','sentido','segmento','Nombre origen','Nombre destino']).size().reset_index(name='encuestas')
    parts['n_estrato']=parts.groupby(['campana','sentido','segmento']).encuestas.transform('sum')
    parts['participacion']=parts.encuestas/parts.n_estrato
    save(parts,'participaciones_OD_sin_pasajeros_como_vehiculos')
    monthly=[];od=[]
    directions=means.sentido.unique()
    for station,months in cfg['estaciones'].items():
        for m in months:
            days=calendar.monthrange(cfg['ano_calendario'],m)[1]
            freq=cfg['frecuencia_historica_por_mes'][str(m)]
            campaign=cfg['campana_por_mes'][str(m)]
            for direction in directions:
                z=means.loc[means.campana.eq(campaign)&means.sentido.eq(direction)]
                for seg in ['VL','CAM','PEATON','MOTO','BICI']:
                    q=float(z.iloc[0][seg]) if len(z) else math.nan
                    r=dict(estacion=station,mes=m,dias=days,sentido=direction,segmento=seg,campana_fuente=campaign,
                           frecuencia_ordinaria_semana=freq,media_por_zarpe=q,flujo_semana=q*freq,flujo_dia=q*freq/7,
                           viajes_mes=q*freq/7*days,estado='estimacion_condicional_atendida' if math.isfinite(q) else 'no_identificado',
                           unidad='personas_peatones' if seg=='PEATON' else 'unidades_clase_'+seg,
                           metodo='media_por_fila_zarpe; transferencia_de_campana_solo_meses_configurados')
                    monthly.append(r)
                    p=parts.loc[parts.campana.eq(campaign)&parts.sentido.eq(direction)&parts.segmento.eq(seg)]
                    if not len(p):
                        od.append(dict(**r,origen='OD_no_identificado',destino='OD_no_identificado',participacion=math.nan,flujo_od_dia=math.nan,flujo_sin_asignar_dia=r['flujo_dia']))
                    else:
                        for _,s in p.iterrows():od.append(dict(**r,origen=s['Nombre origen'],destino=s['Nombre destino'],participacion=s.participacion,flujo_od_dia=r['flujo_dia']*s.participacion,flujo_sin_asignar_dia=0))
    monthly=pd.DataFrame(monthly);od=pd.DataFrame(od)
    save(monthly,'A_historica_mensual');save(od,'A_historica_mensual_OD')
    def seasons(frame,value,keys):
        out=[]
        for k,g in frame.groupby(keys,dropna=False):
            complete=g[value].notna().all() and g.mes.nunique()==3
            val=(g[value]*g.dias).sum(min_count=1)
            out.append(dict(zip(keys,k),cobertura_meses_identificados=int(g.loc[g[value].notna(),'mes'].nunique()),
                            total_estacion=val if complete else math.nan,total_parcial_meses_identificados=val,
                            flujo_dia_estacion=val/g.dias.sum() if complete else math.nan,
                            flujo_semana_equivalente=val/g.dias.sum()*7 if complete else math.nan,
                            estado='condicional_completa' if complete else 'incompleta_no_anualizar'))
        return pd.DataFrame(out)
    seasonal=seasons(monthly,'flujo_dia',['estacion','sentido','segmento'])
    save(seasonal,'A_historica_estacional')
    save(seasons(od,'flujo_od_dia',['estacion','sentido','segmento','origen','destino']),'A_historica_estacional_OD')
    caprows=[]
    for name,n in cfg['naves'].items():
        variants=n.get('ml_variantes',{'Nueva_252':n.get('ml')})
        for v,ml in variants.items():caprows.append(dict(nave=name,variante=v,eslora_m=n['eslora_m'],pasajeros=n['pasajeros'],VL_aproximados_no_cupos_mixtos=n['VL_aproximados'],metros_lineales=ml,fuente=n['fuente'],estado='parametro_inicial_no_certificado'))
    save(pd.DataFrame(caprows),'B_capacidades_naves')
    op=cfg['operacion'];results=[];mins=[];events=[];type_rows=[]
    observed_path=OUT/'B_D_perfil_observado_longitud_CAM_m.csv'
    observed=pd.read_csv(observed_path) if observed_path.exists() else pd.DataFrame()
    # Una fila por mes/sentido; total mercado fijo, volumen lacustre retenido como escenario de oferta pura.
    for (month,direction),g in monthly.groupby(['mes','sentido']):
        q=dict(zip(g.segmento,g.flujo_semana));station=g.estacion.iloc[0];hist=int(g.frecuencia_ordinaria_semana.iloc[0])
        for profile,pr in cfg['perfiles_composicion_sensibilidad'].items():
            known=all(math.isfinite(q[s]) for s in ['VL','CAM','PEATON','MOTO'])
            lc=pr['longitud_CAM_m']
            if pr.get('usar_longitud_CAM_EOD'):
                lc=math.nan
                if len(observed):
                    oo=observed.loc[observed.estacion.eq(station)&observed['Sentido Viaje'].map(prev.sentido).eq(direction)]
                    if len(oo):lc=float(oo.iloc[0]['media'])
            # Bicicletas tienen huella supuesta, sin convertirlas otra vez en personas.
            lm=q['VL']*pr['longitud_VL_m']+q['CAM']*lc+q['MOTO']*pr['longitud_MOTO_m']+q['BICI']*pr['longitud_BICI_m']
            pax=q['PEATON']+q['VL']*pr['pax_VL']+q['CAM']*pr['pax_CAM']+q['MOTO']*pr['pax_MOTO']
            known=math.isfinite(lm) and math.isfinite(pax)
            for variant,ml in cfg['naves']['Tehuelche']['ml_variantes'].items():
                caps=(ml,cfg['naves']['Nueva']['ml'],cfg['naves']['Tehuelche']['pasajeros'],cfg['naves']['Nueva']['pasajeros'])
                for nav in op['navegacion_h_variantes']:
                    perday=limite_ciclos_dia(nav,op['maniobra_terminal_h'],op['horas_disponibles_dia'])
                    maximum=perday*op['dias_semana']
                    for scenario,freqs in cfg['frecuencias_sbo'].items():
                        high=max(cfg['frecuencia_historica_por_mes'].values())
                        value=freqs['alta' if hist==high else 'baja']
                        if value!=int(value) or value<0:raise ValueError('Frecuencia SBO no entera/negativa')
                        f=int(value)
                        if f<hist:raise ValueError('SBO inferior a frecuencia historica')
                        allocs=asignaciones(f,maximum)
                        # Reparto mas cercano a mitad y mitad entre las opciones fisicamente admisibles.
                        nt,nn=min(allocs,key=lambda x:abs(x[0]-x[1])) if allocs else (f//2,f-f//2)
                        schedule,possible=horario_ciclos(nt,nn,nav,op['maniobra_terminal_h'],op['horas_disponibles_dia'],op['dias_semana'])
                        if month==1 and direction==directions[0] and profile==next(iter(cfg['perfiles_composicion_sensibilidad'])) and variant=='ARISTO_164':
                            events.extend(dict(**e,escenario=scenario,navegacion_h=nav) for e in schedule)
                        e=evaluar(lm,pax,nt,nn,*caps)
                        for seg,lmetres,persons in [
                            ('VL',q['VL']*pr['longitud_VL_m'],q['VL']*pr['pax_VL']),
                            ('CAM',q['CAM']*lc,q['CAM']*pr['pax_CAM']),
                            ('MOTO',q['MOTO']*pr['longitud_MOTO_m'],q['MOTO']*pr['pax_MOTO']),
                            ('BICI',q['BICI']*pr['longitud_BICI_m'],math.nan),
                            ('PEATON',0,q['PEATON'])]:
                            type_rows.append(dict(estacion=station,mes=month,sentido=direction,perfil=profile,ml_Tehuelche=ml,
                                navegacion_h=nav,escenario=scenario,segmento=seg,unidades_semana=q[seg],
                                ml_requeridos_semana_sensibilidad=lmetres,pasajeros_semana_sensibilidad=persons,
                                aporte_ocupacion_ml=lmetres/e['capacidad_ml_semana'],
                                aporte_ocupacion_pasajeros=persons/e['capacidad_pax_semana'],
                                interpretacion='aporte_a_recurso_compartido_no_capacidad_independiente_por_clase; composicion_supuesta'))
                        results.append(dict(estacion=station,mes=month,sentido=direction,perfil=profile,ml_Tehuelche=ml,navegacion_h=nav,
                            escenario=scenario,frecuencia_historica=hist,frecuencia_SBO=f,zarpes_Tehuelche_sentido=nt,zarpes_Nueva_sentido=nn,
                            longitud_CAM_m_utilizada=lc,
                            metros_lineales_demanda_sensibilidad_semana=lm,pasajeros_sensibilidad_semana=pax,
                            demanda_lacustre_semana_fija_VL=q['VL'],induccion_total_mercado=cfg['induccion_total_SBO'],
                            delta_desfase_h=math.nan,delta_CG=math.nan,demanda_terrestre_transferida=math.nan,demanda_previamente_no_atendida=math.nan,
                            itinerario_constructible_condicionado=possible,capacidad_completa_identificada=False,
                            bicicletas_semana=q['BICI'],**e))
                    for target in cfg['ocupacion_objetivo']:
                        for peak in cfg['factores_punta']:
                            theoretical=frecuencia_minima(lm,pax,caps,target,peak,op['max_frecuencia_busqueda'],op['max_frecuencia_busqueda'])
                            physical=frecuencia_minima(lm,pax,caps,target,peak,maximum,op['max_frecuencia_busqueda'])
                            mins.append(dict(estacion=station,mes=month,sentido=direction,perfil=profile,ml_Tehuelche=ml,navegacion_h=nav,
                                ocupacion_objetivo=target,factor_punta_diseno=peak,
                                frecuencia_minima_capacidad_promedio=theoretical[0] if theoretical and peak==1 else math.nan,
                                frecuencia_minima_capacidad_con_punta=theoretical[0] if theoretical else math.nan,
                                frecuencia_minima_con_ventana_operacional=physical[0] if physical else math.nan,
                                frecuencia_SBO_minima_condicional=max(hist,physical[0]) if physical else math.nan,
                                frecuencia_economicamente_optima=math.nan,
                                estado_minimo=('no_identificado_por_demanda_o_composicion' if not known else
                                               'sin_solucion_con_ventana_y_limite_busqueda' if not physical else 'calculado_condicionado'),
                                estado='sensibilidad_estiba_y_pasajeros_no_certificados' if known else 'demanda_incompleta'))
    save(pd.DataFrame(results),'C_D_oferta_y_ocupacion_SBO')
    save(pd.DataFrame(type_rows),'D_aportes_ocupacion_por_segmento')
    save(pd.DataFrame(mins),'C_frecuencias_minimas_condicionales')
    save(pd.DataFrame(events),'C_itinerarios_maniobras_constructivos')
    # Razones por fila observada no equivalen a rechazo; capacidad30 es aproximacion.
    peak=raw[['fila_excel','campana','sentido','VL','CAM','PEATON']].copy()
    peak['razon_VL_sobre_30_solo_VL_no_estiba_mixta']=peak.VL/cfg['naves']['Tehuelche']['VL_aproximados']
    peak['usuarios_rechazados']=math.nan;peak['esperaron_otro_zarpe']=math.nan;peak['cancelaron']=math.nan
    save(peak,'D_conteos_por_fila_NO_rechazos')
    (OUT/'config_utilizada.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2))
    (OUT/'INFORME_SBO.md').write_text(documento_legible(informe(cfg,seasonal,means)))
    print(seasonal[['estacion','sentido','segmento','flujo_dia_estacion','cobertura_meses_identificados']].to_string(index=False))


def informe(cfg,seasonal,means):
    table=prev.mdtable(seasonal.loc[seasonal.segmento.isin(['VL','CAM','PEATON']),['estacion','sentido','segmento','flujo_dia_estacion','cobertura_meses_identificados']])
    return f'''# Demanda histórica y SBO de frecuencia — 25/10/2026

## Demanda histórica atendida

Frecuencias ordinarias confirmadas por el usuario: diciembre–abril11 y mayo–noviembre8, por sentido y semana, excluida carga peligrosa. Se conservan conteos y TD Transb originales; las nuevas tablas usan media por fila/zarpe×frecuencia/7. Se reutilizaron hashes y caches del paso03. Una fila por zarpe en verano/mayo sigue siendo supuesto; primavera tiene apoyo en tabla78 ARISTO. No se identificó en los conteos si un embarque corresponde a carga peligrosa: aplicar frecuencia ordinaria a esa composición requiere verificar manifiestos.

Se separan VL de cuatro ruedas (livianos/camioneta/minivan/van/casa rodante), CAM (agregado ARISTO, incluidos furgones y remolques), MOTO, BICI y peatones columnaG. No se suman personas y vehículos. Cambia la definición respecto del privado ARISTO que incluía motos/bicicletas: se documenta y conservan los originales. Los NaN de componentes no se transforman en ceros; los agregados de categorías reportadas no certifican cobertura completa de clases.

Verano usa campaña enero/febrero, primavera la de noviembre, con transferencia condicional a meses de la estación. Mayo usa Normal. Marzo/abril y todo invierno quedan sin perfil principal: las frecuencias son conocidas, la ocupación no. No se extiende mayo al otoño completo. Se mantienen cuatro estaciones y el detalle mensual. No se calcula total anual porque faltan meses. Los flujos estacionales completos son promedios ponderados por días; los totales parciales están en columnas distintas, no son totales de estación. La matriz OD usa participaciones muestrales dentro de campaña/sentido/clase; estratos sin muestra quedan sin asignar.

{table}

## Capacidad documental

La discrepancia80/164ml tiene fuentes: CITRA Informe2c p417 informa80ml/30veh/250personas; p418 eslora70.20m. ARISTO tabla de naves p126 y AnexoA RevB informan164ml/250pax. No se encontró equivalencia certificada entre definiciones ni plano de estiba que reconcilie ambas cifras: se evalúan ambas, sin escoger una. No confundir80ml con eslora ni deducir longitud vehicular de30cupos aproximados.

Nueva: usuario80m,300pax,44VL aproximados,252ml, diésel/eléctrica,13nudos. ARISTO p155 indica288pax/252ml/13nudos: se registra la diferencia y se mantiene300 como definición inicial actual del usuario, no certificación. Las capacidades30/44 se presentan como aproximaciones de flota homogénea, nunca cupos fijos mixtos.

## SBO y nivel de servicio

Solo cambia frecuencia. Tarifa, accesos y tiempo de navegación permanecen iguales entre naves y frente al histórico dentro de cada variante. Se evalúan2h ARISTO frente a2h40 CITRA como sensibilidad documental; no se usa13nudos para reducir tiempos de la nueva nave. Inducción total del mercado=0 por instrucción. Para aislar oferta también se mantiene el volumen lacustre atendido histórico; la redistribución desde tierra no está estimada, no equivale a afirmar que sea cero. `preparar_cambio_costo` admite desfase histórico/SBO y VST, devuelve NaN mientras falten; no adopta intervalo/2.

Frecuencias configurables: mismo total histórico con dos naves, baja12/alta11, baja12/alta14 y20 todo el año. Nunca inferiores al histórico. Se reparten inicialmente casi por mitades. La capacidad semanal por sentido es n_T×C_T+n_N×C_N, separada para metros lineales y pasajeros.

Los perfiles compacto/largo son SUPUESTOS de longitudes y ocupantes, con procedencia en config_sbo.json. No son composición medida ni estiba certificada. El perfil CAM_longitud_EOD incorpora la longitud media positiva declarada por camiones del mismo estrato, documentada por el paso05; no rellena el estrato de verano CC→Ibáñez sin entrevistas CAM. Mantiene supuestos de longitud VL y ocupantes. Si el perfil observado aún no se generó, deja NaN hasta ejecutar05 y repetir04. ML=VL×l_VL+CAM×l_CAM+MOTO×l_MOTO+BICI×l_BICI; pax=peatones+VL×ocupantes_VL+CAM×ocupantes_CAM+MOTO×ocupantes_MOTO. No se añaden grupos ni pasajeros de bus otra vez. Bicicletas tienen huella longitudinal supuesta; no se agregan automáticamente personas por bicicleta: las ocupaciones y mínimos son restricciones parciales, no validación de capacidad completa. Faltan anchos, separaciones, pesos, combinaciones tractor/remolque y pasajeros totales verificados.

Se distinguen mínimo aritmético por capacidad media, mínimo con factores punta de diseño1.5/2 y mínimo compatible con ventana operativa supuesta. Objetivos80/90/95% son nivel de servicio, no captación. La búsqueda enumera asignaciones enteras entre ambas naves. Una punta aplicada a toda la semana es una envolvente conservadora de diseño, no un percentil observado ni garantía por zarpe. Las razones por fila medida se entregan aparte; no se infieren rechazos, colas, cancelaciones o viajes desviados por capacidad. Frecuencia económicamente óptima=NaN: faltan costos marginales y beneficios.

## Comprobación física condicionada

Un ciclo cubre ambos sentidos y devuelve la nave a su puerto inicial. Para n ciclos al día:2n×navegación+(2n+1)×maniobra. Configuración de diseño: maniobra0.5h, ventana12h/día,7días/semana. Se construyen maniobras con naves inicialmente en orillas opuestas y se comprueban ventanas y solapamientos de servicio de terminal. La capacidad máxima de ciclos cambia entre2h y2h40: algunos escenarios altos pueden resultar imposibles dentro de esa ventana. No se certifican operación real, disponibilidad de tripulación, meteo, luz, mantenimiento, atraque de espera o tiempos reales de rampa. No hay pasajeros asignados a horarios específicos; capacidad agregada no garantiza atención punta.

## Archivos y reproducción

`python scripts/04_actualizar_sbo.py`. Configuración:data/templates/config_sbo.json; módulo:src/demanda/capacidad.py. A_historica_mensual y estacional incluyen OD y cobertura; B_capacidades_naves conserva discrepancias; C_D_oferta_y_ocupacion_SBO evalúa oferta; C_frecuencias_minimas_condicionales distingue mínimos; C_itinerarios_maniobras_constructivos documenta calendario relativo; D_conteos_por_fila_NO_rechazos conserva observaciones sin inferir usuarios rechazados.

Los escenarios10/25/50 anteriores se conservan en outputs/historico/estimacion_preliminar_2026-10-24. No forman parte del cálculo actual. Captación del nuevo cruce=NO IDENTIFICADA, pendiente de CG/elección. La investigación terrestre se entrega por separado. No se modificaron originales ni se hizo commit/push.
'''


if __name__=='__main__':main()
