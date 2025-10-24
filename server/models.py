from .extensions import db
from datetime import datetime
import pytz

colombia_tz = pytz.timezone('America/Bogota')

def get_colombia_time():
    return datetime.now(colombia_tz)

class Usuario(db.Model):
    __tablename__ = "usuarios"
    id_usuario = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(100), unique=True, nullable=False)
    contrasena = db.Column(db.String(255), nullable=False) 
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    activo = db.Column(db.Boolean, default=True)
    rol = db.Column(db.Enum('ADMIN','USER'), default='USER')

    eventos = db.relationship("Evento", backref="usuario", cascade="all, delete-orphan")
    exportaciones = db.relationship("HistorialExportado", backref="usuario", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id_usuario": self.id_usuario,
            "usuario": self.usuario,
            "fecha_registro": self.fecha_registro.isoformat() if self.fecha_registro else None,
            "activo": bool(self.activo),
            "rol": self.rol
        }

class Evento(db.Model):
    __tablename__ = "eventos"
    id_evento = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"), nullable=False)
    tipo_evento = db.Column(db.Enum("LED_ON", "LED_OFF", "SENSOR_BLOQUEADO", "SENSOR_LIBRE", "RESET_CONTADOR", "CONTADOR_CAMBIO"), nullable=False)
    detalle = db.Column(db.Enum("LED1", "LED2", "LED3", "LED4", "SENSOR_IR", "CONTADOR"), nullable=False)
    # extend origen enum to include WEB (frontend web app)
    origen = db.Column(db.Enum("APP", "WEB", "CIRCUITO"), nullable=False)
    valor = db.Column(db.String(50), nullable=False)
    origen_ip = db.Column(db.String(45), nullable=True)
    fecha_hora = db.Column(db.DateTime, default=get_colombia_time)

    def to_dict(self):
        return {
            "id_evento": self.id_evento,
            "id_usuario": self.id_usuario,
            "tipo_evento": self.tipo_evento,
            "detalle": self.detalle,
            "origen": self.origen,
            "valor": self.valor,
            "origen_ip": self.origen_ip,
            "fecha_hora": self.fecha_hora.isoformat() if self.fecha_hora else None
        }

class HistorialExportado(db.Model):
    __tablename__ = "historialexportado"
    id_exportacion = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"), nullable=False)
    formato = db.Column(db.Enum("CSV", "PDF"), nullable=False)
    fecha_exportacion = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id_exportacion": self.id_exportacion,
            "id_usuario": self.id_usuario,
            "formato": self.formato,
            "fecha_exportacion": self.fecha_exportacion.isoformat() if self.fecha_exportacion else None
        }

class Dispositivo(db.Model):
    __tablename__ = "dispositivos"
    id_dispositivo = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(255), unique=True, nullable=False)
    nombre = db.Column(db.String(100))
    token_device = db.Column(db.String(255))
    last_seen = db.Column(db.DateTime)
    activo = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            "id_dispositivo": self.id_dispositivo,
            "device_id": self.device_id,
            "nombre": self.nombre,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "activo": self.activo
        }

class Command(db.Model):
    __tablename__ = "commands"
    id_command = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"), nullable=False)
    device_id = db.Column(db.String(100), nullable=True)
    tipo = db.Column(db.Enum('LED','MOTOR','SYSTEM'), nullable=False)
    detalle = db.Column(db.String(50), nullable=False)
    accion = db.Column(db.Enum('ON','OFF','STATUS','SHOW_USER'), nullable=False)
    enviada = db.Column(db.Boolean, default=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id_command": self.id_command,
            "id_usuario": self.id_usuario,
            "device_id": self.device_id,
            "tipo": self.tipo,
            "detalle": self.detalle,
            "accion": self.accion,
            "enviada": self.enviada,
            "fecha_creacion": self.fecha_creacion.isoformat() if self.fecha_creacion else None
        }

class EstadoActual(db.Model):
    __tablename__ = "estados_actuales"
    id_estado = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(100), nullable=True)
    detalle = db.Column(db.String(50), nullable=False)
    valor = db.Column(db.String(20), nullable=False)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id_estado": self.id_estado,
            "device_id": self.device_id,
            "detalle": self.detalle,
            "valor": self.valor,
            "fecha_actualizacion": self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None
        }
