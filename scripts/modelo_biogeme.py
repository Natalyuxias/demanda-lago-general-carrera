"""Utilidad EVALSO con cuatro betas. Biogeme3.3.2; sin cruce futuro.

Bibliografia tecnica: https://biogeme.epfl.ch/sphinx/auto_examples/programmers/plot_models.html
lambda EVALSO en(0,1]; Biogeme usa mu_nido=1/lambda con escala superior1.
Con un elemento en cada nido, el logit jerarquico se reduce algebraicamente
al logit de dos alternativas, conservando C,viaje,horario,acceso por separado.
"""
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/mpl-logit')
os.environ.setdefault('JAX_ENABLE_X64','True')
import numpy as np
import pandas as pd
from scipy.special import expit
from biogeme.biogeme import BIOGEME
from biogeme.database import Database
from biogeme.expressions import Beta,Variable
from biogeme.nests import NestsForNestedLogit,OneNestForNestedLogit
from biogeme import models
from biogeme.results_processing import get_pandas_estimated_parameters

PARAMS=['ASC_barcaza','beta_c','beta_t','beta_e','beta_a']
COLS=['dc','dt','de','da']


def utilidades(datos,params):
    """C ya esta en10000CLP, tiempos en horas. ASC tierra0."""
    v={}
    for j in [1,2]:
        v[j]=(params['ASC_barcaza'] if j==2 else 0)+sum(params[p]*datos[f'{x}{j}'] for p,x in [('beta_c','c'),('beta_t','t'),('beta_e','e'),('beta_a','a')])
    return v


def probabilidades(datos,params,lam=.7):
    # Dos nidos singleton: independiente de lambda. No usar lambda para reescalar V.
    if not 0<lam<=1:raise ValueError('lambda debe estar en(0,1]')
    v=utilidades(datos,params);return expit(v[2]-v[1])


def diseno(datos,free):
    x=pd.DataFrame({'ASC_barcaza':np.ones(len(datos)),'beta_c':datos.c2-datos.c1,'beta_t':datos.t2-datos.t1,'beta_e':datos.e2-datos.e1,'beta_a':datos.a2-datos.a1})[free].to_numpy(float)
    scaled=x/np.maximum(np.linalg.norm(x,axis=0),1e-15)
    return int(np.linalg.matrix_rank(scaled)),np.linalg.svd(scaled,compute_uv=False).tolist()


def estimar(datos,fijos,libres,nombre,lam=.7):
    """Pesos normalizados externamente. SE condicionales de modelo, no diseño."""
    needed=['choice','weight']+[f'{x}{j}' for j in [1,2] for x in ['c','t','e','a']]
    clean=datos[needed].astype(float).copy()
    if not np.isfinite(clean.to_numpy()).all():raise ValueError('Faltantes en atributos/peso de estimacion')
    db=Database(nombre,clean)
    start={'ASC_barcaza':0,'beta_c':-.2,'beta_t':-.2,'beta_e':-.2,'beta_a':-.2}
    betas={}
    for p in PARAMS:
        lb,ub=(-80,80) if p=='ASC_barcaza' else (-20,-1e-8)
        betas[p]=Beta(p,fijos.get(p,start[p]),lb,ub,0 if p in libres else 1)
    v={}
    for j in [1,2]:
        v[j]=(betas['ASC_barcaza'] if j==2 else 0)+sum(betas[p]*Variable(f'{x}{j}') for p,x in [('beta_c','c'),('beta_t','t'),('beta_e','e'),('beta_a','a')])
    nests=NestsForNestedLogit(choice_set=[1,2],tuple_of_nests=(OneNestForNestedLogit(1,[1],'terrestre'),OneNestForNestedLogit(1/lam,[2],'lacustre')))
    logp=models.lognested(v,{1:1,2:1},nests,Variable('choice'))
    b=BIOGEME(db,{'log_like':logp,'weight':Variable('weight')},generate_html=False,generate_yaml=False,save_iterations=False,number_of_threads=1)
    b.model_name=nombre;r=b.estimate()
    vals={**fijos,**r.get_beta_values()};tab=get_pandas_estimated_parameters(r)
    se={row['Name']:row['Robust std err.'] for _,row in tab.iterrows()}
    rank,svals=diseno(datos,libres)
    return vals,dict(log_likelihood=float(r.final_loglikelihood),convergio=bool(r.algorithm_has_converged),rango=rank,columnas=len(libres),
                    singulares=svals,SE_condicional=se,gradiente=float(r.gradient_norm),libres=libres,betas=vals)


if __name__=='__main__':
    import argparse,json
    p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--segmento',default='VL');p.add_argument('--ponderacion',default='CC_PC1_laboral')
    args=p.parse_args();d=pd.read_csv(args.base);d=d[d.segmento.eq(args.segmento)&d.ponderacion.eq(args.ponderacion)&d.apta_estimacion.eq(True)]
    vals,diagnostic=estimar(d,{'beta_c':-.2,'beta_t':-.2,'beta_a':-.2},['ASC_barcaza','beta_e'],'reproducir_condicional')
    print(json.dumps(diagnostic,indent=2))
