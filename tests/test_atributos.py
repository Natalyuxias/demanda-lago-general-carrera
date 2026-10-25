import unittest
import pandas as pd
from demanda.atributos import calendario_semanal,grafo_vial,camino_minimo,comprobar_secuencia,tiempos_aditivos


class Atributos(unittest.TestCase):
    def test_calendario_incluye_intervalo_entre_semanas(self):
        x=calendario_semanal([(0,8),(6,16)])
        self.assertEqual(x['intervalos_h'],[152,16])
        self.assertEqual(sum(x['intervalos_h']),168)
        self.assertEqual(x['H_media_intervalos_h'],84)
        self.assertGreater(x['H_ponderado_tiempo_h'],84)

    def test_salidas_duplicadas_no_equivalen_mas_frecuencia(self):
        with self.assertRaises(ValueError):calendario_semanal([(1,8),(1,8)])

    def test_no_duplicar_conduccion_acceso(self):
        x=tiempos_aditivos(1.5,2,True)
        self.assertEqual(x['t_acceso_modelo_h']+x['t_viaje_modelo_h'],3.5)
        y=tiempos_aditivos(6,0,False)
        self.assertEqual(y['t_acceso_modelo_h']+y['t_viaje_modelo_h'],6)

    def test_velocidades_CAM_propias_y_exclusion_conectores(self):
        d=pd.DataFrame([
            dict(ID_Arco=1,Nodo_A=1,Nodo_B=2,LONGITUD=10,Clave='I',REGI_N='Aysén',**{'VEL VL':100,'VEL VP':10}),
            dict(ID_Arco=2,Nodo_A=1,Nodo_B=3,LONGITUD=10,Clave='I',REGI_N='Aysén',**{'VEL VL':20,'VEL VP':50}),
            dict(ID_Arco=3,Nodo_A=3,Nodo_B=2,LONGITUD=10,Clave='I',REGI_N='Aysén',**{'VEL VL':20,'VEL VP':50}),
            dict(ID_Arco=4,Nodo_A=1,Nodo_B=2,LONGITUD=0,Clave='C',REGI_N='Aysén',**{'VEL VL':0,'VEL VP':0})])
        car=camino_minimo(grafo_vial(d,'VL','Chile'),1,2)
        truck=camino_minimo(grafo_vial(d,'CAM','Chile'),1,2)
        self.assertEqual([e['ID_Arco'] for e in car],[1])
        self.assertEqual([e['ID_Arco'] for e in truck],[2,3])
        comprobar_secuencia(truck,1,2)

    def test_rechaza_itinerario_discontinuo(self):
        with self.assertRaises(ValueError):
            comprobar_secuencia([dict(desde=1,hasta=2,ID_Arco=1),dict(desde=3,hasta=4,ID_Arco=2)],1,4)


if __name__=='__main__':unittest.main()
