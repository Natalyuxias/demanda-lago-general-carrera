"""ASC condicionada a cuatro betas fijos. Biogeme3.3.2.

Modelos actuales de dos nidos singleton, escala superior1 y mu=1/lambda.
La funcion proxy usa cuotas fraccionarias agregadas, NO elecciones personales
inventadas. No interpreta la curvatura del objetivo proxy como error estadistico.
"""
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/mpl-logit')
os.environ.setdefault('JAX_ENABLE_X64','True')
from pathlib import Path
import sys
for parent in Path(__file__).resolve().parents:
    if (parent/'scripts/modelo_biogeme.py').exists():
        sys.path.insert(0,str(parent/'scripts'));break
import numpy as np
from biogeme.biogeme import BIOGEME
from biogeme.database import Database
from biogeme.expressions import Beta,Variable
from biogeme.nests import NestsForNestedLogit,OneNestForNestedLogit
from biogeme import models
from modelo_biogeme import estimar,probabilidades


def coeficientes(beta_c_por_CLP,vst,ra,re):
    """beta_c escala interna por10000CLP. VST CLP/h por unidad de decision."""
    if beta_c_por_CLP>=0 or min(vst,ra,re)<=0:raise ValueError('Signos o relaciones no admisibles')
    bt=beta_c_por_CLP*vst
    return dict(beta_c=beta_c_por_CLP*10000,beta_t=bt,beta_a=ra*bt,beta_e=re*bt)


def calibrar_ASC(datos,pendientes,nombre,lam=.7,proxy=False):
    if not 0<lam<=1:raise ValueError('lambda debe estar en(0,1]')
    if not proxy:
        return estimar(datos,pendientes,['ASC_barcaza'],nombre,lam)
    cols=[f'{x}{j}' for x in ['c','t','e','a'] for j in [1,2]]
    df=datos[cols+['weight','cuota_aproximada_barcaza']].astype(float).copy()
    df['weight']=df.weight*len(df)/df.weight.sum()
    if not np.isfinite(df.to_numpy()).all() or not df.cuota_aproximada_barcaza.between(0,1).all():raise ValueError('Insumo proxy invalido')
    db=Database(nombre,df)
    asc=Beta('ASC_barcaza',0,-80,80,0)
    v={j:(asc if j==2 else 0)+sum(pendientes[p]*Variable(f'{x}{j}') for p,x in [('beta_c','c'),('beta_t','t'),('beta_e','e'),('beta_a','a')]) for j in [1,2]}
    nests=NestsForNestedLogit(choice_set=[1,2],tuple_of_nests=(OneNestForNestedLogit(1,[1],'terrestre'),OneNestForNestedLogit(1/lam,[2],'lacustre')))
    s=Variable('cuota_aproximada_barcaza')
    # Fracciones del objetivo proxy. No son una columna CHOICE observada.
    objective=s*models.lognested(v,{1:1,2:1},nests,2)+(1-s)*models.lognested(v,{1:1,2:1},nests,1)
    b=BIOGEME(db,{'log_like':objective,'weight':Variable('weight')},generate_html=False,generate_yaml=False,save_iterations=False,number_of_threads=1)
    b.model_name=nombre;r=b.estimate()
    params=dict(pendientes,ASC_barcaza=r.get_beta_values()['ASC_barcaza'])
    return params,dict(convergio=bool(r.algorithm_has_converged),objetivo_proxy=float(r.final_loglikelihood),SE_condicional={},
        metodo='Biogeme: calibracion de constante por cross-entropy de cuotas proxy; NO MLE de personas')
