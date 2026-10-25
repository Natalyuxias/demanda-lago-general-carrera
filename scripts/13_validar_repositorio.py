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
