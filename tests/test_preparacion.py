from demanda.preparacion import normalizar_cadena
from demanda.costos import costo_generalizado_privado
import pandas as pd
import pytest

def test_acentos():
    assert normalizar_cadena('Río Ibáñez') == 'rio ibanez'

def test_cg_unidades():
    a = pd.DataFrame([dict(c_privado_clp=20000,vst_clp_h=10000,
                           t_acceso_h=1,t_viaje_h=2,t_horario_h=0.5,t_embarque_h=0.25)])
    assert costo_generalizado_privado(a).iloc[0] == pytest.approx(57500)

def test_cg_no_silencia_faltantes():
    with pytest.raises(ValueError):
        costo_generalizado_privado(pd.DataFrame([dict(c_privado_clp=20)]))
