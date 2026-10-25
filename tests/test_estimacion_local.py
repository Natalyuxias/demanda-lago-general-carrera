"""Pruebas sintéticas ejecutables sin pytest ni datos reales."""
import importlib.util
from pathlib import Path
import math
import unittest

SPEC=importlib.util.spec_from_file_location('estimacion',Path(__file__).resolve().parents[1]/'scripts/03_estimar_demanda_local.py')
m=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)

class EstimacionLocalTests(unittest.TestCase):
    def test_no_expandir_celda_sin_muestra(self):
        self.assertTrue(math.isnan(m.repartir(100,0,0)))

    def test_conservacion_unidades_vehiculares(self):
        self.assertAlmostEqual(m.repartir(70,2,7)+m.repartir(70,5,7),70)

    def test_rechaza_participacion_invalida(self):
        with self.assertRaises(ValueError):m.repartir(70,8,7)

    def test_anualizacion_no_duplica_dias(self):
        # Perfil constante y mismo invierno: se conserva el total de un año.
        self.assertEqual(m.anualizar(dict(Verano=2,Primavera=2,Normal=2),dict(Verano=90,Primavera=91,Normal=92,Invierno=92),1),730)

    def test_anualizacion_propaga_faltante(self):
        self.assertTrue(math.isnan(m.anualizar(dict(Verano=float('nan'),Primavera=2,Normal=2),dict(Verano=90,Primavera=91,Normal=92,Invierno=92),1)))

    def test_sentido_no_se_invierte_por_tildes(self):
        self.assertEqual(m.sentido('De Pto. Ibáñez a Chile Chico'),'Ibanez a Chile Chico')
        self.assertEqual(m.sentido('De Chile Chico a Puerto Ibáñez'),'Chile Chico a Ibanez')

if __name__=='__main__':unittest.main()
