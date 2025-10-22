from flask import Blueprint, request, jsonify
from server.extensions import db
from server.models import Evento, Usuario
from flask_jwt_extended import jwt_required, get_jwt_identity

bp = Blueprint('events', __name__, url_prefix='/events')

@bp.route('', methods=['POST'])
@jwt_required()  
def create_event():
    data = request.get_json() or {}
    uid = int(get_jwt_identity()) 
    
    id_usuario = data.get('id_usuario') or uid
    if not id_usuario:
        return jsonify({"error":"id_usuario requerido"}), 400
    
    tipo_evento = data.get('tipo_evento')
    detalle = data.get('detalle')
    origen = data.get('origen')
    valor = data.get('valor')
    if not all([tipo_evento, detalle, origen, valor]):
        return jsonify({"error":"tipo_evento, detalle, origen y valor son requeridos"}), 400
    ip = request.remote_addr
    ev = Evento(id_usuario=id_usuario, tipo_evento=tipo_evento, detalle=detalle, origen=origen, valor=str(valor), origen_ip=ip)
    db.session.add(ev)
    db.session.commit()
    return jsonify({"msg":"evento creado","id_evento": ev.id_evento}), 201

@bp.route('', methods=['GET'])
def latest():
    detalle = request.args.get('detalle')
    limit = int(request.args.get('limit', 5))
    q = Evento.query
    if detalle:
        q = q.filter_by(detalle=detalle)
    rows = q.order_by(Evento.fecha_hora.desc()).limit(limit).all()
    return jsonify([r.to_dict() for r in rows]), 200
