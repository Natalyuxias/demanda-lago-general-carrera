"""Etapa adicional 10h→24h: preserva las matrices del paso07.

Base sin factor identificado y sensibilidades híbridas CITRA diurno + MOP12→24.
No ejecuta los estimadores anteriores, no anualiza y no calcula TMDA.
"""
from pathlib import Path
import hashlib
import json
import math
import re
import subprocess
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from demanda.temporal import suma_ventana, cociente, factor_hibrido

SRC = ROOT / 'outputs/matrices_od_referencia'
OUT = ROOT / 'outputs/expansion_temporal_terrestre'


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(frame, name):
    frame.to_csv(OUT / (name + '.csv'), index=False, encoding='utf-8-sig', na_rep='NaN')


def md(frame):
    def fmt(v):
        if pd.isna(v): return 'No identificado'
        if isinstance(v, float): return f'{v:.4f}'
        return str(v).replace('|', '/').replace('\n', ' ')
    return '\n'.join(['| ' + ' | '.join(frame.columns) + ' |',
                      '| ' + ' | '.join(['---'] * len(frame.columns)) + ' |'] +
                     ['| ' + ' | '.join(fmt(v) for v in row) + ' |' for row in frame.itertuples(index=False, name=None)])


def extraer_tablas(pdf, cfg):
    chunks = []
    for start, end in cfg['rangos_paginas_pdf']:
        chunks.append(subprocess.run(['pdftotext', '-f', str(start), '-l', str(end), '-layout', str(pdf), '-'],
                                     capture_output=True, check=True, text=True).stdout)
    text = '\n'.join(chunks)
    page_marks = [(m.start(), int(m[1])) for m in re.finditer(r'Pág\.\s*(\d+)', text)]
    tables = {}
    records = []
    for number in sorted({p['tabla'] for p in cfg['perfiles']}):
        header = re.search(r'Cuadro N°\s*' + str(number) + r':', text)
        if header is None: raise ValueError(f'Tabla no encontrada: {number}')
        nxt = re.search(r'Cuadro N°\s*\d+:', text[header.end():])
        end = header.end() + nxt.start() if nxt else len(text)
        block = text[header.end():end]
        rows = []
        for match in re.finditer(r'(\d{1,2}):00\s+a\s+(\d{1,2}):00([^\n]*)', block):
            values = [int(v.replace('.', '').replace(',', '')) for v in re.findall(r'\d+(?:[.,]\d+)?', match[3])]
            if not values: continue
            pos = header.end() + match.start()
            page = [p for a, p in page_marks if a <= pos][-1]
            start, finish = int(match[1]), int(match[2])
            if finish != start + 1: raise ValueError('Intervalo no horario')
            row = dict(tabla=number, pagina=page, hora_inicio=start, hora_fin=finish,
                       total_publicado_veq_h=values[-1], suma_movimientos_redondeados= sum(values[:-1]),
                       discrepancia_total=values[-1] - sum(values[:-1]), movimientos_json=json.dumps(values[:-1]))
            rows.append(row); records.append(row)
        if not rows: raise ValueError(f'Tabla sin horas: {number}')
        if len({r['hora_inicio'] for r in rows}) != len(rows): raise ValueError(f'Horas duplicadas tabla {number}')
        if len({len(json.loads(r['movimientos_json'])) for r in rows}) != 1:
            raise ValueError(f'Columnas inconsistentes en tabla {number}')
        footers=re.findall(r'^\s*Total\s+([^\n]+)',block,re.MULTILINE)
        footer_values=[]
        if footers:
            footer_values=[int(v.replace('.', '').replace(',', '')) for v in re.findall(r'\d+(?:[.,]\d+)?',footers[0])]
        for r in rows:
            r['total_periodo_publicado_veq']=footer_values[-1] if footer_values else math.nan
            r['totales_movimientos_periodo_json']=json.dumps(footer_values[:-1]) if footer_values else '[]'
        tables[number] = rows
    return tables, pd.DataFrame(records)


def calcular_perfiles(tables, cfg):
    profiles, hourly, factors = [], [], []
    for p in cfg['perfiles']:
        rows = tables[p['tabla']]
        by_hour = {}
        individual = 'indice_movimiento' in p
        severe = any(abs(r['discrepancia_total']) > max(5, 0.02 * r['total_publicado_veq_h']) for r in rows)
        for r in rows:
            value = json.loads(r['movimientos_json'])[p['indice_movimiento']] if individual else r['total_publicado_veq_h']
            by_hour[r['hora_inicio']] = value
            hourly.append(dict(perfil=p['id'], serie=p.get('serie','Total_publicado'), valor_veq_h=value, **r))
        assert sorted(by_hour) == list(range(*p['horas'])), p['id']
        quality = ('movimiento_original_sin_usar_total_inconsistente' if individual and severe else
                   'total_inconsistente_excluido' if severe else 'total_publicado_con_redondeo_por_movimientos')
        footer=json.loads(rows[0]['totales_movimientos_periodo_json'])
        printed=(footer[p['indice_movimiento']] if individual and footer else rows[0]['total_periodo_publicado_veq'])
        metadata = dict(perfil=p['id'], localidad=p['localidad'], punto=p['punto'], tabla=p['tabla'],
                        paginas=';'.join(str(x) for x in sorted({r['pagina'] for r in rows})),
                        fuente=cfg['fuente_CITRA'], fecha_medicion=math.nan, estacion_fuente=math.nan,
                        publicacion_informe='diciembre_2025_NO_fecha_medicion', tipo_dia=p['tipo_dia'],
                        sentido_fuente=p.get('serie','todos_movimientos_interseccion'),
                        inicio_observado=p['horas'][0], fin_observado=p['horas'][1], horas_observadas=len(rows),
                        unidad_perfil='vehiculos_equivalentes_publicados_NO_vehiculos_fisicos',
                        tipo_vehiculo_fuente='mezcla_categorias_en_veq_sin_perfil_fisico_VL_CAM',
                        total_periodo_fuente_publicado_veq=printed,
                        suma_horarios_publicados_veq=sum(by_hour.values()),
                        diferencia_suma_horas_total_periodo=sum(by_hour.values())-printed,
                        calidad_tabla=quality, comparabilidad_Cerro_Castillo=p['comparabilidad'])
        profiles.append(metadata)
        for station, window in cfg['ventanas_ARISTO'].items():
            q10 = suma_ventana(by_hour, *window)
            q12 = suma_ventana(by_hour, *cfg['ventana_12h_referencia'])
            q24 = suma_ventana(by_hour, 0, 24)
            coef = cfg['coeficientes_MOP_12_24'].get(station, math.nan)
            eligible = (not severe or individual) and p['tipo_dia'] == 'laboral'
            hybrid = factor_hibrido(q12, q10, coef) if eligible else math.nan
            reason = ('sin_coeficiente_otono_ni_24h_observado' if station=='Otoño' else
                      'total_tabla_inconsistente' if severe and not individual else
                      'ventana07_19_o_10h_incompleta_o_tipo_dia_no_homologable' if not math.isfinite(hybrid) else
                      'sensibilidad_urbana_veq_fecha_y_estacion_desconocidas; NO_factor_oficial10h')
            factors.append(dict(**metadata, estacion_destino=station, ventana_ARISTO=f'{window[0]:02d}:00-{window[1]:02d}:00',
                                flujo_10h_perfil_veq=q10, flujo_12h_07_19_veq=q12,
                                flujo_periodo_observado_veq=sum(by_hour.values()), flujo_24h_observado_veq=q24,
                                factor_24h_10h_directo=cociente(q24,q10), proporcion_10h_en24h_observada=cociente(q10,q24),
                                relacion_12h_10h=cociente(q12,q10), factor_periodo_parcial_10h=cociente(sum(by_hour.values()),q10),
                                coeficiente_MOP_12_24=coef, factor_24h_10h_sensibilidad=hybrid,
                                proporcion_10h_en24h_supuesta=cociente(1,hybrid),
                                fuente_coeficiente=cfg['fuente_coeficientes'], estado=reason,
                                aplicado_a_matriz_como_sensibilidad=p['id'] in cfg['perfiles_sensibilidad_matriz']))
    return pd.DataFrame(profiles), pd.DataFrame(hourly), pd.DataFrame(factors)


def construir_matrices(original, factor_table, cfg):
    original = original.copy()
    assert original.ruta.eq('terrestre_chile').all()
    original.insert(0, 'fila_matriz_10h', range(2,len(original)+2))
    original['demanda_10h_original'] = original.demanda_expandida_viajes_diarios_promedio
    original['unidad_encuestas'] = 'registros_validos; no_son_flujo_diario'
    all_cases = []
    for case in ['base_sin_factor_identificado'] + cfg['perfiles_sensibilidad_matriz']:
        x = original.copy(); x['caso'] = case
        if case == 'base_sin_factor_identificado':
            x['factor_temporal_aplicado'] = math.nan
            x['fuente_factor'] = 'No se localizo un perfil24h interurbano comparable por fecha/segmento/sentido'
            x['calidad_representatividad'] = 'no_identificado'
        else:
            selected = factor_table.loc[factor_table.perfil.eq(case)].set_index('estacion_destino')
            x['factor_temporal_aplicado'] = x.estacion.map(selected.factor_24h_10h_sensibilidad)
            info=selected.iloc[0]
            x['fuente_factor'] = f"CITRA Informe1 cuadro{info.tabla} pp{info.paginas} + MOP12-24; serie {info.sentido_fuente}"
            x['calidad_representatividad'] = x.estacion.map(selected.estado).fillna('sin_medicion_estacional_ARISTO')
        x['demanda_estimada_24h'] = x.demanda_10h_original * x.factor_temporal_aplicado
        x['ventana_origen'] = x.estacion.map({s:f'{h[0]:02d}:00-{h[1]:02d}:00' for s,h in cfg['ventanas_ARISTO'].items()})
        x['unidad_temporal_24h'] = 'unidad_fisica_original_por_dia_equivalente24h_condicionado_NO_TMDA'
        x['tipo_factor'] = 'sin_factor' if case=='base_sin_factor_identificado' else 'hibrido_sensibilidad_NO_oficial10_24'
        x['limite_transferencia'] = '; '.join(cfg['supuestos_sensibilidad']) if case!='base_sin_factor_identificado' else cfg['caso_base']
        all_cases.append(x)
    return pd.concat(all_cases,ignore_index=True)


def controles_y_validacion(matrix, factor_table, control10, original):
    rows=[];share_checks=[]
    group=['estacion','sentido_control','segmento']
    for case,x in matrix.groupby('caso',sort=False):
        assigned=x.loc[x.demanda_10h_original.notna()&x.sentido_control.notna()].groupby(group).demanda_10h_original.sum().to_dict()
        for r in control10.loc[control10.segmento.isin(['VL','CAM'])].itertuples():
            station=r.estacion
            candidates=factor_table.loc[factor_table.perfil.eq(case)&factor_table.estacion_destino.eq(station)]
            factor=candidates.iloc[0].factor_24h_10h_sensibilidad if len(candidates) else math.nan
            total10=r.conteo_medio_por_jornada
            q10=assigned.get((station,r.sentido_control,r.segmento),0.0)
            rest=total10-q10
            assert rest>=-1e-9
            rows.append(dict(caso=case,estacion=station,sentido_control=r.sentido_control,segmento=r.segmento,
                             conteo_control_10h=total10,asignado_a_OD_lista_10h=q10,
                             resto_control_10h_sin_repartir_por_ruta_OD=rest,factor_temporal=factor,
                             control24h_estimado=total10*factor,asignado_OD24h=q10*factor,
                             resto_control24h_sin_repartir_por_ruta_OD=rest*factor,
                             validacion='identidad_algebraica_NO_representatividad_OD; resto incluye otrosOD_y_rutas_desconocidas'))
        for _,g in x.loc[x.demanda_estimada_24h.notna()].groupby(group):
            a=g.demanda_10h_original; b=g.demanda_estimada_24h
            if a.sum()>0 and b.sum()>0:
                share_checks.append(bool(((a/a.sum()-b/b.sum()).abs()<1e-10).all()))
    checks=dict(
        composicion_OD_conservada=all(share_checks),
        sin_duplicar_filas_entre_misma_sensibilidad=not matrix.duplicated(['caso','fila_matriz_10h']).any(),
        sin_duplicar_OD_expandido=not matrix.loc[matrix.demanda_10h_original.notna()].duplicated(
            ['caso','estacion','origen','destino','sentido','segmento','ruta','sentido_control']).any(),
        solo_ruta_terrestre_chile=bool(matrix.ruta.eq('terrestre_chile').all()),
        base24_sigue_no_identificada=bool(matrix.loc[matrix.caso.eq('base_sin_factor_identificado'),'demanda_estimada_24h'].isna().all()),
        sin_factor_otono_inventado=bool(matrix.loc[matrix.estacion.eq('Otoño'),'factor_temporal_aplicado'].isna().all()),
        faltantes_originales_conservados=bool(matrix.loc[matrix.demanda_10h_original.isna(),'demanda_estimada_24h'].isna().all()),
        valores10h_preservados=all(x.demanda_10h_original.reset_index(drop=True).equals(original.demanda_expandida_viajes_diarios_promedio.reset_index(drop=True)) for _,x in matrix.groupby('caso',sort=False)))
    controls=pd.DataFrame(rows)
    valid=controls.dropna(subset=['control24h_estimado'])
    checks['conservacion_control24_estimado']=bool(((valid.asignado_OD24h+valid.resto_control24h_sin_repartir_por_ruta_OD-valid.control24h_estimado).abs()<1e-8).all())
    return controls, checks


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    cfg=json.loads((ROOT/'data/templates/config_expansion_temporal.json').read_text())
    before={str(p.relative_to(ROOT)):digest(p) for p in SRC.iterdir() if p.is_file()}
    pdf=ROOT.parent/cfg['fuente_CITRA']
    tables,raw=extraer_tablas(pdf,cfg)
    profiles,hourly,factors=calcular_perfiles(tables,cfg)
    save(raw,'tablas_CITRA_transcripcion_automatica')
    save(hourly,'perfiles_horarios_fuente')
    save(profiles,'inventario_perfiles_CITRA')
    save(factors,'factores_10h_24h_y_cobertura')
    official=pd.DataFrame([dict(estacion=s,coeficiente_12_24=cfg['coeficientes_MOP_12_24'].get(s,math.nan),
                               ventana_original_horas=12,fuente=cfg['fuente_coeficientes'],verificacion=cfg['verificacion_fuente'])
                           for s in ['Verano','Otoño','Invierno','Primavera']])
    save(official,'coeficientes_MOP_verificados_NO_factores10h')
    original=pd.read_csv(SRC/'matriz_od_terrestre.csv')
    matrix=construir_matrices(original,factors,cfg)
    save(matrix.loc[matrix.caso.eq('base_sin_factor_identificado')],'matriz_terrestre_24h_base')
    save(matrix.loc[~matrix.caso.eq('base_sin_factor_identificado')],'matrices_24h_sensibilidades')
    save(matrix,'comparacion_terrestre_10h_24h')
    control10=pd.read_csv(SRC/'factores_y_comparacion_ARISTO.csv')
    controls,checks=controles_y_validacion(matrix,factors,control10,original)
    save(controls,'balance_control_corredor_24h_estimado')
    bar=pd.read_csv(SRC/'matriz_od_barcaza.csv')
    keys=['estacion','origen','destino','segmento']
    bar=bar.groupby(keys,dropna=False).agg(
        barcaza_promedio_diario_equivalente24h=('demanda_expandida_viajes_diarios_promedio',lambda s:s.sum(min_count=1)),
        unidad_fisica_barcaza=('unidad',lambda s:';'.join(sorted(set(s.dropna().astype(str)))))).reset_index()
    comparison=matrix.merge(bar,on=keys,how='left',validate='many_to_one')
    comparison['compatibilidad']='unidad temporal diaria equivalente; conservar unidad fisica de cada columna y verificar claseCAM; campanas y representatividad no identicas; NO_sumar_para_mercado_total'
    save(comparison,'comparacion_barcaza_tierra_diaria_equivalente')
    pncpath=ROOT.parent/'Cap 3/Flujos vehiculares/Flujos_Vehiculares_PNC_2024-2022-2020-2018-2016-2014.xlsx'
    cols=['AÑO','REGIÓN','PC','RAMA','NOMBRE CAMINO','ROL','ESTACIÓN\nASIMILABLE','MUESTRA','TOTAL RAMA']
    pnc=pd.read_excel(pncpath,sheet_name='BBDD',usecols=cols)
    pnc=pnc.loc[pnc.AÑO.eq(2024)&pnc.REGIÓN.eq(11)&pnc.PC.isin([46,55,58,63])].copy()
    pnc['utilidad_temporal']='volumen_agregado_publicado; sin_horas_no_identifica_F24_10'
    save(pnc,'PNCV_estaciones_candidatas_sin_perfil_horario')
    audit=pd.read_csv(SRC/'auditoria_exposicion_Cerro_Castillo.csv')
    for r in audit.itertuples():
        s={'Normal':'Otoño'}.get(r.campana,r.campana)
        assert cfg['ventanas_ARISTO'][s]==[r.hora_inicio_conteo,r.hora_fin_conteo]
        dates=r.fechas_informe.split(';')
        assert all(pd.Timestamp(d).weekday()<5 for d in dates)
    roadpath=ROOT.parent/'Cap 6/Mediciones de flujo/Consolidado Flujos.xlsx'
    road=pd.read_excel(roadpath,sheet_name='Carretera',usecols=['PC','Temporada','SENTIDO','DÍA','CUARTO'])
    roadcov=road.groupby(['PC','Temporada','SENTIDO','DÍA']).CUARTO.agg(['min','max','nunique']).reset_index()
    roadcov['exposicion_horas']=roadcov['nunique']/4
    save(roadcov,'cobertura_horaria_ARISTO_carretera')
    checks['ningun_perfil_CITRA_es24h']=bool(profiles.horas_observadas.lt(24).all())
    checks['sin_F24_10_directo_ficticio']=bool(factors.factor_24h_10h_directo.isna().all())
    candidate=factors.dropna(subset=['factor_24h_10h_sensibilidad','flujo_10h_perfil_veq'])
    checks['sensibilidad24_no_inferior_a_periodo_observado']=bool((
        candidate.factor_24h_10h_sensibilidad*candidate.flujo_10h_perfil_veq>=candidate.flujo_periodo_observado_veq-1e-9).all())
    checks['ventanas10h_cotejadas_ARISTO']=True
    checks['matrices_paso07_intactas']=all(digest(ROOT/p)==v for p,v in before.items())
    assert all(checks.values()),checks
    (OUT/'validacion.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2))
    (OUT/'config_utilizada.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2))
    save(pd.DataFrame([dict(archivo=p,sha256=v,intacto=True) for p,v in before.items()]),'integridad_matrices_10h_y_barcaza')
    save(pd.DataFrame([dict(archivo=str(p.relative_to(ROOT.parent)),sha256=digest(p)) for p in [pdf,pncpath,roadpath]]),'fuentes_locales_hash')
    report(matrix,profiles,factors,official,pnc,controls,checks,cfg)
    print(f'Extraídos {len(profiles)} perfiles de {len(tables)} tablas; 0 perfiles de24h. Sensibilidades guardadas en {OUT}')


def report(matrix,profiles,factors,official,pnc,controls,checks,cfg):
    selected=factors.loc[factors.perfil.isin(cfg['perfiles_sensibilidad_matriz'])]
    core=matrix.loc[matrix.ambito.eq('nucleo_Chile_Chico_ribera_norte')&matrix.demanda_10h_original.notna()]
    keys=['estacion','origen','destino','segmento','unidad','demanda_10h_original']
    tab=core.pivot(index=keys,columns='caso',values='demanda_estimada_24h').reset_index()
    lower=profiles[['perfil','paginas','tipo_dia','inicio_observado','fin_observado','horas_observadas','calidad_tabla']]
    chosen=selected[['perfil','tabla','paginas','estacion_destino','ventana_ARISTO','flujo_10h_perfil_veq','flujo_12h_07_19_veq','flujo_24h_observado_veq','relacion_12h_10h','coeficiente_MOP_12_24','factor_24h_10h_sensibilidad']]
    text=f'''# Expansión temporal terrestre 10→24 horas — etapa adicional

## Resultado y criterio de uso

No se localizó un perfil horario **observado de 24 horas** defendible para Cerro Castillo en las fuentes seleccionadas. El caso base de 24h permanece faltante. Se revisaron21 tablas de7 puntos para3 tipos de día y se conservaron además2 series de movimientos del cuadro44: no son23 mediciones independientes. Se entregan cuatro sensibilidades explícitas por forma diurna de Chile Chico, para verano y primavera; **no son factores oficiales de 10h**, ni una estimación estadísticamente validada por OD. Mayo no recibe el coeficiente de otra estación; invierno permanece sin matriz observada. No se calcula TMDA ni anualización.

Se preservaron todos los archivos del paso07 por hash. La nueva etapa lee la matriz terrestre y agrega demanda10h, factor temporal, demanda24h, procedencia y calidad. Las otras rutas no reciben estos factores.

## Factores calculados y flujos de las fuentes

Las columnas de flujo CITRA están en **vehículos equivalentes integrados por hora** (veq), no vehículos físicos ni pasajeros. La proporción 10h/24h observada no puede calcularse: falta parte de la noche. `flujo_24h_observado_veq` y `factor_24h_10h_directo` permanecen NaN. No se extrapolan los gráficos: se extraen valores tabulados del PDF con `pdftotext`, conservando hora, cuadro, página y total publicado.

{md(chosen)}

Fuente CITRA: `{cfg['fuente_CITRA']}`, §§2.3.2.1–2.3.2.2 pp165–218, §2.3.2.3 pp218–222 y §2.3.2.5 pp250–261. Los perfiles pertenecen a estudios anteriores; en las secciones citadas no se informa fecha ni estación de medición. La publicación diciembre2025 no es la fecha de los aforos. Los días laborales de ARISTO son martes/miércoles de noviembre2025, lunes/martes de febrero2026 y jueves de mayo2026; solo el tipo de día laboral puede emparejarse con CITRA.

{md(lower)}

Las periódicas de Chile Chico (§2.3.2.2, pp175–176) observan intervalos de1,5h por período punta/fuera de punta, discontinuos; no contienen 24h ni completan la noche. Las continuas laborales7–23 tienen16h, sábado9–23 tiene14h y domingo10–22 tiene12h. Ni siquiera las12h del domingo corresponden a la ventana diurna07–19 del puente PNCV.

El cuadro44 p173 tiene un error visible: Total reproduce movimiento42 en todas las horas. Se conserva el valor publicado y su discrepancia con suma de movimientos en `tablas_CITRA_transcripcion_automatica.csv`; el total no genera factor. Las series24 y42 conservan sus celdas originales, documentadas como movimientos directos de Ruta265 en el croquis, sin recomponer el total ni homologar automáticamente los sentidos con Cerro Castillo. Los pequeños desfases de1–2veq de otros cuadros se registran y pueden deberse al redondeo independiente de los movimientos; se utiliza el total de cada hora publicado. La integración suma esas celdas horarias, y también se conserva el total de período impreso y su diferencia con esa suma. Ningún ajuste de redondeo se distribuye silenciosamente entre horas.

## Coeficientes oficiales y adaptación de ventanas

La [Dirección de Vialidad](https://vialidad.mop.gob.cl/plan-nacional-de-censo-vial/) confirma coeficientes generales **12→24h**, verificados el25/10/2026:

{md(official)}

La [documentación MOP2014]({cfg['fuente_ventana']}) describe el conteo PNCV12h entre07–19. Su correspondencia con los coeficientes generales actuales es una hipótesis explícita de esta sensibilidad. No se dispone aquí del perfil de calibración original por estación/clase/sentido.

Se calcula para cada perfil laboral elegible:

`r12/10 = suma(CITRA 07–19) / suma(CITRA ventana ARISTO)`

`F10→24_sens = r12/10 × coeficiente_MOP12→24(estación)`

`Q_OD24_sens = Q_OD10_original × F10→24_sens`

Primavera ARISTO usa08–18; verano y mayo09–19, cotejados con CUARTO y40 intervalos/jornada de ODC3. No se aplica el coeficiente12→24 directamente ni se usa12/10=1,2 suponiendo flujo uniforme. La cobertura de toda la hoja Carretera revisada es10h por jornada; `cobertura_horaria_ARISTO_carretera.csv` registra cada punto/campaña/sentido/día.

La transferencia de cocientes calculados con veq a VL/CAM físicos exige que la forma horaria sea trasladable entre clases y localidades. Se mantiene **la unidad física original** y solo se multiplica por un cociente adimensional. No hay perfil individual VL/CAM ni orientación común de sentido: los factores son iguales para ambos sentidos/segmentos dentro de cada escenario, por supuesto. No se trata veq como vehículos ni se estima pasajeros a partir de ellos. Las diferencias entre escenarios de movimiento24/42 representan forma horaria, no un mapeo a N–S/S–N.

## Matriz comparativa: núcleo local

Unidades VL/CAM: vehículos por jornada10h en la columna original y vehículos por día equivalente24h en las sensibilidades. El caso base permanece faltante. Otoño representa únicamente mayo. Los CSV completos incluyen los otros OD candidatos y celdas sin medición; los faltantes se conservan, sin convertirlos en cero.

{md(tab)}

## PNCV y comparabilidad territorial

Se revisó el Excel local ARISTO `Cap3/Flujos vehiculares/Flujos_Vehiculares_PNC_2024-2022-2020-2018-2016-2014.xlsx`, hoja BBDD, Aysén2024. Estaciones46 (bifurcación Puerto Ibáñez),55 (bifurcación Balmaceda),58 (bifurcación Puerto Guadal) y63 (bifurcación Puerto Murta) son candidatos geográficos por Ruta7. El archivo publica volúmenes agregados por campaña/rama/categoría; **no publica la secuencia horaria para aislar08–18 o09–19**. La columna estación asimilable se conserva literalmente, sin inferir una serie nocturna desde sus códigos. El [portal oficial PNCV](https://vialidad.mop.gob.cl/plan-nacional-de-censo-vial/) ofrece el archivo Aysén2024 de volúmenes regionales; no se identificó allí una descarga de perfil horario local que resuelva esta razón. No se deduce un factor comparando campañas, años diferentes o TMDA.

Los candidatos PNCV completos quedan en `PNCV_estaciones_candidatas_sin_perfil_horario.csv`. Chile Chico es urbano en Ruta265 y tiene viajes locales, acceso fronterizo y barcaza; Cerro Castillo es un control interurbano de Ruta7. Cochrane tiene perfiles urbanos y Puerto Cisnes tráfico costero y una localización contradictoria entre texto y figuras. Sus cocientes se informan como referencias secundarias en el CSV de factores, sin aplicación automática. Ningún punto sustituye una estación24h comparable por estación, clase, sentido y día.

## Validaciones y comparación con barcaza

Se conserva la composición OD dentro del grupo estación/sentido/clase al multiplicar todas sus filas por el mismoF. El control completo es mayor que los OD terrestres seleccionados: NO se obliga a que esos OD sumen todo el tránsito del corredor. `balance_control_corredor_24h_estimado.csv` verifica:

`C24_estimado = Q24_asignado_lista_OD + resto24_sin_repartir_por_ruta_OD`

El resto incluye otros OD y rutas desconocidas; no se convierte en tierra del proyecto. Reproducir ese total estimado es una identidad aritmética y **no garantiza representatividad de cada OD**, ni valida el factor temporal.

`comparacion_barcaza_tierra_diaria_equivalente.csv` conserva el flujo de barcaza promedio semanal/7 junto al terrestre24h supuesto. La unidad temporal es diaria equivalente, pero las fechas y la representatividad difieren; no se calcula una cuota modal ni se suman para afirmar mercado total. Peatones y vehículos mantienen unidades separadas. Argentina y rutas desconocidas permanecen fuera de la expansión.

Validaciones: `{json.dumps(checks,ensure_ascii=False)}`.

## Archivos y reproducción

- `matriz_terrestre_24h_base.csv`: factor y flujo24h base faltantes, con las10h originales.
- `matrices_24h_sensibilidades.csv` y `comparacion_terrestre_10h_24h.csv`: cálculos condicionados y cobertura.
- `factores_10h_24h_y_cobertura.csv`: fuente/página/punto/día/ventana/clase/flujo10h/flujo24h/factor/calidad.
- `perfiles_horarios_fuente.csv`: series extraídas de tablas, sin lecturas aproximadas de gráficos.
- `integridad_matrices_10h_y_barcaza.csv`: hashes que prueban que las matrices anteriores permanecen iguales.

Ejecutar desde el proyecto: `python scripts/08_expandir_tiempo_terrestre.py`. Parámetros y supuestos: `data/templates/config_expansion_temporal.json`. La ejecución usa únicamente fuentes locales y la transcripción documentada de parámetros oficiales; no depende de consultas web para repetir el cálculo. Originales y resultados07 intactos; salidas08 locales excluidas de Git, sin commit/push.

Para reemplazar las sensibilidades por un caso base faltan conteos horarios de24h de una sección interurbana comparable, fechas y sentidos, clasificación física VL/CAM y cobertura por estación/tipo de día. Para mayo falta además respaldo estacional específico; ningún coeficiente oficial de otoño fue localizado en la fuente citada.
'''
    (OUT/'resumen_expansion_temporal.md').write_text(text,encoding='utf-8')


if __name__=='__main__':
    main()
