"""Seleccionar resultados YA calculados para compartir. No estima demanda ni logit.

Lee outputs locales excluidos de Git; escribe results/ y una comparación histórica.
Regla editorial: no divulgar flujos de celdas pequeñas ni atributos individuales.
El umbral no representa una garantía formal de anonimato.
"""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs';RES=ROOT/'results'
SEG=['VL','CAM','PEATON']
KEY=['origen','destino','estacion','segmento']
OD=[('Chile Chico','Coyhaique'),('Coyhaique','Chile Chico'),('Chile Chico','Puerto Ibáñez'),('Puerto Ibáñez','Chile Chico')]
MIN=5
MANIFEST=[]


def read(rel):return pd.read_csv(OUT/rel)
def save(d,rel,source,criterion):
    p=ROOT/rel;p.parent.mkdir(parents=True,exist_ok=True)
    d.to_csv(p,index=False,encoding='utf-8-sig',na_rep='NaN')
    MANIFEST.append(dict(archivo=rel,fuente_local=source,criterio_seleccion=criterion,filas=len(d),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))


def exportar_etapa12(coverage):
    """Solo el mercado VL verano ya divulgado; sin totales de otras celdas."""
    source='etapa12/sensibilidad_proyecto.csv'
    target='results/etapa12/ejemplo_vl_verano.csv'
    if not (OUT/source).exists():
        # Conservar una selección revisada existente si no hay salidas12 locales.
        manifest=RES/'manifest_publicacion.json'
        if (ROOT/target).exists():
            previous=json.loads(manifest.read_text())
            item=next(x for x in previous['archivos'] if x['archivo']==target)
            assert hashlib.sha256((ROOT/target).read_bytes()).hexdigest()==item['sha256']
            MANIFEST.append(item)
        return
    support=coverage.loc[coverage.origen.eq('Chile Chico')&coverage.destino.eq('Coyhaique')&coverage.estacion.eq('Verano')&coverage.segmento.eq('VL')]
    assert len(support)==1 and support.n_terrestre_chile.ge(MIN).all() and support.n_barcaza_actual.ge(MIN).all()
    d=read(source)
    d=d.loc[d.origen.eq('Chile Chico')&d.destino.eq('Coyhaique')&d.estacion.eq('Verano')&d.segmento.eq('VL')&d.escenario_mercado.eq('VL24h_exploratorio')].copy()
    assert len(d)>0 and d.escenario.eq('central').sum()==1 and not d.duplicated(KEY+['escenario']).any()
    cols=KEY+['escenario','variante','lambda_lago','delta_ASC_nuevo','frecuencia_nuevo','f_SBO_alta','f_SBO_baja','navegacion_h',
        'demanda_total_OD','unidad','estado','P_SBO_tierra','P_SBO_actual','P_proyecto_tierra','P_proyecto_actual','P_proyecto_nuevo',
        'demanda_nuevo','desde_tierra','desde_actual','logsum_SBO','logsum_proyecto','ganancia_equivalente_CLP']
    save(d[cols],target,'outputs/'+source,
        'Solo VL verano Chile Chico->Coyhaique ya compartido; soporte>=5 por alternativa; central y sensibilidades del mismo mercado; sin otros OD/segmentos ni totales complementarios')


def main():
    MANIFEST.clear()
    bar=read('matrices_od_referencia/matriz_od_barcaza.csv')
    road=read('matrices_od_referencia/matriz_od_terrestre.csv')
    h=read('expansion_temporal_terrestre/matrices_24h_sensibilidades.csv')
    matrix=[]
    for o,d in OD:
        for season in ['Verano','Otoño','Invierno','Primavera']:
            for route in ['barcaza_actual','terrestre_chile']:
                source=bar if route=='barcaza_actual' else road
                g=source.loc[source.origen.eq(o)&source.destino.eq(d)&source.estacion.eq(season)&source.segmento.eq('VL')]
                value10=value24=np.nan
                # Divulgación limitada al ejemplo con ambas alternativas de soporte>=5.
                allowed=(o,d,season)==('Chile Chico','Coyhaique','Verano') and len(g)==1 and g.iloc[0].encuestas_validas>=MIN
                if allowed:
                    if route=='barcaza_actual':value24=g.iloc[0].demanda_diaria_24h_equivalente
                    else:
                        value10=g.iloc[0].demanda_expandida_viajes_diarios_promedio
                        hh=h.loc[h.origen.eq(o)&h.destino.eq(d)&h.estacion.eq(season)&h.segmento.eq('VL')&h.caso.eq('CC_PC1_laboral')]
                        assert len(hh)==1;value24=hh.iloc[0].demanda_estimada_24h
                matrix.append(dict(origen=o,destino=d,estacion=season,segmento='VL',ruta=route,flujo_10h_vehiculos=value10,
                    flujo_diario_equivalente_vehiculos=value24,estado='expandido_condicional' if allowed and route=='barcaza_actual' else 'sensibilidad_24h_NO_observado' if allowed else 'no_publicado_o_no_identificado;NO_cero',
                    cobertura='ejemplo_compartible;NO_matriz_completa',fuente='ARISTO/etapa07; tiempo/etapa08 CC_PC1_laboral',
                    advertencia='Se omiten otras celdas por soporte reducido o supresion complementaria; consultar matrices completas solo localmente'))
    save(pd.DataFrame(matrix),'results/matrices_od/matriz_vl_divulgacion.csv','outputs/matrices_od_referencia; outputs/expansion_temporal_terrestre','Ejemplo VL verano; dos alternativas con soporte>=5; resto reservado sin publicar totales que permitan reconstruir celdas')
    factors=read('expansion_temporal_terrestre/factores_10h_24h_y_cobertura.csv')
    factors=factors.loc[factors.perfil.isin(['CC_PC1_laboral','CC_PC2_laboral','CC_PC3_mov24_laboral','CC_PC3_mov42_laboral'])&factors.estacion_destino.isin(['Verano','Primavera'])]
    cols=['perfil','localidad','estacion_destino','ventana_ARISTO','relacion_12h_10h','coeficiente_MOP_12_24','factor_24h_10h_sensibilidad','estado','fuente_coeficiente','comparabilidad_Cerro_Castillo']
    save(factors[cols],'results/expansion_temporal/factores_sensibilidad.csv','outputs/expansion_temporal_terrestre/factores_10h_24h_y_cobertura.csv','Cocientes calculados, sin transcribir conteos horarios originales CITRA')
    attrs=read('atributos_alternativas/atributos_alternativas.csv')
    attrs=attrs.loc[attrs.alternativa.isin(['terrestre_chile','barcaza_actual'])&attrs.segmento.isin(['VL','CAM'])&attrs.estacion.eq('Verano')].copy()
    cols=['origen','destino','segmento','alternativa','distancia_terrestre_total_km','tiempo_conduccion_terrestre_h','tiempo_navegacion_h','t_acceso_modelo_h','anticipacion_exigida_h','COV_terrestre_privado_ARISTO_CLP','fuente_distancia','fuente_COV']
    attrs=attrs[cols];attrs['alcance']='Entre anclajes publicos de red; NO domicilio; velocidades/COV estaticos; COV CLP diciembre2025 por vehiculo-viaje'
    save(attrs,'results/atributos/rutas_completas_vehiculares.csv','outputs/atributos_alternativas/atributos_alternativas.csv','Solo atributos de red, sin longitud/ocupacion declaradas ni secuencias de arcos originales')
    cfg=json.loads((ROOT/'data/templates/config_calibracion_logit.json').read_text())
    tariffs=[dict(concepto=k,valor=v,fuente=cfg['fuente_tarifas_equipo'],vigencia='pendiente') for k,v in cfg['tarifas_equipo'].items()]
    tariffs += [dict(concepto='adulto_barcaza_historico',valor=2550,fuente='ARISTO tabla52 p121',vigencia='mes exacto pendiente'),dict(concepto='vehiculo_hasta5_5m',valor=21270,fuente='ARISTO tabla52 p121',vigencia='mes exacto pendiente'),dict(concepto='metro_lineal_CAM',valor=7310,fuente='ARISTO tabla52 p121',vigencia='categoria y longitud facturada pendientes')]
    save(pd.DataFrame(tariffs),'results/atributos/tarifas_referencia.csv','config_calibracion_logit.json; ARISTO tabla52','Tarifas de referencia y descuentos, sin tickets ni pagadores individuales')
    p=read('calibracion_logit_11b/parametros_logit_recalibrados.csv')
    cols=['segmento','escenario','parametro','valor','valor_escala_Biogeme','unidad','metodo','condicion','error_estandar','alcance_error','unidad_decision','VST_CLP_h','ratio_acceso','ratio_horario','ponderacion']
    save(p.loc[p.escenario.eq('central'),cols],'results/calibracion_logit/parametros_centrales_11b.csv','outputs/calibracion_logit_11b/parametros_logit_recalibrados.csv','Parametros de modelos agregados; ninguna fila de eleccion/atributo individual')
    save(p.loc[~p.escenario.eq('central'),cols],'results/sensibilidades/parametros_11b.csv','outputs/calibracion_logit_11b/parametros_logit_recalibrados.csv','Supuestos y ASC de modelos, no nuevas observaciones')
    coverage=read('atributos_logit_actualizados/cobertura_elecciones_por_OD.csv')
    def protect(q):
        q=q.merge(coverage[KEY+['n_terrestre_chile','n_barcaza_actual']],on=KEY,how='left',validate='many_to_one')
        verified=q.segmento.eq('VL')&q.n_terrestre_chile.ge(MIN)&q.n_barcaza_actual.ge(MIN)&q.origen.isin(['Chile Chico','Coyhaique'])&q.destino.isin(['Chile Chico','Coyhaique'])
        proxy=q.segmento.eq('PEATON')&q.origen.isin(['Chile Chico','Coyhaique'])&q.destino.isin(['Chile Chico','Coyhaique'])
        allowed=verified|proxy
        q.loc[~allowed,'probabilidad']=np.nan
        q['estado_divulgacion']=np.where(allowed,np.where(proxy,'perfil_modelado_con_cuota_proxy_NO_personas_observadas','VL_soporte_compartido>=5_por_alternativa'),'reservado_por_soporte_reducido_o_atributo_no_identificado')
        return q
    q=protect(read('calibracion_logit_11b/probabilidades_base_recalibradas.csv'))
    cols=KEY+['alternativa','probabilidad','escenario','tipo','estado_divulgacion','unidad_decision']
    save(q[cols],'results/calibracion_logit/probabilidades_11b_divulgacion.csv','outputs/calibracion_logit_11b/probabilidades_base_recalibradas.csv','VL con soporte>=5 en ambas alternativas; peatones perfil proxy; CAM/otros OD reservados; sin medias individuales')
    sens=protect(read('calibracion_logit_11b/sensibilidades_parametros.csv'))
    save(sens[cols+['VST','ra','re','lam','factor']],'results/sensibilidades/probabilidades_11b_divulgacion.csv','outputs/calibracion_logit_11b/sensibilidades_parametros.csv','Misma supresion que central; no se publican atributos ni probabilidades de celdas reducidas')
    fit=read('calibracion_logit_11b/ajuste_recalibraciones.csv');fit=fit.loc[fit.escenario.eq('central')]
    cols=['segmento','escenario','n_filas','tipo_filas','cuota_objetivo','cuota_predicha','log_likelihood','rho2','fuente_objetivo']
    save(fit[cols],'results/calibracion_logit/ajuste_global_11b.csv','outputs/calibracion_logit_11b/ajuste_recalibraciones.csv','Objetivos globales sobre61VL/9CAM; proxy referido a VL. Sin desagregacion de los controles de celdas')
    old=read('calibracion_logit/parametros_logit.csv');old=old.loc[old.escenario.eq('central'),['segmento','parametro','valor','unidad','metodo','error_estandar']]
    save(old,'archive/results/etapa11/parametros_centrales.csv','outputs/calibracion_logit/parametros_logit.csv','Comparacion historica de modelos; no entrevistas ni objetivos por celda')
    exportar_etapa12(coverage)
    (RES/'manifest_publicacion.json').write_text(json.dumps(dict(version='2026-10-26',regla='Seleccion editorial conservadora; MIN5 por alternativa y supresion complementaria; no garantia formal de anonimato',archivos=MANIFEST),ensure_ascii=False,indent=2)+'\n')
    print('Resultados compartibles exportados sin estimar:',len(MANIFEST))


if __name__=='__main__':main()
