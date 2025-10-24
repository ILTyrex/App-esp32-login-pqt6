from flask import Blueprint, request, jsonify
from server.extensions import db
from server.models import Evento, EstadoActual
from datetime import datetime

bp = Blueprint('legacy_esp32', __name__)


@bp.route('/sendData', methods=['POST'])
def send_data():
    data = request.get_json() or {}
    contador = data.get('contador')

    if contador is None:
        return jsonify({"error": "contador requerido"}), 400

    # map to Evento and EstadoActual (detalle CONTADOR)
    try:
        valor = str(int(contador))
    except Exception:
        valor = str(contador)

    # choose tipo_evento: use RESET_CONTADOR when counter is 0, else SENSOR_BLOQUEADO
    tipo = 'RESET_CONTADOR' if valor == '0' else 'SENSOR_BLOQUEADO'

    ev = Evento(id_usuario=1, tipo_evento=tipo, detalle='CONTADOR', origen='CIRCUITO', valor=valor, fecha_hora=datetime.utcnow(), origen_ip=request.remote_addr)
    db.session.add(ev)

    # update or create EstadoActual for CONTADOR
    st = EstadoActual.query.filter_by(detalle='CONTADOR').first()
    if not st:
        st = EstadoActual(device_id=None, detalle='CONTADOR', valor=valor)
        db.session.add(st)
    else:
        st.valor = valor

    db.session.commit()
    return jsonify({"msg": "contador recibido", "contador": valor}), 201


@bp.route('/updateLed/<int:led_num>', methods=['PUT'])
def update_led(led_num):
    data = request.get_json() or {}
    estado = data.get('estado')

    if estado is None:
        return jsonify({"error": "estado requerido"}), 400

    try:
        estado_int = int(estado)
    except Exception:
        # allow boolean-like values
        estado_int = 1 if str(estado).lower() in ('1','true','on') else 0

    detalle = f'LED{led_num}'
    tipo = 'LED_ON' if estado_int else 'LED_OFF'

    ev = Evento(id_usuario=1, tipo_evento=tipo, detalle=detalle, origen='CIRCUITO', valor=str(estado_int), fecha_hora=datetime.utcnow(), origen_ip=request.remote_addr)
    db.session.add(ev)

    # update EstadoActual
    st = EstadoActual.query.filter_by(detalle=detalle).first()
    if not st:
        st = EstadoActual(device_id=None, detalle=detalle, valor=str(estado_int))
        db.session.add(st)
    else:
        st.valor = str(estado_int)

    db.session.commit()
    return jsonify({"msg": "led actualizado", "detalle": detalle, "estado": estado_int}), 200


@bp.route('/getDatos', methods=['GET'])
def get_datos():
    # return led1/2/3 states
    def led_state(n):
        d = EstadoActual.query.filter_by(detalle=f'LED{n}').first()
        if not d:
            return False
        try:
            return bool(int(d.valor))
        except Exception:
            return str(d.valor).lower() in ('1','true','on')

    return jsonify({
        'led1': led_state(1),
        'led2': led_state(2),
        'led3': led_state(3)
    }), 200
