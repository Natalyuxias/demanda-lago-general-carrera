import math
import unittest
from demanda.temporal import suma_ventana, factor_hibrido


class ExpansionTemporal(unittest.TestCase):
    def test_perfil_parcial_no_se_convierte_en_observacion24(self):
        perfil={h:10.0 for h in range(7,23)}
        self.assertEqual(suma_ventana(perfil,9,19),100)
        self.assertTrue(math.isnan(suma_ventana(perfil,0,24)))

    def test_ventanas_diferentes_respetan_los_horarios(self):
        perfil={h:float(h+1) for h in range(24)}
        self.assertEqual(suma_ventana(perfil,8,18),135)
        self.assertEqual(suma_ventana(perfil,9,19),145)

    def test_factor12h_requiere_puente_observado(self):
        self.assertAlmostEqual(factor_hibrido(250,200,1.35),1.6875)
        self.assertTrue(math.isnan(factor_hibrido(math.nan,200,1.35)))
        self.assertTrue(math.isnan(factor_hibrido(250,200,math.nan)))

    def test_rechaza_ventanas_no_contenidas(self):
        with self.assertRaises(ValueError):factor_hibrido(100,120,1.35)


if __name__=='__main__':unittest.main()
