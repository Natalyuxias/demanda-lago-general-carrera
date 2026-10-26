"""Entradas enteramente sintéticas; no se abren resultados reales."""
import importlib.util
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('et13_test',ROOT/'scripts/15_estimar_demanda_preliminar.py')
stage=importlib.util.module_from_spec(spec);spec.loader.exec_module(stage)


def test_transferencia_conserva_sentido_y_oferta_destino():
    c=json.loads((ROOT/'data/templates/config_etapa13.json').read_text())
    bar=[];tierra=[];hist=[]
    for o,d in c['od']:
        for seg in c['segmentos']:
            for s in c['estaciones']:
                keys=dict(origen=o,destino=d,estacion=s,segmento=seg)
                hist.append(dict(keys,alternativa='barcaza_actual',probabilidad=.1 if s=='Invierno' else .4))
                if s=='Otoño':
                    if seg=='CAM' and 'Puerto Ibáñez' in (o,d):continue
                    q=10 if o=='Chile Chico' else 20
                    bar.append(dict(keys,demanda_diaria_24h_equivalente=q))
                    if seg!='PEATON':tierra.append(dict(keys,demanda_expandida_viajes_diarios_promedio=2))
    factors=pd.DataFrame([dict(perfil=c['perfil_temporal'],estacion_destino=s,factor_24h_10h_sensibilidad=1.5) for s in ['Verano','Primavera']])
    fake=dict(bar=pd.DataFrame(bar),tierra=pd.DataFrame(tierra),historica=pd.DataFrame(hist),factores=factors,
              mercado12=pd.DataFrame(columns=stage.K+['alternativa','escenario_mercado','demanda_total_OD']))
    m=stage.completar(fake,c)
    winter=m.loc[m.estacion.eq('Invierno')&m.segmento.eq('VL')]
    assert winter.loc[winter.origen.eq('Chile Chico'),'demanda_total_OD'].eq(13).all()
    assert winter.loc[~winter.origen.eq('Chile Chico'),'demanda_total_OD'].eq(23).all()
    assert winter.P_historica.eq(.1).all()  # No se reemplaza la oferta de destino.
    service=m.loc[m.ambito.ne('mercado_eleccion')]
    assert len(service)==8 and service.demanda_total_OD.isna().all()
    assert service.demanda_servicio_lacustre.notna().all()
    cam=m.loc[m.segmento.eq('CAM')]
    assert cam.demanda_total_OD.notna().all()
    assert cam.metodo.eq('D_CAM_OD_comparable_razon_mercados_VL').sum()==8


def test_piso_probabilidad_registrado():
    c=dict(probabilidad_minima_imputacion=.05,multiplicador_participacion_imputacion=1)
    total,p,flag=stage.imputar_barcaza(2,.0001,c)
    assert total==40 and p==.05 and flag
    assert np.isnan(stage.imputar_barcaza(np.nan,.2,c)[0])


def test_auditoria_rechaza_intervalo_que_reconstruye_celda():
    keys=dict(origen='A',destino='B',estacion='S',segmento='CAM')
    matrix=pd.DataFrame([dict(keys,ambito='mercado_eleccion',demanda_total_OD=10,metodo='A')])
    table=pd.DataFrame([dict(keys,demanda_total_OD=10,dias_estacion=365)])
    scenarios={'central':{'demanda_desviada':table}}
    public=pd.DataFrame([dict(escenario='central',segmento='CAM',concepto='existente_anual',limite_inferior=3650,limite_superior=3650.0001)])
    c=dict(segmentos=['CAM'],publicacion=dict(minimo_ancho_relativo_celda_reservada=.1))
    with pytest.raises(ValueError,match='acota demasiado'):
        stage.auditar_intervalos(public,matrix,scenarios,c)
