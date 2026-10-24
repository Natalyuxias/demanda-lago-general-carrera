"""Costos privados: fórmula 5.2 del Informe 2 EVALSO.

Este módulo NO provee los parámetros ni acredita su procedencia.
"""
from __future__ import annotations
import pandas as pd

COMPONENTES_H = ["t_acceso_h", "t_viaje_h", "t_horario_h", "t_embarque_h"]


def costo_generalizado_privado(df: pd.DataFrame) -> pd.Series:
    """CLP/viaje = C privado CLP/viaje + VST CLP/h * sum(tiempos h).

    Exige que tarifa y costos sean privados y VST sea de la MISMA unidad de decisión
    (persona/vehículo) para prevenir dobles conteos.
    """
    requeridas = ["c_privado_clp", "vst_clp_h", *COMPONENTES_H]
    faltan = [c for c in requeridas if c not in df.columns]
    if faltan:
        raise ValueError(f"Faltan columnas: {faltan}")
    a = df[requeridas].apply(pd.to_numeric, errors="raise")
    if a.isna().any().any():
        raise ValueError("Existen valores faltantes: corregir o definir escenario explícito")
    if (a < 0).any().any():
        raise ValueError("Existen costos/VST/tiempos negativos")
    return a["c_privado_clp"] + a["vst_clp_h"] * a[COMPONENTES_H].sum(axis=1)
