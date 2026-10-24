"""Escenarios de captación CONDICIONALES a flujos de entrada validados.

NO es logit, NO es modelo de demanda inducida, NO deriva flujos diarios de encuestas.
La tasa elegida es un supuesto explícito de redistribución, no coeficiente estimado.
"""
from __future__ import annotations
import pandas as pd

CAMPOS = ["temporada", "sentido", "segmento", "flujo_lago_dia",
          "flujo_tierra_elegible_dia", "dias_temporada", "estado_fuente", "fuente_y_metodo"]
CAPTACIONES = (0.10, 0.25, 0.50)


def simular_captacion(base: pd.DataFrame, tasas=CAPTACIONES) -> pd.DataFrame:
    """Retorna redistribución por escenarios, sin inventar tierra desconocida.

    El cálculo supone igual tasa de captación para lago y tierra *solo si ambos
    flujos están disponibles*. Es una prueba de sensibilidad, no elección observada.
    """
    falta = sorted(set(CAMPOS) - set(base.columns))
    if falta:
        raise ValueError(f"Faltan columnas del esquema: {falta}")
    x = base.copy()
    for col in ["flujo_lago_dia", "flujo_tierra_elegible_dia", "dias_temporada"]:
        x[col] = pd.to_numeric(x[col], errors="coerce")
        if (x[col].dropna() < 0).any():
            raise ValueError(f"No se aceptan valores negativos en {col}")
    if (x["dias_temporada"].dropna() > 366).any():
        raise ValueError("Días de temporada > 366: revisar")
    if x["fuente_y_metodo"].isna().any():
        x["fuente_y_metodo"] = x["fuente_y_metodo"].fillna("")
    if x.duplicated(["temporada", "sentido", "segmento"]).any():
        raise ValueError("Estratos duplicados: revisar antes de sumar resultados")
    x = x[x["flujo_lago_dia"].notna()].copy()
    if x.empty:
        raise ValueError("No hay flujos lacustres por día acreditados o supuestos explícitos de entrada. "
                         "Las encuestas por sí solas no sirven como demanda.")
    if (x["estado_fuente"].astype(str).str.strip().str.lower() == "pendiente").any():
        raise ValueError("Indica el estado de la fuente para cada flujo ingresado: observado, calculado o supuesto")
    salidas = []
    for tasa in tasas:
        if not 0 <= tasa <= 1:
            raise ValueError("La tasa de captura debe estar entre 0 y 1")
        y = x.copy()
        y["captacion_escenario"] = tasa
        y["desviados_del_lago_dia"] = y["flujo_lago_dia"] * tasa
        y["desviados_de_tierra_dia"] = y["flujo_tierra_elegible_dia"] * tasa
        y["captacion_total_dia"] = y["desviados_del_lago_dia"] + y["desviados_de_tierra_dia"]
        y["desviados_del_lago_periodo"] = y["desviados_del_lago_dia"] * y["dias_temporada"]
        y["captacion_total_periodo"] = y["captacion_total_dia"] * y["dias_temporada"]
        y["alcance_resultado"] = y["flujo_tierra_elegible_dia"].isna().map(
            {True: "solo_desvio_lago_no_demanda_total", False: "lago_y_tierra_escenario_no_calibrado"}
        )
        salidas.append(y)
    return pd.concat(salidas, ignore_index=True)
