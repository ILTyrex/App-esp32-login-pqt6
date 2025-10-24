from flask import Blueprint, request
from ..models import Evento
from ..extensions import db 
from datetime import datetime, timezone, timedelta

bp = Blueprint("esp32", __name__, url_prefix="/api/esp32")

@bp.route("/data", methods=["POST"])
def receive_data():
    data = request.get_json() or {}

    id_usuario = data.get("id_usuario", 1) 
    tipo_evento = data.get("tipo_evento", "LED_ON")
    detalle = data.get("detalle", "LED1")
    origen = data.get("origen", "CIRCUITO")
    valor = data.get("valor", "ON")

    colombia_tz = timezone(timedelta(hours=-5))

    evento = Evento(
        id_usuario=id_usuario,
        tipo_evento=tipo_evento,
        detalle=detalle,
        origen=origen,
        valor=valor,
        fecha_hora=datetime.now(colombia_tz),
        origen_ip=request.remote_addr
    )
    db.session.add(evento)
    db.session.commit()

    return {"msg": "Evento guardado correctamente"}, 201


@bp.route("/get-data", methods=["GET"])
def get_data():
    """
    Devuelve la tabla completa de eventos (o limitada por el parámetro `limit`).
    Query params opcionales:
      - limit: número máximo de eventos a devolver (por defecto devuelve todos)
      - since: fecha ISO para filtrar desde esa fecha
    """
    # Devuelve solo los últimos 5 registros ordenados por fecha (más recientes primero)
    events = (
        Evento.query.order_by(Evento.fecha_hora.desc()).limit(5).all()
    )
    return {"events": [e.to_dict() for e in events]}, 200


@bp.route("/last-event", methods=["GET"])
def get_last_event():
    """
    Devuelve el último evento creado desde la WEB que sea relevante para el ESP.
    Actualmente incluye comandos para LEDs ('LED_ON','LED_OFF') y para resetear el
    contador ('RESET_CONTADOR'). El ESP puede consultar esta ruta periódicamente y,
    si hay un evento nuevo, leer los campos `tipo_evento`, `detalle` (ej. 'LED1' o 'CONTADOR')
    y `valor` ('ON'|'OFF'|'RESET') para accionar el hardware y la pantalla.
    """
    # Filtrar solo eventos creados por la WEB que interesan al ESP
    # (LED on/off, reset contador y login de usuario)
    q = Evento.query.filter(Evento.origen == 'WEB', Evento.tipo_evento.in_(['LED_ON', 'LED_OFF', 'RESET_CONTADOR', 'LOGIN']))
    ev = q.order_by(Evento.fecha_hora.desc()).first()
    if not ev:
        return {"event": None}, 200
    return {"event": ev.to_dict()}, 200

