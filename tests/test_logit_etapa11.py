import importlib.util
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd
from scipy.special import expit
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import modelo_biogeme as model
sp=importlib.util.spec_from_file_location('etapa11',ROOT/'scripts/11_calibrar_logit.py');stage=importlib.util.module_from_spec(sp);sp.loader.exec_module(stage)


class LogitEtapa11(unittest.TestCase):
    def setUp(self):
        self.data=pd.DataFrame(dict(c1=[1.,2.,3.,4.],c2=[2.,3.,1.,1.],t1=[4.,4.,5.,5.],t2=[2.,2.,2.,2.],
            e1=[0.,0.,0.,0.],e2=[3.,3.,5.,5.],a1=[0.,0.,0.,0.],a2=[1.,1.,1.,1.],choice=[1,2,1,2],weight=[1.,2.,1.,2.]))
        self.params=dict(ASC_barcaza=.3,beta_c=-.2,beta_t=-.3,beta_e=-.4,beta_a=-.5)

    def test_cuatro_componentes_no_tiempo_unico(self):
        p=model.probabilidades(self.data,self.params)
        d=self.data.iloc[0]
        delta=.3-.2*(d.c2-d.c1)-.3*(d.t2-d.t1)-.4*(d.e2-d.e1)-.5*(d.a2-d.a1)
        self.assertAlmostEqual(p.iloc[0],expit(delta))

    def test_biogeme_lambda_singleton_convencion_inversa(self):
        from biogeme import models
        from biogeme.nests import NestsForNestedLogit,OneNestForNestedLogit
        for lam in [.5,.7,.9]:
            n=NestsForNestedLogit(choice_set=[1,2],tuple_of_nests=(OneNestForNestedLogit(1,[1]),OneNestForNestedLogit(1/lam,[2])))
            p=models.nested({1:0,2:.4},{1:1,2:1},n,2).get_value()
            self.assertAlmostEqual(p,expit(.4),places=12)

    def test_ASC_calibra_cuota_ponderada_sin_fabricar_elecciones(self):
        params=stage.score_ASC(self.data,{k:v for k,v in self.params.items() if k!='ASC_barcaza'})
        self.assertAlmostEqual(np.average(model.probabilidades(self.data,params),weights=self.data.weight),np.average(self.data.choice.eq(2),weights=self.data.weight),places=10)
        self.assertEqual(self.data.choice.to_list(),[1,2,1,2])

    def test_ASC_condicional_absorbe_tiempo_constante(self):
        p1=stage.score_ASC(self.data,self.params)
        second=self.data.copy();second.t2+=.25
        p2=stage.score_ASC(second,self.params)
        np.testing.assert_allclose(model.probabilidades(self.data,p1),model.probabilidades(second,p2),atol=1e-12)

    def test_monedas_escaladas_consistentes(self):
        p1=model.probabilidades(self.data,self.params)
        d=self.data.copy();d.c1*=10000;d.c2*=10000
        pars=dict(self.params,beta_c=self.params['beta_c']/10000)
        np.testing.assert_allclose(p1,model.probabilidades(d,pars),atol=1e-14)


if __name__=='__main__':unittest.main()
