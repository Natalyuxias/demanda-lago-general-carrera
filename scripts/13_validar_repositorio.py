"""Validar código y selección compartible sin ejecutar estimadores ARISTO.

--indice revisa además los archivos preparados para commit.
No necesita originales: las pruebas de modelos usan fixtures sintéticos aparte.
"""
from pathlib import Path
import argparse,ast,hashlib,importlib.util,json,re,subprocess,sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--indice',action='store_true');args=ap.parse_args()
    checks={}
    paths=list((ROOT/'scripts').glob('*.py'))+list((ROOT/'src').rglob('*.py'))+list((ROOT/'tests').glob('*.py'))
    for p in paths:ast.parse(p.read_text(),filename=str(p))
    checks['sintaxis_python']=len(paths)
    for p in (ROOT/'scripts').glob('*.py'):
        spec=importlib.util.spec_from_file_location('verificar_'+p.stem,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    checks['imports_scripts_sin_main']=True
    manifest=json.loads((ROOT/'results/manifest_publicacion.json').read_text())
    banned={'ID 2','id_encuestado','fila_local','choice','ocupantes_declarados','longitud_declarada_m','latitud','longitud','direccion','patente','rut','secuencia_nodos','secuencia_arcos'}
    for item in manifest['archivos']:
        p=ROOT/item['archivo'];d=pd.read_csv(p)
        assert len(d)==item['filas'],p
        assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'],p
        assert not {str(x).lower() for x in d}.intersection({x.lower() for x in banned}),p
    checks['manifiesto_y_campos_privados']=len(manifest['archivos'])
    p=pd.read_csv(ROOT/'results/calibracion_logit/parametros_centrales_11b.csv')
    expected={'beta_c':-.00002,'beta_t':-.2,'beta_a':-.3,'beta_e':-.3,'ASC_terrestre':0,'lambda_lago':.7}
    for name,value in expected.items():
        z=p[p.parametro.eq(name)];assert len(z)==3 and np.allclose(z.valor,value),name
        assert z.metodo.eq('supuesto').all(),name
    assert p.loc[p.metodo.eq('supuesto'),'error_estandar'].isna().all()
    checks['coeficientes_11b_y_normalizacion']=True
    q=pd.read_csv(ROOT/'results/calibracion_logit/probabilidades_11b_divulgacion.csv')
    s=pd.read_csv(ROOT/'results/sensibilidades/probabilidades_11b_divulgacion.csv')
    for d in [q,s]:
        assert set(d.alternativa)=={'terrestre_chile','barcaza_actual'}
        key=['origen','destino','estacion','segmento','escenario']
        assert not d.duplicated(key+['alternativa']).any()
        total=d.groupby(key).probabilidad.sum(min_count=2).dropna();assert np.allclose(total,1)
        assert d.probabilidad.dropna().between(0,1).all()
        assert d.loc[d.segmento.eq('CAM'),'probabilidad'].isna().all()
        assert d.loc[d.estado_divulgacion.str.startswith('reservado'),'probabilidad'].isna().all()
    checks['probabilidades_y_reservas']=True
    etapa12=ROOT/'results/etapa12/ejemplo_vl_verano.csv'
    if etapa12.exists():
        e=pd.read_csv(etapa12)
        assert e.origen.eq('Chile Chico').all() and e.destino.eq('Coyhaique').all()
        assert e.estacion.eq('Verano').all() and e.segmento.eq('VL').all()
        assert e.escenario.eq('central').sum()==1 and not e.escenario.duplicated().any()
        assert any(x['archivo']=='results/etapa12/ejemplo_vl_verano.csv' for x in manifest['archivos'])
        for cols in [['P_SBO_tierra','P_SBO_actual'],['P_proyecto_tierra','P_proyecto_actual','P_proyecto_nuevo']]:
            assert np.isfinite(e[cols].to_numpy()).all() and e[cols].ge(0).all().all() and e[cols].le(1).all().all()
            assert np.allclose(e[cols].sum(axis=1),1)
        reference=pd.read_csv(ROOT/'results/matrices_od/matriz_vl_divulgacion.csv')
        reference=reference.loc[reference.origen.eq('Chile Chico')&reference.destino.eq('Coyhaique')&reference.estacion.eq('Verano')]
        assert len(reference)==2 and reference.flujo_diario_equivalente_vehiculos.notna().all()
        assert np.allclose(e.demanda_total_OD,reference.flujo_diario_equivalente_vehiculos.sum())
        assert np.allclose(e.demanda_nuevo,e.demanda_total_OD*e.P_proyecto_nuevo)
        assert np.allclose(e.desde_tierra,e.demanda_total_OD*(e.P_SBO_tierra-e.P_proyecto_tierra))
        assert np.allclose(e.desde_actual,e.demanda_total_OD*(e.P_SBO_actual-e.P_proyecto_actual))
        assert np.allclose(e.demanda_nuevo,e.desde_tierra+e.desde_actual)
        assert (e.logsum_proyecto>=e.logsum_SBO).all()
        checks['etapa12_seleccion_y_conservacion']=True
    preliminary=ROOT/'results/demanda_preliminar'
    if preliminary.exists():
        pm=json.loads((preliminary/'manifest_publicacion.json').read_text())
        expected_files={'totales_anuales_intervalos.csv','sensibilidades_intervalos.csv','supuestos_centrales.csv','ejemplo_vl_verano.csv'}
        assert {Path(item['archivo']).name for item in pm['archivos']}==expected_files
        for item in pm['archivos']:
            path=ROOT/item['archivo'];dd=pd.read_csv(path)
            assert path.parent==preliminary and hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
            assert len(dd)==item['filas']
            assert not {str(x).lower() for x in dd}.intersection({x.lower() for x in banned})
            if 'intervalos' in path.name:
                assert not set(dd).intersection({'origen','destino','estacion','sentido'})
                assert dd.limite_superior.gt(dd.limite_inferior).all() and dd.limite_inferior.ge(0).all()
                assert set(dd.segmento)=={'VL','CAM','PEATON'}
            if path.name=='ejemplo_vl_verano.csv':
                assert len(dd)==3 and dd.segmento.eq('VL').all() and dd.estacion.eq('Verano').all()
                assert dd.origen.eq('Chile Chico').all() and dd.destino.eq('Coyhaique').all()
                assert np.isclose(dd.probabilidad.sum(),1) and dd.inducida.ge(0).all()
                assert np.allclose(dd.total_con_proyecto,dd.existente_redistribuida+dd.inducida)
        assert pm['minimo_ancho_relativo']>=.1
        checks['etapa13_publicacion_restringida_y_hashes']=True
    readme=(ROOT/'README.md').read_text();doc=(ROOT/'docs/07_resultados_y_limitaciones.md').read_text()
    for val in p.loc[p.parametro.eq('ASC_barcaza'),'valor']:
        assert f'{val:,.6g}' in readme and f'{val:,.6g}' in doc,'ASC documental distinta de CSV'
    assert 'P-20a' in readme and 'P-20a' in (ROOT/'docs/08_proximos_pasos.md').read_text()
    for f in [ROOT/'README.md',*list((ROOT/'docs').glob('*.md')),ROOT/'results/README.md',ROOT/'archive/README.md']:
        for target in re.findall(r'\]\(([^)]+)\)',f.read_text()):
            if target.startswith(('https:','http:','#','mailto:')):continue
            path=target.split('#')[0].split(':')[0]
            assert (f.parent/path).resolve().exists(),f'Enlace roto {f.relative_to(ROOT)}: {target}'
    checks['documentacion_y_enlaces']=True
    if args.indice:
        names=subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=ROOT).decode().split('\0')
        for name in filter(None,names):
            path=ROOT/name
            if not path.exists():continue
            assert not path.is_symlink(),f'Symlink: {name}'
            assert not name.startswith(('outputs/','data/interim/','data/private/','data/raw/','.venv/')) or name.endswith('/.gitkeep'),name
            assert path.suffix.lower() not in {'.xlsx','.xls','.pdf','.pkl','.pickle','.gpkg','.shp','.dbf','.zip','.env'},name
            assert not path.name.startswith('.env'),name
            assert path.stat().st_size<1024*1024,f'Archivo grande: {name}'
            if name!='scripts/13_validar_repositorio.py':
                text=path.read_text(errors='replace')
                assert not re.search(r'gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,}|-----BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY-----',text),f'Posible secreto: {name}'
        checks['indice_revisado']=True
    print(json.dumps(checks,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
