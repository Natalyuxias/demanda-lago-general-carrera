import math
import unittest
from demanda.preparacion_logit import homologar,tiempo_vehiculo,tarifa_personas,tiempo_servicio_completo


class PreparacionLogit(unittest.TestCase):
    def test_homologacion_con_indices_no_variacion_redondeada(self):
        self.assertAlmostEqual(homologar(10000,104.45,109.26),10000*109.26/104.45)
        self.assertTrue(math.isnan(homologar(10000,None,109.26)))

    def test_anticipacion_y_desembarque_no_son_acceso_duplicado(self):
        fisico,indice=tiempo_vehiculo(1.5,2,2,.5,5.25)
        self.assertEqual(fisico,6)
        self.assertEqual(indice,11.25)

    def test_servicio_integrado_no_repite_operaciones(self):
        self.assertEqual(tiempo_servicio_completo(6),6)
        self.assertEqual(tiempo_servicio_completo(6,.2),6.2)

    def test_tarifa_distingue_conductor_y_exenciones(self):
        self.assertEqual(tarifa_personas(3,2550,True),5100)
        self.assertEqual(tarifa_personas(3,2550,False),7650)
        self.assertEqual(tarifa_personas(3,2550,True,True),0)
        self.assertEqual(tarifa_personas(3,2550,False,True),2550)

    def test_faltante_no_es_cero(self):
        self.assertTrue(math.isnan(tarifa_personas(math.nan,2550,True)))
        self.assertTrue(math.isnan(tiempo_vehiculo(math.nan,2,1,.5,5.25)[0]))


if __name__=='__main__':unittest.main()
