from flask import Blueprint, request
from ..models import Evento
from ..extensions import db 
from flask_jwt_extended import jwt_required, get_jwt_identity
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


@bp.route("/secure-data", methods=["POST"])
@jwt_required()
def secure_data():
    uid = get_jwt_identity()
    data = request.get_json() or {}

    evento = Evento(
        id_usuario=uid,
        tipo_evento=data.get("tipo_evento", "LED_OFF"),
        detalle=data.get("detalle", "LED2"),
        origen=data.get("origen", "APP"),
        valor=data.get("valor", "OFF"),
        fecha_hora=datetime.utcnow(),
        origen_ip=request.remote_addr
    )
    db.session.add(evento)
    db.session.commit()
    return {"msg": "Evento guardado por usuario autenticado", "user": uid}, 201
