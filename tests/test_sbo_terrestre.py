"""Datos sinteticos: restricciones de capacidad, operacion y evidencia de rutas."""
from pathlib import Path
import importlib.util,json,math,sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from demanda.capacidad import (limite_ciclos_dia,horario_ciclos,frecuencia_minima,
                              evaluar,preparar_cambio_costo)
spec=importlib.util.spec_from_file_location('rutas',ROOT/'scripts/05_investigar_demanda_terrestre.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

class CapacidadTests(unittest.TestCase):
    def test_ciclo_incluye_maniobra_final(self):
        self.assertEqual(limite_ciclos_dia(2,.5,12),2)
        self.assertEqual(limite_ciclos_dia(8/3,.5,12),1)

    def test_itinerario_rechaza_ventana_corta(self):
        self.assertFalse(horario_ciclos(10,10,8/3,.5,12)[1])
        self.assertTrue(horario_ciclos(10,10,2,.5,12)[1])

    def test_conservacion_pasajeros_y_ml_sin_mezclar(self):
        x=evaluar(200,100,1,1,80,252,250,300)
        self.assertAlmostEqual(x['ocupacion_ml'],200/332)
        self.assertAlmostEqual(x['ocupacion_pax'],100/550)

    def test_doble_capacidad_no_crea_demanda(self):
        a=evaluar(200,100,1,1,80,252,250,300)
        b=evaluar(200,100,2,2,80,252,250,300)
        self.assertAlmostEqual(a['ocupacion_ml']/2,b['ocupacion_ml'])

    def test_faltante_no_produce_frecuencia(self):
        self.assertIsNone(frecuencia_minima(math.nan,100,(80,252,250,300),.8,1,7))

    def test_faltante_no_declara_saturacion(self):
        self.assertIsNone(evaluar(math.nan,100,1,1,80,252,250,300)['cumple_media_o_punta_condicional'])

    def test_minimo_no_supera_limite_operacional(self):
        self.assertIsNone(frecuencia_minima(10000,100,(80,252,250,300),.8,1,2))

    def test_desfase_no_se_inventa(self):
        self.assertTrue(math.isnan(preparar_cambio_costo()))

    def test_cuatro_estaciones_y_otono_dos_regimenes(self):
        c=json.loads((ROOT/'data/templates/config_sbo.json').read_text())
        self.assertEqual(len(c['estaciones']),4)
        self.assertEqual(c['frecuencia_historica_por_mes']['3'],11)
        self.assertEqual(c['frecuencia_historica_por_mes']['5'],8)
        self.assertIsNone(c['campana_por_mes']['3'])

class RutasTests(unittest.TestCase):
    cfg={'sin_transbordador_explicito':['ninguno'],'fronteras_argentina':['jeinimeni']}
    def check(self,place,kind,ferry):
        return r.clasificar({'Lugar encuestado':place,'Lugar de Encuesta':kind,'ferry':ferry},['ferry'],[],self.cfg)

    def test_carretera_sin_respuesta_no_es_tierra(self):
        self.assertEqual(self.check('Cerro Castillo','Carretera',None)['clase_ruta'],'ruta_desconocida')

    def test_negativa_explicita_es_tierra_declarada(self):
        self.assertEqual(self.check('Cerro Castillo','Carretera','Ninguno')['clase_ruta'],'tierra_confirmada_por_declaracion_sin_transbordadores')

    def test_declaracion_lago_en_carretera_no_confirmada(self):
        x=self.check('Cerro Castillo','Carretera','Pto. Ibáñez - Chile Chico')
        self.assertEqual(x['clase_ruta'],'ruta_desconocida')
        self.assertTrue(x['lago_declarado_no_confirmado'])

    def test_interceptacion_lago_confirma(self):
        self.assertEqual(self.check('Ruta Pto. Ibáñez - Chile Chico','Transbordador',None)['clase_ruta'],'barcaza_confirmada_interceptacion')

    def test_argentina_no_borra_evidencia_tierra(self):
        x=self.check('Jeinimeni','Paso fronterizo','Ninguno')
        self.assertTrue(x['argentina_interceptacion'])
        self.assertEqual(x['clase_ruta'],'tierra_confirmada_por_declaracion_sin_transbordadores')

if __name__=='__main__':unittest.main()
