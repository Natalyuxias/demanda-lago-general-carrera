"""Respuesta al costo privado por perfil, sin alterar ASC ni estimar betas."""
import numpy as np
from demanda.proyecto import logit_anidado


def respuesta_perfiles(xs, xp, pesos, betas, asc, epsilon, lam=.7,
                       max_reduccion=.95, formula='constante', factor_cg=1, delta_asc_nuevo=0):
    """C,h_viaje,h_horario,h_acceso. Previo/desembarque ya están en viaje.

    Los pesos de inducción son w*(multiplicador-1); no se reemplazan por w.
    El CG positivo excluye ASC/entropía; no es el negativo del logsum.
    """
    xs, xp, w, b = map(lambda x: np.asarray(x, float), (xs, xp, pesos, betas))
    if not 0 < max_reduccion < 1 or factor_cg <= 0 or epsilon > 0:
        raise ValueError('Escala, límite o elasticidad no admisible')
    if xs.shape != (len(w), 2, 4) or xp.shape != (len(w), 3, 4):
        raise ValueError('Dimensiones de perfiles inválidas')
    if not all(np.isfinite(a).all() for a in (xs, xp, w, b)):
        raise ValueError('Perfil incompleto: debe quedar fuera de la elección')
    if (w < 0).any() or not np.isclose(w.sum(), 1) or (b >= 0).any():
        raise ValueError('Pesos o coeficientes inválidos')
    ps, pp, ls, lp = [], [], [], []
    for a, z in zip(xs, xp):
        p, l = logit_anidado(a @ b + [0, asc], lam)
        q, k = logit_anidado(z @ b + [0, asc, asc+delta_asc_nuevo], lam)
        ps.append(p); pp.append(q); ls.append(l); lp.append(k)
    ps, pp = np.array(ps), np.array(pp)
    # beta_t/beta_c y restantes cocientes son valores privados positivos del tiempo.
    cg_por_alt = xs @ (b / b[0])
    cg = (ps * cg_por_alt).sum(axis=1) * factor_cg
    if (cg <= 0).any():
        raise ValueError('Referencia económica no positiva')
    beneficio = (np.asarray(lp)-np.asarray(ls))/abs(b[0])
    raw = beneficio/cg
    usado = np.minimum(raw, max_reduccion)
    cociente = 1-usado
    if formula == 'constante':
        mult = np.maximum(1, cociente**epsilon)
    elif formula == 'local':
        mult = 1 + np.maximum(0, -epsilon*usado)
    else:
        raise ValueError('Fórmula desconocida')
    avg = lambda x: np.average(x, axis=0, weights=w)
    factor_media = max(1, (1-min(float(avg(beneficio))/float(avg(cg)),max_reduccion))**epsilon)
    return dict(p_sbo=avg(ps), p_proyecto=avg(pp),
                inducida_por_unidad=avg((mult-1)[:,None]*pp),
                factor_total=float(avg(mult)), factor_transformacion_media=factor_media,
                cg_referencia=float(avg(cg)), beneficio=float(avg(beneficio)),
                logsum_sbo=float(avg(ls)), logsum_proyecto=float(avg(lp)),
                r_media=float(avg(raw)), r_max=float(raw.max()),
                cociente_min=float(cociente.min()), n_perfiles=len(w),
                n_limitados=int((raw>max_reduccion).sum()),
                peso_limitado=float(w[raw>max_reduccion].sum()),
                peso_cociente_invalido_sin_limite=float(w[raw>=1].sum()))
