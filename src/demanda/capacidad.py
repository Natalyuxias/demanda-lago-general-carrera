"""Capacidad y oferta: restricciones distintas, sin inferir demanda adicional."""
from __future__ import annotations
import math
import re


def documento_legible(text):
    """Espacios entre cantidades y palabras en prosa, sin alterar tablas/codigo."""
    out=[];code=False
    for line in text.splitlines():
        if line.startswith('```'):code=not code
        if not code and not line.startswith('|'):
            line=re.sub(r'(?<=[A-Za-záéíóúñÁÉÍÓÚÑ])(?=\d)',' ',line)
            line=re.sub(r'(?<=\d)(?=[A-Za-záéíóúñÁÉÍÓÚÑ])',' ',line)
            line=re.sub(r',(?=[A-Za-záéíóúñÁÉÍÓÚÑ])',', ',line)
            line=re.sub(r'(?<=[A-Za-záéíóúñÁÉÍÓÚÑ]):(?=[A-Za-záéíóúñÁÉÍÓÚÑ\d])',': ',line)
        out.append(line)
    return '\n'.join(out)+'\n'


def limite_ciclos_dia(navegacion_h, maniobra_h, ventana_h):
    # n ciclos: 2n navegaciones y 2n+1 maniobras; inicio y fin descargados.
    if navegacion_h <= 0 or maniobra_h < 0 or ventana_h <= 0:
        raise ValueError('Tiempos no validos')
    return max(0, math.floor((ventana_h-maniobra_h)/(2*(navegacion_h+maniobra_h))))


def asignaciones(frecuencia, max_por_nave):
    """Cada salida por sentido requiere un ciclo completo por nave."""
    if frecuencia < 0 or int(frecuencia) != frecuencia:
        raise ValueError('Frecuencia debe ser entero no negativo por sentido')
    return [(i, frecuencia-i) for i in range(1, frecuencia)
            if i <= max_por_nave and frecuencia-i <= max_por_nave]


def evaluar(semana_ml, semana_pax, f_teh, f_nueva, ml_teh, ml_nueva,
            pax_teh, pax_nueva, objetivo=1, punta=1):
    if not 0 < objetivo <= 1 or punta < 1:
        raise ValueError('Objetivo o punta no validos')
    cm=f_teh*ml_teh+f_nueva*ml_nueva
    cp=f_teh*pax_teh+f_nueva*pax_nueva
    rm=semana_ml*punta/cm if cm else math.nan
    rp=semana_pax*punta/cp if cp else math.nan
    return dict(capacidad_ml_semana=cm, capacidad_pax_semana=cp,
                ocupacion_ml=rm, ocupacion_pax=rp,
                cumple_media_o_punta_condicional=(rm<=objetivo and rp<=objetivo)
                if math.isfinite(rm) and math.isfinite(rp) else None)


def frecuencia_minima(semana_ml, semana_pax, capacidades, objetivo, punta,
                      max_por_nave, max_busqueda=50):
    if not all(math.isfinite(x) for x in [semana_ml,semana_pax]):
        return None
    if min(semana_ml,semana_pax)<0: raise ValueError('Demanda negativa')
    for f in range(2,max_busqueda+1):
        candidates=[]
        for a,b in asignaciones(f,max_por_nave):
            e=evaluar(semana_ml,semana_pax,a,b,*capacidades,objetivo,punta)
            if e['cumple_media_o_punta_condicional']:
                candidates.append((max(e['ocupacion_ml'],e['ocupacion_pax']),a,b))
        if candidates:
            _,a,b=min(candidates)
            return f,a,b
    return None


def horario_ciclos(f_teh,f_nueva,navegacion_h,maniobra_h,ventana_h,dias=7):
    """Calendario constructivo: naves parten de orillas opuestas y vuelven al origen.

    Mantiene tiempos iguales en ambas naves. Verifica ventana y maniobras en
    terminal; no certifica tripulacion, clima, atraque de espera ni autorizacion.
    """
    events=[]
    for ship,cycles,home in [('Tehuelche',f_teh,'Chile Chico'),('Nueva',f_nueva,'Ibanez')]:
        other='Ibanez' if home=='Chile Chico' else 'Chile Chico'
        for day in range(dias):
            n=cycles//dias+(day<cycles%dias)
            if n and 2*n*navegacion_h+(2*n+1)*maniobra_h>ventana_h+1e-9:
                return [],False
            for k in range(2*n+1 if n else 0):
                t=k*(navegacion_h+maniobra_h)
                events.append(dict(nave=ship,dia=day+1,terminal=home if k%2==0 else other,
                                   inicio_h=t,fin_h=t+maniobra_h,
                                   evento='maniobra_terminal',zarpa=k<2*n))
    for i,a in enumerate(events):
        for b in events[i+1:]:
            if a['nave']!=b['nave'] and a['dia']==b['dia'] and a['terminal']==b['terminal']:
                if min(a['fin_h'],b['fin_h'])-max(a['inicio_h'],b['inicio_h'])>1e-9:
                    return events,False
    return events,True


def preparar_cambio_costo(t_horario_historico=None,t_horario_sbo=None,vst=None):
    """Gancho para CG: ninguna espera uniforme ni intervalo/2 por defecto."""
    if any(v is None for v in [t_horario_historico,t_horario_sbo,vst]):return math.nan
    return (t_horario_sbo-t_horario_historico)*vst
