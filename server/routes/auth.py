from flask import Blueprint, request, jsonify
from server.extensions import db
from server.models import Usuario, Dispositivo
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import datetime
import pytz

bp = Blueprint('auth', __name__, url_prefix='/auth')
colombia_tz = pytz.timezone('America/Bogota')

@bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = data.get('usuario')
    password = data.get('contrasena')
    if not username or not password:
        return jsonify({"error": "usuario y contrasena son requeridos"}), 400
    if Usuario.query.filter_by(usuario=username).first():
        return jsonify({"error": "Usuario ya existe"}), 400
    hashed = generate_password_hash(password)
    user = Usuario(usuario=username, contrasena=hashed)
    db.session.add(user)
    db.session.commit()
    return jsonify({"msg": "usuario creado", "id_usuario": user.id_usuario}), 201

@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('usuario')
    password = data.get('contrasena')
    if not username or not password:
        return jsonify({"error": "usuario y contrasena son requeridos"}), 400
    user = Usuario.query.filter_by(usuario=username).first()
    if not user:
        return jsonify({"error": "Credenciales inválidas"}), 401
    valid = False
    try:
        valid = check_password_hash(user.contrasena, password)
    except ValueError:
        if user.contrasena == password:
            valid = True
            try:
                user.contrasena = generate_password_hash(password)
                db.session.add(user)
                db.session.commit()
            except Exception:
                pass
    if not valid:
        return jsonify({"error": "Credenciales inválidas"}), 401
    expires = datetime.timedelta(hours=8)
    access_token = create_access_token(identity=str(user.id_usuario), expires_delta=expires)
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent', 'Desconocido')
    device = Dispositivo.query.filter_by(device_id=user_agent).first()
    if not device:
        device = Dispositivo(
            device_id=user_agent,
            nombre=f"Dispositivo de {user.usuario}",
            last_seen=datetime.datetime.now(colombia_tz),
            activo=True
        )
        db.session.add(device)
    else:
        device.last_seen = datetime.datetime.now(colombia_tz)
        device.activo = True
    db.session.commit()
    return jsonify({
        "msg": f"Bienvenido {user.usuario}",
        "access_token": access_token,
        "usuario": user.to_dict(),
        "ip": ip_address,
        "dispositivo": user_agent
    }), 200

@bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    uid = get_jwt_identity()
    user = Usuario.query.get(uid)
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404
    return jsonify(user.to_dict()), 200
