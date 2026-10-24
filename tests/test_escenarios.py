import pandas as pd
import pytest
from demanda.escenarios import simular_captacion


def base(**kwargs):
    datos = dict(temporada="Verano", sentido="CC_PI", segmento="livianos",
                 flujo_lago_dia=100., flujo_tierra_elegible_dia=float("nan"),
                 dias_temporada=80., estado_fuente="supuesto", fuente_y_metodo="ejemplo SINTETICO")
    datos.update(kwargs)
    return pd.DataFrame([datos])


def test_tierra_desconocida_no_es_cero():
    r = simular_captacion(base(), tasas=[0.25])
    assert r.iloc[0]["desviados_del_lago_dia"] == 25
    assert pd.isna(r.iloc[0]["captacion_total_dia"])
    assert r.iloc[0]["desviados_del_lago_periodo"] == 2000


def test_tierra_observada():
    r = simular_captacion(base(flujo_tierra_elegible_dia=40), tasas=[0.25])
    assert r.iloc[0]["captacion_total_dia"] == 35


def test_sin_flujo_no_estima():
    with pytest.raises(ValueError):
        simular_captacion(base(flujo_lago_dia=float("nan")))


def test_sin_puede_observar_sin_fuente():
    with pytest.raises(ValueError):
        simular_captacion(base(estado_fuente="pendiente"))
