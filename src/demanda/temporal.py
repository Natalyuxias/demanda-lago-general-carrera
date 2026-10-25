"""Ventanas horarias y factores temporales con cobertura explícita."""
import math


def suma_ventana(perfil, inicio, fin):
    """Integrar horas completas; una hora ausente hace desconocida la ventana."""
    if not (0 <= inicio < fin <= 24):
        raise ValueError('Ventana inválida')
    valores = [perfil.get(h, math.nan) for h in range(inicio, fin)]
    if not all(math.isfinite(v) and v >= 0 for v in valores):
        return math.nan
    return sum(valores)


def cociente(numerador, denominador):
    if not all(math.isfinite(v) for v in (numerador, denominador)) or denominador <= 0:
        return math.nan
    return numerador / denominador


def factor_hibrido(q12, q10, coeficiente_12_24):
    """Sensibilidad: coeficiente 12→24 multiplicado por relación observada 12/10.

    No convierte un perfil parcial en observación de 24 horas. La transferencia de
    localidad, estación, sentido y clase es un supuesto del llamador.
    """
    if not math.isfinite(coeficiente_12_24) or coeficiente_12_24 < 1:
        return math.nan
    ratio = cociente(q12, q10)
    if not math.isfinite(ratio):
        return math.nan
    if ratio < 1 - 1e-12:
        raise ValueError('La ventana de 10 horas debe estar contenida en la de 12 horas')
    return coeficiente_12_24 * ratio
