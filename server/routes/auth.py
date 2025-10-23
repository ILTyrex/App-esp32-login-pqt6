from flask import Blueprint, request, jsonify
from server.extensions import db
from server.models import Usuario
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import datetime

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = data.get('usuario')
    password = data.get('contrasena')
    if not username or not password:
        return jsonify({"error":"usuario y contrasena son requeridos"}), 400
    if Usuario.query.filter_by(usuario=username).first():
        return jsonify({"error":"Usuario ya existe"}), 400
    hashed = generate_password_hash(password)
    user = Usuario(usuario=username, contrasena=hashed)
    db.session.add(user)
    db.session.commit()
    return jsonify({"msg":"usuario creado", "id_usuario": user.id_usuario}), 201

@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('usuario')
    password = data.get('contrasena')
    if not username or not password:
        return jsonify({"error":"usuario y contrasena son requeridos"}), 400
    user = Usuario.query.filter_by(usuario=username).first()
    if not user:
        return jsonify({"error":"Credenciales inválidas"}), 401

    # validate password; handle legacy plain-text passwords
    valid = False
    try:
        valid = check_password_hash(user.contrasena, password)
    except ValueError:
        # stored password not a valid hash (maybe plain text) -> fallback
        if user.contrasena == password:
            valid = True
            # try to migrate to a secure hash
            try:
                user.contrasena = generate_password_hash(password)
                db.session.add(user)
                db.session.commit()
            except Exception:
                # don't block login if migration fails
                pass

    if not valid:
        return jsonify({"error":"Credenciales inválidas"}), 401
    expires = datetime.timedelta(hours=8)
    access_token = create_access_token(identity=str(user.id_usuario), expires_delta=expires)
    return jsonify({"access_token": access_token, "usuario": user.to_dict()}), 200

@bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    uid = get_jwt_identity()
    user = Usuario.query.get(uid)
    if not user:
        return jsonify({"error":"Usuario no encontrado"}), 404
    return jsonify(user.to_dict()), 200
