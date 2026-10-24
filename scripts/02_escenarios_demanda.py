"""Estima SOLO captación potencial condicional a demanda base diaria suministrada.

No convierte microdatos en demanda por sí solo. Usa por defecto escenario 10/25/50 %.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from demanda.escenarios import simular_captacion


def main():
    parser = argparse.ArgumentParser(description="Escenarios de desviación a la nueva ruta (NO LOGIT)")
    parser.add_argument("--input", required=True, help="CSV agregado basado en data/templates/flujos_base.csv")
    args = parser.parse_args()
    inp = pd.read_csv(args.input)
    res = simular_captacion(inp)
    out = ROOT / "outputs" / "tables" / "escenarios_captacion.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"Se generaron {len(res)} filas de escenarios en {out}")
    print("AVISO: los porcentajes no provienen de calibración; si no hay tierra elegible, "
          "la captación total permanece vacía. No incluye demanda inducida.")


if __name__ == "__main__":
    main()
