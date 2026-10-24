"""Preparación descriptiva de las EOD de ARISTO, SIN expansión ni logit."""

from __future__ import annotations
import re
import unicodedata
from pathlib import Path
import pandas as pd


def normalizar_cadena(x: object) -> str:
    if pd.isna(x):
        return ""
    text = unicodedata.normalize("NFKD", str(x))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.lower().split())


def normalizar_id(series: pd.Series) -> pd.Series:
    """Lee identificadores numéricos/texto con consistencia entre hojas."""
    return series.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)


def leer_eod(ruta: str | Path) -> pd.DataFrame:
    """Conserva todos los válidos de BBDD-2 y los enlaza a BBDD-1 por ID 2.

    No convierte ausencias de rutas declaradas en elecciones terrestres.
    No aplica factores de expansión todavía no auditados.
    """
    ruta = Path(ruta)
    if not ruta.is_file():
        raise FileNotFoundError(f"Archivo no encontrado: {ruta}")
    original = pd.read_excel(ruta, sheet_name="BBDD-1")
    validos = pd.read_excel(ruta, sheet_name="BBDD-2 (solo válidas)")
    for df, nombre in [(original, "BBDD-1"), (validos, "BBDD-2")]:
        if "ID 2" not in df:
            raise ValueError(f"Falta columna 'ID 2' en hoja {nombre}")
        df["ID 2"] = normalizar_id(df["ID 2"])
        if df["ID 2"].isna().any() or df["ID 2"].duplicated().any():
            raise ValueError(f"ID 2 vacío/repetido en {nombre}; revisar antes de unir")

    columnas_necesarias = ["ID 2", "Nombre origen", "Nombre destino"]
    for c in columnas_necesarias:
        if c not in validos:
            raise ValueError(f"Falta columna '{c}' en BBDD-2")
    columnas_extra = ["Tipo usuario", "ID origen", "ID destino"]
    seleccion = [*columnas_necesarias, *(c for c in columnas_extra if c in validos)]
    if "Versión" not in original:
        raise ValueError("No se encontró 'Versión' en BBDD-1; revisar las etiquetas")
    if "Lugar encuestado" not in original:
        raise ValueError("No se encontró 'Lugar encuestado' en BBDD-1")

    base = original.merge(
        validos[seleccion], on="ID 2", how="inner", validate="one_to_one",
        suffixes=("_original", "_normalizada"),
    )
    if len(base) != len(validos):
        raise ValueError("Hay registros normalizados sin registro original; revisar ID 2")

    base["origen_normalizado"] = base["Nombre origen"].map(normalizar_cadena)
    base["destino_normalizado"] = base["Nombre destino"].map(normalizar_cadena)
    base["temporada_analisis"] = (
        base["Versión"].map(normalizar_cadena)
        .replace({"normal": "otono", "otoño": "otono"})
    )
    sitio = base["Lugar encuestado"].map(normalizar_cadena)
    # Identificación conservadora: estar encuestado SOBRE ese transbordador demuestra lago.
    base["interceptado_en_cruce_actual"] = (
        sitio.str.contains("ibanez", regex=False)
        & sitio.str.contains("chile chico", regex=False)
        & sitio.str.contains("ruta", regex=False)
    )
    # Nunca clasificar "sin evidencia lago" como "eligió ruta terrestre".
    base["estado_eleccion"] = "no_verificada"
    base.loc[base["interceptado_en_cruce_actual"], "estado_eleccion"] = "lago_confirmado_interceptacion"

    origen_cc = base["origen_normalizado"].eq("chile chico")
    destino_cc = base["destino_normalizado"].eq("chile chico")
    comparables = base["origen_normalizado"].isin(["coyhaique", "rio ibanez"])
    comparables_dest = base["destino_normalizado"].isin(["coyhaique", "rio ibanez"])
    base["od_prueba_inicial"] = (origen_cc & comparables_dest) | (destino_cc & comparables)
    # Esto NO es una regla final de elegibilidad del proyecto.
    return base


def tabla_no_expandida(base: pd.DataFrame) -> pd.DataFrame:
    """Solo recuentos de encuestas; NO población ni flujo."""
    segmentos = ["origen_normalizado", "destino_normalizado", "temporada_analisis"]
    if "Tipo usuario" in base.columns:
        segmentos.append("Tipo usuario")
    return (
        base.groupby(segmentos, dropna=False)
        .agg(encuestas=("ID 2", "size"), encuestas_cruce=("interceptado_en_cruce_actual", "sum"))
        .reset_index()
        .sort_values("encuestas", ascending=False)
    )
