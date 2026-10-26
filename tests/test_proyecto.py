import numpy as np
import pytest
from scipy.special import softmax
from demanda.proyecto import logit_anidado, desviar


def test_limite_mnl_y_singleton():
    v = [-2, -.5, -1]
    p, _ = logit_anidado(v, 1)
    assert np.allclose(p, softmax(v))
    for lam in [.5, .7, 1]:
        p, _ = logit_anidado(v[:2], lam)
        assert np.allclose(p, softmax(v[:2]))


def test_nido_identico_y_conservacion():
    s, ls = logit_anidado([-2, -1])
    p, lp = logit_anidado([-2, -1, -1])
    assert p[1] == p[2]
    assert lp > ls
    captados = desviar(100, s, p)
    assert np.isclose(captados.sum(), 100 * p[2])
    assert (captados > 0).all()


def test_faltante_no_equivale_indisponible():
    p, _ = logit_anidado([-2, -1, np.nan])
    assert np.isnan(p).all()
    p, _ = logit_anidado([-2, -1, np.nan], disponibles=[True, True, False])
    assert p[2] == 0
    assert np.isclose(p.sum(), 1)
    assert np.isnan(desviar(np.nan, [.5, .5], [.3, .3, .4])).all()
    with pytest.raises(ValueError):
        logit_anidado([0, 1, 2], 1.1)


def test_estabilidad_extremos():
    p, ls = logit_anidado([-10000, -10001, -9999], .5)
    assert np.isfinite(ls)
    assert np.isclose(p.sum(), 1)


def test_equivalencia_biogeme_tres_alternativas():
    from biogeme import models
    from biogeme.nests import NestsForNestedLogit, OneNestForNestedLogit
    # Utilidades sintéticas asimétricas: verifica la escala del nido con dos ferries.
    v = [-2.3, -1.7, -2.1]
    for lam in [.5, .7, .9, 1]:
        nests = NestsForNestedLogit(choice_set=[1, 2, 3], tuple_of_nests=(
            OneNestForNestedLogit(1, [1], 'tierra'),
            OneNestForNestedLogit(1/lam, [2, 3], 'lago')))
        expected = [models.nested(dict(enumerate(v, 1)), {1: 1, 2: 1, 3: 1}, nests, j).get_value() for j in [1, 2, 3]]
        actual, _ = logit_anidado(v, lam)
        assert np.allclose(actual, expected, atol=1e-12)
