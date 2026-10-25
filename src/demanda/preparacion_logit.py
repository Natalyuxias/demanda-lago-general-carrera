"""Atributos físicos y dinero; sin estimación de utilidades ni probabilidades."""
import math


def homologar(precio, indice_origen, indice_destino):
    if any(x is None or not math.isfinite(float(x)) for x in [precio,indice_origen,indice_destino]):
        return math.nan
    if indice_origen<=0 or indice_destino<=0:raise ValueError('IPC debe ser positivo')
    return precio*indice_destino/indice_origen


def tiempo_vehiculo(conduccion, navegacion, previo, desembarque, horario):
    """Conducción incluye acceso: no sumar otra vez una columna de acceso."""
    valores=[conduccion,navegacion,previo,desembarque]
    fisico=sum(valores) if all(math.isfinite(float(x)) for x in valores) else math.nan
    return fisico,fisico+horario


def tarifa_personas(ocupantes, adulto, conductor_liberado, todos_acompanantes_exentos=False):
    if not math.isfinite(float(ocupantes)) or ocupantes<1:return math.nan
    pagadores=max(ocupantes-1,0) if conductor_liberado else ocupantes
    if todos_acompanantes_exentos:pagadores=0 if conductor_liberado else 1
    return adulto*pagadores


def tiempo_servicio_completo(publicado, extras_fuera_servicio=0):
    """No re-agregar navegación ni operaciones a un servicio combinado completo."""
    return publicado+extras_fuera_servicio
