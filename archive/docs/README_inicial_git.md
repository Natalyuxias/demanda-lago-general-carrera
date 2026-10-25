# Estimación de demanda Bahía Jara–Levicán (EVALSO)

Repositorio de implementación reproducible en Python de la metodología de demanda del **Informe 2 EVALSO, capítulo 5**. Comenzamos con **diagnóstico, demanda base y escenarios**, no con un logit inventado.

## Inicio inmediato en Linux / EndeavourOS

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src pytest -q
python scripts/01_auditar_eod.py --eod '/home/nataly/Escritorio/Anexos/Cap 6/BBDD EOD/Base de datos agregada.xlsx'
```

**Leer primero** `AGENTS.md` y `docs/PLAN_PARA_HOY.md`.

## Trabajar con Codex y GitHub

1. Crear un repositorio **privado** vacío en GitHub (sin README precreado). Copiar esta carpeta al equipo.
2. Desde la carpeta local: `git init && git branch -M main && git add . && git commit -m 'Estructura de demanda'`.
3. Vincular el repositorio: `git remote add origin git@github.com:USUARIO/NOMBRE-REPO.git && git push -u origin main` (configurar previamente claves SSH), o usar GitHub CLI `gh repo create NOMBRE-REPO --private --source=. --remote=origin --push` después de `gh auth login`.
4. Ejecutar `codex` en la carpeta local, con sesión iniciada. Copiar el prompt de `docs/PROMPT_CODEX_HOY.md`.
5. **Preferir Codex CLI local:** la EOD es grande y no debe subirse a GitHub para que la analice Codex. El agente local puede leerla desde el disco con permisos del usuario; Codex Cloud no puede acceder por defecto a esa carpeta externa.

## Pasos de cálculo

### A. Auditoría individual

`01_auditar_eod.py`: lee hoja `BBDD-1` y `BBDD-2 (solo válidas)` e informa registros por OD. **NO es demanda expandida.**

### B. Escenarios (solo cuando la base diaria esté validada o explícitamente supuesta)

Completar la plantilla `data/templates/flujos_base.csv` con un flujo lacustre **diario** por temporada, sentido y tipo de usuario. El dato debe incluir `estado_fuente` (`observado`, `calculado` o `supuesto`) y `fuente_y_metodo`. `flujo_tierra_elegible_dia` puede quedar vacío y en ese caso **la captación total seguirá vacía**. No inventar días de temporada: si están vacíos no habrá resultado anual.

```bash
python scripts/02_escenarios_demanda.py --input data/templates/flujos_base.csv
```

Genera `outputs/tables/escenarios_captacion.csv` con captación **condicional** del 10/25/50 %. Son tasas hipotéticas de desviación, NO probabilidades calibradas, y el resultado no incorpora demanda inducida.

## Qué NO se ha estimado

No se han estimado factores de expansión representativos, logit, betas, `lambda`, elasticidades, flujos terrestres elegibles, demanda inducida, demanda anual de referencia ni beneficios sociales. Ver `docs/plan_implementacion.md` y la bitácora de decisiones.

## Tratamiento de datos y privacidad

Archivos de consultoras y microdatos individuales deben quedar solo en carpeta local; **no subir a repositorio ni compartir claves/identificadores personales**. `.gitignore` excluye `data/raw`, `data/interim`, salidas y documentos de consultoras.
