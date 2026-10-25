import importlib.util
from pathlib import Path
import os,sys,tempfile,unittest
import numpy as np
import pandas as pd
from scipy.special import expit
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import modelo_biogeme_11b as model
sp=importlib.util.spec_from_file_location('etapa11b',ROOT/'scripts/11b_recalibrar_logit.py');stage=importlib.util.module_from_spec(sp);sp.loader.exec_module(stage)


class Recalibracion11B(unittest.TestCase):
    def test_escalas_y_valor_tiempo(self):
        for vst,bt in [(5000,-.1),(10000,-.2),(15000,-.3)]:
            p=model.coeficientes(-.00002,vst,1.5,1.5)
            self.assertAlmostEqual(p['beta_c'],-.2)
            self.assertAlmostEqual(p['beta_t'],bt)
            self.assertAlmostEqual(p['beta_a'],1.5*bt)
            self.assertAlmostEqual(p['beta_e'],1.5*bt)
            self.assertAlmostEqual(p['beta_t']/(p['beta_c']/10000),vst)

    def test_sensibilidades_un_factor_y_no_muestras_extra(self):
        import json
        cfg=json.loads((ROOT/'data/templates/config_calibracion_logit_11b.json').read_text())
        scenarios=list(stage.escenarios(cfg));self.assertEqual(len(scenarios),9)
        for s in scenarios[1:]:
            self.assertEqual(sum(s[k]!=scenarios[0][k] for k in ['VST','ra','re','lam']),1)

    def test_unidades_economicas_separadas(self):
        import json
        cfg=json.loads((ROOT/'data/templates/config_calibracion_logit_11b.json').read_text())
        self.assertIn('persona-h',cfg['unidades_decision']['PEATON'])
        self.assertIn('vehiculo-h',cfg['unidades_decision']['VL'])
        self.assertIn('camion',cfg['unidades_decision']['CAM'])

    def test_proxy_biogeme_sin_elecciones_personales_ficticias(self):
        d=pd.DataFrame({f'{x}{j}':[0.,0.,0.] for x in ['c','t','e','a'] for j in [1,2]})
        d['weight']=[1.,2.,1.];d['cuota_aproximada_barcaza']=[.1,.2,.7]
        target=np.average(d.cuota_aproximada_barcaza,weights=d.weight)
        old=Path.cwd()
        with tempfile.TemporaryDirectory(prefix='test-logit-11b-') as td:
            try:
                os.chdir(td)
                pars,diag=model.calibrar_ASC(d,model.coeficientes(-.00002,10000,1.5,1.5),'proxy_sintetico',proxy=True)
            finally:os.chdir(old)
        self.assertTrue(diag['convergio']);self.assertEqual(diag['SE_condicional'],{})
        self.assertNotIn('choice',d)
        self.assertAlmostEqual(expit(pars['ASC_barcaza']),target,places=5)


if __name__=='__main__':unittest.main()
