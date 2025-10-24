from flask import Blueprint, request, jsonify
from server.extensions import db
from server.models import Command, Evento
from flask_jwt_extended import jwt_required, get_jwt_identity
import requests
import logging

bp = Blueprint('commands', __name__, url_prefix='/api/commands')

@bp.route('', methods=['POST'])  
@jwt_required()
def create_command():
    data = request.get_json() or {}
    uid = get_jwt_identity()
    tipo = data.get('tipo')
    detalle = data.get('detalle')
    accion = data.get('accion')
    device_id = data.get('device_id')
    if not all([tipo, detalle, accion]):
        return jsonify({"error":"tipo, detalle y accion son requeridos"}), 400
    # ensure uid is integer for FK
    try:
        uid_int = int(uid)
    except Exception:
        uid_int = uid

    cmd = Command(id_usuario=uid_int, device_id=device_id, tipo=tipo, detalle=detalle, accion=accion)
    db.session.add(cmd)
    # determine tipo_evento using known enum values so the column is not left NULL
    tipo_evento = None
    if tipo == 'LED':
        tipo_evento = 'LED_ON' if str(accion).upper() == 'ON' else 'LED_OFF'
    elif tipo == 'MOTOR':
        # motors don't have a specific Evento enum; fallback to LED-like mapping if applicable
        tipo_evento = 'LED_ON' if str(accion).upper() == 'ON' else 'LED_OFF'
    elif detalle == 'CONTADOR' and str(accion).upper() in ('RESET', '0'):
        tipo_evento = 'RESET_CONTADOR'
    else:
        # best-effort fallback to one of the allowed enums
        if str(accion).upper() in ('ON','OFF'):
            tipo_evento = 'LED_ON' if str(accion).upper() == 'ON' else 'LED_OFF'
        else:
            tipo_evento = 'RESET_CONTADOR' if 'RESET' in str(accion).upper() else None

    origen = data.get('origen', 'APP')
    ev = Evento(id_usuario=uid_int, tipo_evento=tipo_evento, detalle=detalle, origen=origen, valor=accion, origen_ip=request.remote_addr)
    db.session.add(ev)
    db.session.commit()

    # attempt to deliver command to device directly if device_id looks like a reachable host
    # This is best-effort: network errors won't fail the API call
    if device_id:
        try:
            # if detalle looks like LEDn, extract number to call device endpoint
            if detalle and detalle.upper().startswith('LED'):
                try:
                    led_num = int(''.join([c for c in detalle if c.isdigit()]))
                except Exception:
                    led_num = None
                if led_num is not None:
                    # decide estado payload
                    estado_val = '1' if str(accion).upper() == 'ON' else '0'
                    # allow device_id to be an IP or host; caller must provide full host or ip
                    url = f'http://{device_id}/updateLed/{led_num}'
                    logging.info(f'Attempting to notify device at {url} payload estado={estado_val}')
                    try:
                        requests.put(url, json={"led": led_num, "estado": int(estado_val)}, timeout=2)
                    except Exception as e:
                        logging.debug(f'Could not contact device {device_id}: {e}')
        except Exception:
            # swallow any errors to avoid breaking the API
            logging.debug('Error trying to notify device')
    return jsonify({"msg":"comando creado", "id_command": cmd.id_command}), 201

@bp.route('', methods=['GET'])
@jwt_required()
def list_commands():

    device_id = request.args.get('device_id')
    q = Command.query
    if device_id:
        q = q.filter_by(device_id=device_id)
    rows = q.order_by(Command.fecha_creacion.desc()).all()
    return jsonify([r.to_dict() for r in rows]), 200

@bp.route('mark', methods=['POST'])
@jwt_required()
def mark_command():
    data = request.get_json() or {}
    idc = data.get('id_command')
    if not idc:
        return jsonify({"error":"id_command requerido"}), 400
    cmd = Command.query.get(idc)
    if not cmd:
        return jsonify({"error":"comando no encontrado"}), 404
    cmd.enviada = True
    db.session.commit()
    return jsonify({"msg":"ok"}), 200
