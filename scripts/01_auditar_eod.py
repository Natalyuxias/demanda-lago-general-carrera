"""Primer paso: leer microdatos y generar diagnósticos NO expandidos."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from demanda.preparacion import leer_eod, tabla_no_expandida


def main() -> None:
    parser = argparse.ArgumentParser(description="Auditar ARISTO BBDD-1 y BBDD-2")
    parser.add_argument("--eod", required=True, help="Ruta a Base de datos agregada.xlsx")
    args = parser.parse_args()
    df = leer_eod(args.eod)
    out = ROOT / "outputs" / "tables"
    out.mkdir(parents=True, exist_ok=True)

    reporte = {
        "registros_validos_con_llave": len(df),
        "registros_cruce_actual": int(df["interceptado_en_cruce_actual"].sum()),
        "registros_od_prueba_inicial": int(df["od_prueba_inicial"].sum()),
        "registros_od_prueba_en_cruce": int((df["od_prueba_inicial"] & df["interceptado_en_cruce_actual"]).sum()),
    }
    pd.DataFrame([reporte]).to_csv(out / "control_eod.csv", index=False, encoding="utf-8-sig")
    tabla_no_expandida(df[df["od_prueba_inicial"]]).to_csv(
        out / "od_muestral_prueba.csv", index=False, encoding="utf-8-sig"
    )
    # Evita exportar nombre, dirección, teléfonos o geocoordenadas privadas.
    columnas = ["ID 2", "Nombre origen", "Nombre destino", "Versión", "Lugar encuestado",
                "temporada_analisis", "interceptado_en_cruce_actual", "estado_eleccion"]
    if "Tipo usuario" in df:
        columnas.append("Tipo usuario")
    df.loc[df["od_prueba_inicial"], columnas].to_csv(
        out / "candidatos_no_expandidos.csv", index=False, encoding="utf-8-sig"
    )
    print("\nCONTROL DE CARGA (no es estimación de demanda):")
    for k, v in reporte.items():
        print(f"- {k}: {v}")
    print(f"\nArchivos de diagnóstico generados en: {out}")
    print("ADVERTENCIA: falta expansión y clasificación confirmada de las rutas terrestres.")


if __name__ == "__main__":
    main()
