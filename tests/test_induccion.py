import numpy as np
import pytest
from demanda.induccion import respuesta_perfiles


def fixture():
    xs=np.array([[[10000,3,0,0],[12000,2,4,1]],[[50000,5,0,0],[20000,3,6,2]]],float)
    xp=np.concatenate([xs,np.array([[[8000,2,1,.5]],[[17000,2,3,1]]])],axis=1)
    return xs,xp,np.array([.3,.7]),np.array([-.00002,-.2,-.3,-.3])


def test_induccion_conserva_y_no_logsum_negativo_como_costo():
    x,z,w,b=fixture()
    r=respuesta_perfiles(x,z,w,b,-.3,-.354)
    assert r['cg_referencia']>0 and r['beneficio']>0
    assert r['factor_total']>1
    assert np.isclose(r['inducida_por_unidad'].sum(),r['factor_total']-1)
    assert np.isclose(r['p_sbo'].sum(),1) and np.isclose(r['p_proyecto'].sum(),1)
    no=respuesta_perfiles(x,z,w,b,-.3,0)
    assert no['factor_total']==1 and np.allclose(no['inducida_por_unidad'],0)


def test_heterogeneidad_se_transforma_antes_de_agregar():
    x,z,w,b=fixture()
    all_=respuesta_perfiles(x,z,w,b,-.3,-.8)
    each=[respuesta_perfiles(x[i:i+1],z[i:i+1],[1],b,-.3,-.8) for i in range(2)]
    assert np.isclose(all_['factor_total'],sum(w[i]*r['factor_total'] for i,r in enumerate(each)))
    assert np.allclose(all_['inducida_por_unidad'],sum(w[i]*r['inducida_por_unidad'] for i,r in enumerate(each)))
    assert not np.isclose(all_['factor_total'],all_['factor_transformacion_media'])


def test_limite_explicito_y_formula_local():
    x,z,w,b=fixture()
    r=respuesta_perfiles(x,z,w,b,-.3,-.8,factor_cg=.001,max_reduccion=.8)
    assert r['n_limitados']==2 and r['peso_cociente_invalido_sin_limite']==1
    assert np.isclose(r['cociente_min'],.2)
    assert np.isfinite(r['factor_total'])
    local=respuesta_perfiles(x,z,w,b,-.3,-.8,formula='local')
    constant=respuesta_perfiles(x,z,w,b,-.3,-.8)
    assert 1<local['factor_total']<constant['factor_total']
    with pytest.raises(ValueError):
        respuesta_perfiles(x,z,w,b,-.3,-.8,max_reduccion=1)


def test_cg_componentes_coherentes_un_perfil():
    x,z,w,b=fixture()
    r=respuesta_perfiles(x[:1],z[:1],[1],b,-.3,-.354)
    economic=x[0] @ np.array([1,10000,15000,15000])
    assert np.isclose(r['cg_referencia'],r['p_sbo']@economic)
