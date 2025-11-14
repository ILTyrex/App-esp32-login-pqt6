from flask import Blueprint, request, send_file, jsonify
from server.extensions import db
from server.models import Evento, HistorialExportado
from flask_jwt_extended import jwt_required, get_jwt_identity
import csv, io, datetime

bp = Blueprint('export', __name__, url_prefix='/export')

@bp.route('', methods=['GET'])
@jwt_required()
def export_csv():
    user = int(get_jwt_identity())
    formato = request.args.get('format', 'CSV').upper()
    desde = request.args.get('from')    
    hasta = request.args.get('to')
    detalle = request.args.get('detalle')

    q = Evento.query
    if detalle:
        q = q.filter_by(detalle=detalle)
    if desde:
        q = q.filter(Evento.fecha_hora >= desde)
    if hasta:
        q = q.filter(Evento.fecha_hora <= hasta)
    rows = q.order_by(Evento.fecha_hora.asc()).all()

    if formato == 'CSV':
        si = io.StringIO()
        writer = csv.writer(si)
        writer.writerow(['id_evento','id_usuario','tipo_evento','detalle','origen','valor','origen_ip','fecha_hora'])
        for r in rows:
            writer.writerow([r.id_evento, r.id_usuario, r.tipo_evento, r.detalle, r.origen, r.valor, r.origen_ip, r.fecha_hora.isoformat() if r.fecha_hora else ''])
        si.seek(0)
        
        reg = HistorialExportado(id_usuario=user, formato='CSV')
        db.session.add(reg)
        db.session.commit()
        return send_file(io.BytesIO(si.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name=f'export_{datetime.datetime.utcnow().isoformat()}.csv')
    elif formato == 'PDF':
        # The client performs PDF generation locally; here we only record the export in the history
        reg = HistorialExportado(id_usuario=user, formato='PDF')
        db.session.add(reg)
        db.session.commit()
        return jsonify({"ok": True, "message": "Exportación registrada como PDF"}), 200
    else:
        return jsonify({"error":"Formato no soportado"}), 400
