"""Rutas y componentes de atributos, sin utilidades ni probabilidades de elección."""
import math
import networkx as nx


def calendario_semanal(salidas):
    """Intervalos cíclicos; H ponderado por tiempo supone horario deseado uniforme.

    No calcula espera en el terminal. La media simple de intervalos siempre es168/f.
    """
    hours=sorted(float(day)*24+float(hour) for day,hour in salidas)
    if not hours or len(set(hours))!=len(hours) or min(hours)<0 or max(hours)>=168:
        raise ValueError('Calendario inválido o con salidas duplicadas')
    gaps=[b-a for a,b in zip(hours,hours[1:]+[hours[0]+168])]
    return dict(f=len(hours),salidas_h_semana=hours,intervalos_h=gaps,
                H_media_intervalos_h=sum(gaps)/len(gaps),
                H_ponderado_tiempo_h=sum(x*x for x in gaps)/168,
                intervalo_min_h=min(gaps),intervalo_max_h=max(gaps))


def grafo_vial(frame, segmento, pais=None, pares_frontera=()):
    """Grafo dirigido con reverso modelado donde la fuente no da restricciones.

    Arcos paralelos: conservar el de menor tiempo y su identificador, no sobrescribir
    por orden de lectura. Se excluyen conectores convencionales y transbordadores.
    """
    speed='VEL VP' if segmento=='CAM' else 'VEL VL'
    excluded={frozenset(p) for p in pares_frontera}
    g=nx.DiGraph()
    for _,row in frame.iterrows():
        if row.Clave in ['C','TRANSB']:continue
        a,b=int(row.Nodo_A),int(row.Nodo_B)
        if frozenset([a,b]) in excluded:continue
        argentina=str(row.REGI_N)=='Argentina'
        if pais=='Chile' and argentina or pais=='Argentina' and not argentina:continue
        if row[speed]<=0 or not math.isfinite(float(row[speed])):continue
        data=row.to_dict();data['tiempo_ruteo_h']=float(row.LONGITUD/row[speed])
        for u,v in [(a,b),(b,a)]:
            if not g.has_edge(u,v) or data['tiempo_ruteo_h']<g[u][v]['tiempo_ruteo_h']:
                g.add_edge(u,v,**data)
    return g


def camino_minimo(g,origen,destino):
    nodes=nx.shortest_path(g,origen,destino,weight='tiempo_ruteo_h')
    return [dict(g[a][b],desde=a,hasta=b) for a,b in zip(nodes[:-1],nodes[1:])]


def comprobar_secuencia(edges,origen,destino):
    current=origen
    for e in edges:
        if e['desde']!=current:raise ValueError('Itinerario discontinuo')
        current=e['hasta']
    if current!=destino:raise ValueError('Destino no alcanzado')
    ids=[int(e['ID_Arco']) for e in edges]
    if len(ids)!=len(set(ids)):raise ValueError('Arcos repetidos en el viaje')


def tiempos_aditivos(conduccion,navegacion,es_barcaza):
    """Conducción completa se asigna a acceso en viajes con barcaza, una sola vez."""
    return dict(t_acceso_modelo_h=conduccion if es_barcaza else 0.0,
                t_viaje_modelo_h=navegacion if es_barcaza else conduccion,
                t_desplazamiento_fisico_h=conduccion+navegacion)
