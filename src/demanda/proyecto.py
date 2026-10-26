"""Aplicación del logit anidado, sin estimación ni recalibración."""
import numpy as np
from scipy.special import logsumexp


def logit_anidado(utilidades, lambda_lago=.7, disponibles=None):
    """Orden: tierra, ferry existente, ferry nuevo; escala superior 1.

    lambda es la disimilitud (mu Biogeme=1/lambda). Una disponibilidad
    desconocida debe resolverse antes de llamar; NaN de utilidad se propaga.
    """
    v = np.asarray(utilidades, dtype=float)
    if v.ndim != 1 or len(v) not in (2, 3):
        raise ValueError('Se esperan dos o tres alternativas')
    if not 0 < lambda_lago <= 1:
        raise ValueError('lambda fuera de (0,1]')
    av = np.ones(len(v), dtype=bool) if disponibles is None else np.asarray(disponibles, dtype=bool)
    if av.shape != v.shape or not av.any():
        raise ValueError('Disponibilidad inválida')
    if not np.isfinite(v[av]).all():
        return np.full(len(v), np.nan), np.nan
    v = np.where(av, v, -np.inf)
    lago = logsumexp(v[1:] / lambda_lago)
    superior = logsumexp([v[0], lambda_lago * lago])
    p = np.zeros(len(v))
    p[0] = np.exp(v[0] - superior)
    if np.isfinite(lago):
        p[1:] = np.exp(v[1:] / lambda_lago - lago + lambda_lago * lago - superior)
    return p, float(superior)


def desviar(total, p_sbo, p_proyecto):
    """Pérdidas netas de las rutas existentes; no transiciones individuales."""
    s = np.asarray(p_sbo, float)
    p = np.asarray(p_proyecto, float)
    if len(s) != 2 or len(p) != 3:
        raise ValueError('Dimensiones inválidas')
    if not np.isfinite(s).all() or not np.isfinite(p).all():
        return np.full(2, np.nan)
    if not np.isclose(s.sum(), 1) or not np.isclose(p.sum(), 1):
        raise ValueError('Probabilidades sin normalizar')
    perdida = s - p[:2]
    if (perdida < -1e-10).any() or not np.isclose(perdida.sum(), p[2]):
        raise ValueError('No se conserva demanda o se incumple regularidad')
    return total * perdida
