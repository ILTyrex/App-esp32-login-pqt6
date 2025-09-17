# python.py
import sys
import os
import webbrowser
import time
import json
import csv
from functools import partial
from pathlib import Path
from datetime import datetime
import re

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QMessageBox, QComboBox, QPlainTextEdit, QSizePolicy,
    QDialog, QDialogButtonBox, QListWidget, QRadioButton, QTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QTextCursor
import base64
import binascii
from io import BytesIO, StringIO

# optional serial
try:
    import serial
    import serial.tools.list_ports
except Exception:
    serial = None

# optional pdf generation
try:
    from reportlab.pdfgen import canvas as pdfcanvas
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

# Try use new LoginController
try:
    from app.controllers.login_controller import LoginController
except Exception:
    LoginController = None

# DB helper
try:
    from app.models.database import get_connection
except Exception:
    get_connection = None

# constants
MAX_WIDTH = 820
SETTINGS_FILE = Path(__file__).parent / "settings.json"
EXPORTS_DIR = Path(__file__).parent / "exports"
EXPORTS_DIR.mkdir(exist_ok=True)
EXPORTS_SESSION = EXPORTS_DIR / "session"
EXPORTS_BD = EXPORTS_DIR / "bd"
EXPORTS_SESSION.mkdir(parents=True, exist_ok=True)
EXPORTS_BD.mkdir(parents=True, exist_ok=True)


# ----------------- settings helpers -----------------
def load_settings():
    defaults = {"theme": "light"}
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return defaults
            return {**defaults, **data}
    except Exception:
        return defaults
    return defaults


def save_settings(settings: dict):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("No se pudo guardar settings:", e)


# ----------------- DB helpers -----------------
def get_db_conn():
    if get_connection is None:
        return None
    try:
        return get_connection()
    except Exception as e:
        print("DB get_db_conn error:", e)
        return None


def get_or_create_user_id(username: str):
    conn = get_db_conn()
    if conn is None:
        return None
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id_usuario FROM usuarios WHERE usuario = %s", (username,))
        row = cursor.fetchone()
        if row:
            if isinstance(row, dict):
                return row.get("id_usuario")
            return row[0]
        cursor.execute("INSERT INTO usuarios (usuario, contrasena) VALUES (%s, %s)", (username, ""))
        try:
            conn.commit()
        except Exception:
            pass
        return cursor.lastrowid if hasattr(cursor, "lastrowid") else None
    except Exception as e:
        print("DB get_or_create_user_id error:", e)
        return None
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass


def db_save_event(user_id, tipo_evento, detalle, origen, valor):
    if user_id is None:
        return False
    conn = get_db_conn()
    if conn is None:
        return False
    cursor = None
    try:
        cursor = conn.cursor()
        sql = "INSERT INTO eventos (id_usuario, tipo_evento, detalle, origen, valor) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(sql, (user_id, tipo_evento, detalle, origen, valor))
        try:
            conn.commit()
        except Exception:
            pass
        return True
    except Exception as e:
        print("DB save_event error:", e)
        return False
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass


def db_save_export_file(user_id, formato, filename=None, content_bytes=None):
    """
    Guarda metadatos de exportación en `historialexportado`.
    - Si `filename` se proporciona, intenta guardarlo en la columna `filename` (si existe).
    - Si `content_bytes` se proporciona, lo codifica en base64 y lo guarda en una columna de texto
      (intenta `contenido`, `detalle`, `valor` en ese orden según lo que exista en el esquema).
    - Si no se puede guardar filename ni contenido, guarda al menos el formato.
    """
    if user_id is None:
        return False
    conn = get_db_conn()
    if conn is None:
        return False
    cursor = None
    try:
        cursor = conn.cursor()
        # prefer guardar contenido si se proporcionó
        if content_bytes is not None:
            try:
                b64 = base64.b64encode(content_bytes).decode('ascii')
            except Exception:
                try:
                    # si es str
                    b64 = base64.b64encode(str(content_bytes).encode('utf-8')).decode('ascii')
                except Exception:
                    b64 = None

            if b64:
                # intentar columnas candidatas para contenido
                inserted = False
                # primero intentar columna 'contenido'
                try:
                    cursor.execute("INSERT INTO historialexportado (id_usuario, formato, contenido) VALUES (%s, %s, %s)",
                                   (user_id, formato, b64))
                    try:
                        conn.commit()
                    except Exception:
                        pass
                    inserted = True
                except Exception as e:
                    # si la columna no existe, intentar crearla (LONGBLOB) y reintentar
                    try:
                        msg = str(e).lower()
                        if 'unknown column' in msg or 'columna' in msg or 'contenido' in msg:
                            try:
                                cursor.execute("ALTER TABLE historialexportado ADD COLUMN contenido LONGBLOB")
                                try:
                                    conn.commit()
                                except Exception:
                                    pass
                                # reintentar insert
                                cursor.execute("INSERT INTO historialexportado (id_usuario, formato, contenido) VALUES (%s, %s, %s)",
                                               (user_id, formato, b64))
                                try:
                                    conn.commit()
                                except Exception:
                                    pass
                                inserted = True
                            except Exception:
                                inserted = False
                        else:
                            inserted = False
                    except Exception:
                        inserted = False

                if not inserted:
                    # intentar columnas alternativas de texto (detalle / valor)
                    try:
                        cursor.execute("INSERT INTO historialexportado (id_usuario, formato, detalle) VALUES (%s, %s, %s)",
                                       (user_id, formato, b64))
                        try:
                            conn.commit()
                        except Exception:
                            pass
                        inserted = True
                    except Exception:
                        try:
                            cursor.execute("INSERT INTO historialexportado (id_usuario, formato, valor) VALUES (%s, %s, %s)",
                                           (user_id, formato, b64))
                            try:
                                conn.commit()
                            except Exception:
                                pass
                            inserted = True
                        except Exception:
                            inserted = False

                if inserted:
                    return True

        # si no hay contenido, intentar guardar filename si existe
        if filename:
            try:
                cursor.execute(
                    "INSERT INTO historialexportado (id_usuario, formato, filename) VALUES (%s, %s, %s)",
                    (user_id, formato, filename)
                )
                try:
                    conn.commit()
                except Exception:
                    pass
                return True
            except Exception:
                # fallback: try detalle/valor
                try:
                    cursor.execute("INSERT INTO historialexportado (id_usuario, formato, detalle) VALUES (%s, %s, %s)",
                                   (user_id, formato, filename))
                    try:
                        conn.commit()
                    except Exception:
                        pass
                    return True
                except Exception:
                    try:
                        cursor.execute("INSERT INTO historialexportado (id_usuario, formato) VALUES (%s, %s)", (user_id, formato))
                        try:
                            conn.commit()
                        except Exception:
                            pass
                        return True
                    except Exception:
                        return False

        # final fallback: sólo formato
        try:
            cursor.execute("INSERT INTO historialexportado (id_usuario, formato) VALUES (%s, %s)", (user_id, formato))
            try:
                conn.commit()
            except Exception:
                pass
            return True
        except Exception as e:
            print("DB save_export_file error:", e)
            return False
    except Exception as e:
        print("DB save_export_file error:", e)
        return False
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass


def _extract_filename_from_row(cursor, row):
    """
    Extrae de forma robusta el nombre de fichero a partir de una fila y la descripción del cursor.
    Intenta columnas comunes: filename, file, nombre, ruta, detalle, valor, name, path.
    También detecta valores que terminan en .pdf o .csv.
    """
    candidates = ["filename", "file", "nombre", "ruta", "path", "detalle", "valor", "name"]
    try:
        # dict-like row
        if isinstance(row, dict):
            for c in candidates:
                if c in row and row[c]:
                    return str(row[c])
            for k, v in row.items():
                try:
                    if isinstance(v, str) and (v.lower().endswith(".pdf") or v.lower().endswith(".csv")):
                        return v
                except Exception:
                    pass
            return None
        # tuple-like row: use cursor.description
        desc = []
        try:
            desc = [d[0].lower() for d in cursor.description] if cursor and cursor.description else []
        except Exception:
            desc = []
        for idx, colname in enumerate(desc):
            if colname in candidates:
                try:
                    val = row[idx]
                    if val:
                        return str(val)
                except Exception:
                    pass
        # fallback: any str item ending .pdf/.csv
        for item in row:
            try:
                if isinstance(item, str) and (item.lower().endswith(".pdf") or item.lower().endswith(".csv")):
                    return item
            except Exception:
                pass
        return None
    except Exception:
        return None


def db_list_exported(formato=None):
    """
    Lista registros en historialexportado.
    Si `formato` es 'CSV' o 'PDF' filtra por ello, si es None devuelve ambos.
    Devuelve lista de tuples (id, formato, filename_or_None, fecha_hora_or_None).
    """
    conn = get_db_conn()
    if conn is None:
        return []
    cursor = None
    out = []
    try:
        cursor = conn.cursor()
        if formato in ("CSV", "PDF"):
            cursor.execute("SELECT * FROM historialexportado WHERE formato=%s", (formato,))
        else:
            cursor.execute("SELECT * FROM historialexportado")
        rows = cursor.fetchall()
        if not rows:
            return []
        for r in rows:
            fn = _extract_filename_from_row(cursor, r)
            rec_id = None
            fecha = None
            fmt = None
            try:
                if isinstance(r, dict):
                    rec_id = r.get("id") or r.get("id_exportacion") or r.get("id_historial") or None
                    fecha = r.get("fecha_hora") or r.get("fecha_exportacion") or r.get("created_at") or None
                    fmt = r.get("formato")
                else:
                    desc_names = [d[0].lower() for d in cursor.description] if cursor.description else []
                    if "id" in desc_names:
                        rec_id = r[desc_names.index("id")]
                    elif "id_exportacion" in desc_names:
                        rec_id = r[desc_names.index("id_exportacion")]
                    if "fecha_hora" in desc_names:
                        fecha = r[desc_names.index("fecha_hora")]
                    elif "fecha_exportacion" in desc_names:
                        fecha = r[desc_names.index("fecha_exportacion")]
                    elif "created_at" in desc_names:
                        fecha = r[desc_names.index("created_at")]
                    if "formato" in desc_names:
                        fmt = r[desc_names.index("formato")]
            except Exception:
                pass
            out.append((rec_id, (fmt or "?"), fn, fecha))
        # sort by fecha (if present) descending; fecha may be None or string
        try:
            out_sorted = sorted(out, key=lambda x: x[3] or "", reverse=True)
        except Exception:
            out_sorted = out
        return out_sorted
    except Exception as e:
        print("db_list_exported error:", e)
        return []
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass


def db_fetch_export_file(rec_id):
    """
    Obtiene el contenido de un fichero exportado desde la fila en BD.
    Devuelve siempre bytes (archivo binario o texto en bytes), o None.
    Esta versión intenta con heurísticas decodificar base64 incluso si hay saltos de línea o espacios.
    """
    conn = get_db_conn()
    if conn is None:
        return None
    cursor = None
    try:
        cursor = conn.cursor()
        for id_col in ("id_exportacion", "id", "id_historial"):
            try:
                cursor.execute(f"SELECT * FROM historialexportado WHERE {id_col}=%s LIMIT 1", (rec_id,))
                rows = cursor.fetchall()
                if not rows:
                    continue
                row = rows[0]
                row_map = {}
                if isinstance(row, dict):
                    row_map = row
                else:
                    try:
                        desc = [d[0].lower() for d in cursor.description] if cursor.description else []
                        for idx, name in enumerate(desc):
                            try:
                                row_map[name] = row[idx]
                            except Exception:
                                pass
                    except Exception:
                        pass

                def _try_decode_b64_from_text(text):
                    # eliminar espacios y saltos de línea, intentar decodificar
                    s_clean = re.sub(r"\s+", "", text)
                    try:
                        decoded = base64.b64decode(s_clean, validate=False)
                        return decoded
                    except Exception:
                        return None

                def _is_likely_pdf(bts):
                    return bts[:4] == b"%PDF"

                def _is_likely_text_csv(bts):
                    try:
                        txt = bts.decode('utf-8', errors='ignore')
                        # heurística: contiene comas y/o varias líneas
                        return (',' in txt) and ('\n' in txt or '\r' in txt)
                    except Exception:
                        return False

                # prefer 'contenido' column
                if 'contenido' in row_map and row_map.get('contenido'):
                    val = row_map['contenido']
                    if isinstance(val, (bytes, bytearray)):
                        b = bytes(val)
                        # si parece ser archivo binario válido -> devolver
                        if _is_likely_pdf(b) or not all(32 <= x <= 127 or x in (9,10,13) for x in b[:64]):
                            return b
                        # si parece texto (probablemente base64 almacenado como bytes) intentar decodificar
                        try:
                            txt = b.decode('utf-8', errors='ignore')
                            decoded = _try_decode_b64_from_text(txt)
                            if decoded:
                                # aceptar decoded si parece PDF o CSV
                                if _is_likely_pdf(decoded) or _is_likely_text_csv(decoded):
                                    return decoded
                                # sino, si decoded produce texto legible retornar decoded
                                try:
                                    _ = decoded.decode('utf-8')
                                    return decoded
                                except Exception:
                                    return b
                            else:
                                return b
                        except Exception:
                            return b
                    elif isinstance(val, str):
                        s = val.strip()
                        # si parece filename, no es contenido
                        if s.lower().endswith('.pdf') or s.lower().endswith('.csv'):
                            return None
                        decoded = _try_decode_b64_from_text(s)
                        if decoded:
                            return decoded
                        else:
                            return s.encode('utf-8')

                # fallback: revisar otras columnas
                candidates = ["file", "data", "blob", "detalle", "valor", "contenido_base64", "content", "archivo", "filename"]
                for c in candidates:
                    if c in row_map and row_map[c]:
                        val = row_map[c]
                        if isinstance(val, (bytes, bytearray)):
                            return bytes(val)
                        if isinstance(val, str):
                            s = val.strip()
                            if s.lower().endswith('.pdf') or s.lower().endswith('.csv'):
                                continue
                            decoded = _try_decode_b64_from_text(s)
                            if decoded:
                                return decoded
                            else:
                                return s.encode('utf-8')
                return None
            except Exception:
                continue
        return None
    except Exception as e:
        print("db_fetch_export_file error:", e)
        return None
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass


# ----------------- SerialThread -----------------
class SerialThread(QThread):
    line_received = pyqtSignal(str)
    connected = pyqtSignal(bool)

    def __init__(self, port, baud=115200):
        super().__init__()
        self.port = port
        self.baud = baud
        self._running = True
        self.ser = None

    def run(self):
        if serial is None:
            self.connected.emit(False)
            return
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=0.1)
            self.connected.emit(True)
        except Exception as e:
            print("Serial open error:", e)
            self.connected.emit(False)
            return

        while self._running:
            try:
                if self.ser.in_waiting:
                    line = self.ser.readline().decode(errors='ignore').strip()
                    if line:
                        self.line_received.emit(line)
                self.msleep(10)
            except Exception as e:
                print("Serial read error:", e)
                break

        try:
            self.ser.close()
        except:
            pass
        self.connected.emit(False)

    def stop(self):
        self._running = False
        self.wait()

    def write(self, data: str):
        if self.ser and self.ser.is_open:
            self.ser.write((data + "\n").encode())


# ----------------- MainWindow -----------------
class MainWindow(QWidget):
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.setWindowTitle(f"Protoboard - Usuario: {username}")
        self.resize(900, 640)

        # session-only history (in-memory)
        self.history = []

        self.total_counter = 0
        self.led_states = [False, False, False, False]
        self.sensor_last_state = False

        self.serial_thread = None
        self.sim_timer = None
        self.sim_interval_ms = 7000

        settings = load_settings()
        self.current_theme = settings.get("theme", "light")

        self.db_user_id = None
        self.db_available = False
        try:
            if get_connection is not None:
                self.db_user_id = get_or_create_user_id(self.username)
                if self.db_user_id:
                    self.db_available = True
        except Exception as e:
            print("DB init error:", e)
            self.db_user_id = None
            self.db_available = False

        self.build_ui_centered()
        self.apply_theme(self.current_theme)
        self.update_ui()

        if serial is None:
            self.start_simulation()

    # QSS methods (same as before)
    def qss_light(self):
        return """
        QWidget { background: #f3f6fb; color: #222; font-family: "Segoe UI", Roboto, Arial, sans-serif; }
        QLabel#title { font-size:20px; font-weight:700; color:#23395d; }
        QLabel#counter { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #6a89ff, stop:1 #5ecbe6); color:white; padding:10px 16px; border-radius:10px; font-weight:700; }
        QPushButton { background: white; border:1px solid #d7e0ef; padding:8px 10px; border-radius:8px; font-weight:600; }
        QPushButton:hover { background:#f0f6ff; }
        QPushButton#connectBtn { background:#23395d; color:white; border:none; min-width:130px; }
        QPushButton#resetBtn { background:#ff6b6b; color:white; border:none; }
        QWidget.card { background:white; border-radius:10px; padding:10px; border:1px solid rgba(0,0,0,0.04); }
        QLabel.smallNote { color:#6c7a89; font-size:12px; }
        """

    def qss_dark(self):
        return """
        QWidget { background:#0f1724; color:#e6eef8; font-family: "Segoe UI", Roboto, Arial, sans-serif; }
        QLabel#title { font-size:20px; font-weight:700; color:#9bd1ff; }
        QLabel#counter { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #2b6bff, stop:1 #00c1d4); color:#021029; padding:10px 16px; border-radius:10px; font-weight:700; }
        QPushButton { background:#101826; border:1px solid #243444; padding:8px 10px; border-radius:8px; color:#e6eef8; font-weight:600; }
        QPushButton:hover { background:#162134; }
        QPushButton#connectBtn { background:#0b2946; color:#bfe7ff; border:1px solid #24455f; }
        QPushButton#resetBtn { background:#b94a4a; color:white; border:none; }
        QWidget.card { background:#0b1520; border-radius:10px; padding:10px; border:1px solid #112233; }
        QLabel.smallNote { color:#9fb0c8; font-size:12px; }
        """

    def apply_theme(self, theme: str):
        if theme == "dark":
            self.setStyleSheet(self.qss_dark())
            self.theme_btn.setText("☀️  Claro")
        else:
            self.setStyleSheet(self.qss_light())
            self.theme_btn.setText("🌙  Oscuro")
        self.current_theme = theme
        save_settings({"theme": self.current_theme})
        self.update_ui()

    def build_ui_centered(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(8)

        center_h = QHBoxLayout()
        center_h.addStretch()

        content = QWidget()
        content.setMaximumWidth(MAX_WIDTH)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Panel Protoboard")
        title.setObjectName("title")
        header.addWidget(title)

        self.theme_btn = QPushButton("🌙  Oscuro")
        self.theme_btn.setToolTip("Alternar tema claro/oscuro")
        self.theme_btn.clicked.connect(self.on_toggle_theme)
        self.theme_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        header.addWidget(self.theme_btn)

        header.addStretch()
        content_layout.addLayout(header)

        # connection card
        conn_card = QWidget()
        conn_card.setProperty("class", "card")
        conn_layout = QHBoxLayout(conn_card)
        conn_layout.setContentsMargins(8, 8, 8, 8)
        conn_layout.setSpacing(8)

        self.port_combo = QComboBox()
        ports = []
        if serial is not None:
            try:
                ports = [p.device for p in serial.tools.list_ports.comports()]
            except Exception:
                ports = []
        self.port_combo.addItems(ports)
        self.port_combo.setMaximumWidth(220)

        self.connect_btn = QPushButton("🔌  Conectar")
        self.connect_btn.setObjectName("connectBtn")
        self.connect_btn.setToolTip("Conectar / desconectar puerto serial")
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.connect_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        conn_layout.addWidget(QLabel("Puerto:"))
        conn_layout.addWidget(self.port_combo)
        conn_layout.addStretch()
        conn_layout.addWidget(self.connect_btn)
        content_layout.addWidget(conn_card)

        sensor_counter_h = QHBoxLayout()
        sensor_counter_h.addStretch()

        self.sensor_status_label = QLabel("🟢 Sensor: Libre")
        self.sensor_status_label.setFixedWidth(180)
        self.sensor_status_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sensor_counter_h.addWidget(self.sensor_status_label)

        self.counter_label = QLabel("📡  Contador (sensor): 0")
        self.counter_label.setObjectName("counter")
        self.counter_label.setFixedWidth(200)
        self.counter_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sensor_counter_h.addWidget(self.counter_label)

        sensor_counter_h.addStretch()
        content_layout.addLayout(sensor_counter_h)

        # LEDs area
        leds_card = QWidget()
        leds_card.setProperty("class", "card")
        leds_layout = QGridLayout(leds_card)
        leds_layout.setContentsMargins(8, 8, 8, 8)
        leds_layout.setHorizontalSpacing(12)
        leds_layout.setVerticalSpacing(10)

        leds_layout.setColumnStretch(0, 0)
        leds_layout.setColumnStretch(1, 1)
        leds_layout.setColumnStretch(2, 0)

        leds_layout.addWidget(QLabel("<b>LED</b>"), 0, 0)
        leds_layout.addWidget(QLabel("<b>Control</b>"), 0, 1)
        leds_layout.addWidget(QLabel("<b>Estado</b>"), 0, 2)

        self.led_buttons_toggle = []
        self.led_state_labels = []

        for i in range(3):
            label = QLabel(f"LED {i+1}")
            label.setMinimumWidth(80)
            label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

            btn = QPushButton("🟢  Encender")
            btn.setToolTip(f"Alternar LED {i+1}")
            btn.clicked.connect(partial(self.gui_toggle_led, i))
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

            state_lbl = QLabel("⚪ OFF")
            state_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            state_lbl.setFixedWidth(100)
            state_lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

            leds_layout.addWidget(label, i+1, 0)
            leds_layout.addWidget(btn, i+1, 1)
            leds_layout.addWidget(state_lbl, i+1, 2)

            self.led_buttons_toggle.append(btn)
            self.led_state_labels.append(state_lbl)

        label4 = QLabel("LED 4 (sensor)")
        label4.setMinimumWidth(80)

        btn4 = QPushButton("📡  Sensor (disabled)")
        btn4.setEnabled(False)
        btn4.setToolTip("LED4 se controla desde la protoboard por el sensor; no se puede controlar desde la app.")
        btn4.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        state4 = QLabel("⚪ OFF")
        state4.setAlignment(Qt.AlignmentFlag.AlignCenter)
        state4.setFixedWidth(100)

        leds_layout.addWidget(label4, 4, 0)
        leds_layout.addWidget(btn4, 4, 1)
        leds_layout.addWidget(state4, 4, 2)
        self.led_state_labels.append(state4)

        leds_card.setMaximumWidth(MAX_WIDTH - 40)
        content_layout.addWidget(leds_card)

        # bottom controls: export, view exports, reset
        bottom_card = QWidget()
        bottom_card.setProperty("class", "card")
        bottom_layout = QHBoxLayout(bottom_card)
        bottom_layout.setContentsMargins(8, 8, 8, 8)
        bottom_layout.addStretch()

        self.export_btn = QPushButton("💾  Exportar historial")
        self.export_btn.setToolTip("Exportar historial de la sesión (CSV o PDF)")
        self.export_btn.clicked.connect(self.export_dialog)
        self.export_btn.setMaximumWidth(180)

        self.view_exports_btn = QPushButton("📁 Ver archivos exportados")
        self.view_exports_btn.setToolTip("Ver archivos exportados registrados en BD y abrirlos")
        self.view_exports_btn.clicked.connect(self.view_exports_dialog)
        self.view_exports_btn.setMaximumWidth(200)
        if not self.db_available:
            self.view_exports_btn.setEnabled(False)

        self.reset_btn = QPushButton("♻️  Reset contador")
        self.reset_btn.setObjectName("resetBtn")
        self.reset_btn.setToolTip("Reiniciar contador (solo activaciones del sensor)")
        self.reset_btn.clicked.connect(self.reset_total)
        self.reset_btn.setMaximumWidth(160)

        bottom_layout.addWidget(self.export_btn)
        bottom_layout.addWidget(self.view_exports_btn)
        bottom_layout.addWidget(self.reset_btn)
        content_layout.addWidget(bottom_card)

        note = QLabel()
        if serial is None:
            note.setText("Modo SIMULACIÓN: pyserial no instalado. Activaciones del sensor se simulan.")
        else:
            note.setText("ESP32 debe enviar: BTN:1..3 (pulsadores), SENSOR:1/0 (sensor) y opcional ACK:LED:n:v.")
        note.setProperty("class", "smallNote")
        content_layout.addWidget(note)

        # session-only history view (terminal-like)
        self.events_view = QPlainTextEdit()
        self.events_view.setReadOnly(True)
        self.events_view.setMaximumHeight(200)
        content_layout.addWidget(self.events_view)

        center_h.addWidget(content)
        center_h.addStretch()
        outer.addLayout(center_h)

    # Serial / simulation
    def toggle_connection(self):
        if self.serial_thread and self.serial_thread.isRunning():
            self.serial_thread.stop()
            self.serial_thread = None
            self.connect_btn.setText("🔌  Conectar")
            if serial is None:
                self.start_simulation()
            return

        port = self.port_combo.currentText()
        if not port:
            QMessageBox.warning(self, "Error", "Selecciona un puerto serial.")
            return

        self.stop_simulation()
        self.serial_thread = SerialThread(port, 115200)
        self.serial_thread.line_received.connect(self.on_line)
        self.serial_thread.connected.connect(self.on_connected)
        self.serial_thread.start()

    def on_connected(self, ok):
        if ok:
            self.connect_btn.setText("🔌  Desconectar")
            QMessageBox.information(self, "Serial", "Conectado al puerto serial.")
        else:
            self.connect_btn.setText("🔌  Conectar")
            QMessageBox.critical(self, "Serial", "No se pudo conectar al puerto.")

    def start_simulation(self):
        if self.sim_timer is None:
            self.sim_timer = QTimer(self)
            self.sim_timer.timeout.connect(self.simulate_sensor_event)
            self.sim_timer.start(self.sim_interval_ms)

    def stop_simulation(self):
        if self.sim_timer:
            self.sim_timer.stop()
            self.sim_timer = None

    def simulate_sensor_event(self):
        self.on_line("SENSOR:1")
        QTimer.singleShot(600, lambda: self.on_line("SENSOR:0"))

    # Line processing
    def on_line(self, line: str):
        line = line.strip()
        if not line:
            return
        print("FROM ESP32:", line)
        up = line.upper()

        if up.startswith("BTN:"):
            try:
                idx = int(line.split(":")[1]) - 1
                if 0 <= idx <= 2:
                    self.led_states[idx] = True
                    self.history.append((datetime.now().isoformat(), idx+1, "BTN"))
                    if self.db_user_id:
                        db_save_event(self.db_user_id, "LED_ON", f"LED{idx+1}", "CIRCUITO", "1")
                    self.update_ui()
                elif idx == 3:
                    self.handle_sensor_activation(True)
            except Exception:
                pass
            return

        if up.startswith("ACK:LED:"):
            parts = line.split(":")
            if len(parts) >= 4:
                try:
                    idx = int(parts[2]) - 1
                    val = parts[3]
                    state = (val == "1")
                    if 0 <= idx <= 3:
                        self.led_states[idx] = state
                        self.history.append((datetime.now().isoformat(), idx+1, f"ACK:{val}"))
                        if self.db_user_id and idx < 3:
                            tipo = "LED_ON" if state else "LED_OFF"
                            db_save_event(self.db_user_id, tipo, f"LED{idx+1}", "CIRCUITO", val)
                        if idx == 3:
                            self.handle_sensor_activation(state)
                        self.update_ui()
                except Exception:
                    pass
            return

        if up.startswith("SENSOR:") or up.startswith("PROX:"):
            try:
                parts = line.split(":")
                val = parts[1] if len(parts) > 1 else ""
                is_on = (val == "1" or val.upper() == "ON" or val.upper() == "TRUE")
                self.handle_sensor_activation(is_on)
            except Exception:
                pass
            return

        # Otros -> only in-memory
        self.history.append((datetime.now().isoformat(), 0, line))
        if self.db_user_id:
            db_save_event(self.db_user_id, "LED_OFF", "CONTADOR", "CIRCUITO", line[:50])
        self.update_ui()

    def handle_sensor_activation(self, is_on: bool):
        prev = self.sensor_last_state
        self.sensor_last_state = is_on
        self.led_states[3] = is_on

        if (not prev) and is_on:
            self.total_counter += 1
            self.history.append((datetime.now().isoformat(), 4, "SENSOR_ON"))
            if self.db_user_id:
                db_save_event(self.db_user_id, "SENSOR_BLOQUEADO", "SENSOR_IR", "CIRCUITO", f"contador={self.total_counter}")
        else:
            self.history.append((datetime.now().isoformat(), 4, "SENSOR_ON" if is_on else "SENSOR_OFF"))
            if self.db_user_id:
                tipo = "SENSOR_BLOQUEADO" if is_on else "SENSOR_LIBRE"
                db_save_event(self.db_user_id, tipo, "SENSOR_IR", "CIRCUITO", "1" if is_on else "0")

        self.update_ui()

    def gui_toggle_led(self, idx: int):
        if idx == 3:
            QMessageBox.information(self, "Información", "LED4 es controlado por el sensor y no puede activarse desde la app.")
            return

        new_state = not self.led_states[idx]
        if self.serial_thread and self.serial_thread.isRunning():
            cmd = f"LED:{idx+1}:{'1' if new_state else '0'}"
            self.serial_thread.write(cmd)
            self.led_states[idx] = new_state
            self.history.append((datetime.now().isoformat(), idx+1, f"GUI_TOGGLE:{'1' if new_state else '0'}"))
            if self.db_user_id:
                tipo = "LED_ON" if new_state else "LED_OFF"
                db_save_event(self.db_user_id, tipo, f"LED{idx+1}", "APP", "1" if new_state else "0")
            self.update_ui()
        else:
            self.led_states[idx] = new_state
            action = "ON (GUI)" if new_state else "OFF (GUI)"
            self.history.append((datetime.now().isoformat(), idx+1, action))
            if self.db_user_id:
                tipo = "LED_ON" if new_state else "LED_OFF"
                db_save_event(self.db_user_id, tipo, f"LED{idx+1}", "APP", "1" if new_state else "0")
            self.update_ui()

    def reset_total(self):
        confirm = QMessageBox.question(self, "Confirmar reset",
                                       "¿Deseas reiniciar el contador (solo cuenta activaciones del sensor)?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            self.total_counter = 0
            self.history.append((datetime.now().isoformat(), 0, "RESET"))
            # Enviar comando al dispositivo para resetear el contador físico si está conectado
            try:
                if self.serial_thread and self.serial_thread.isRunning():
                    # El dispositivo debería interpretar 'RESET' como reinicio del contador.
                    # Si tu firmware espera otro comando, cámbialo aquí (p.ej. 'RESET:0').
                    self.serial_thread.write("RESET")
            except Exception:
                pass
            if self.db_user_id:
                db_save_event(self.db_user_id, "RESET_CONTADOR", "CONTADOR", "APP", "0")
            self.update_ui()

    # ---------------- export logic ----------------
    def export_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Exportar historial - Elegir formato")
        dlg.resize(360, 140)
        layout = QVBoxLayout(dlg)

        lbl = QLabel("¿En qué formato deseas exportar el historial de la SESIÓN actual?")
        layout.addWidget(lbl)

        radios_layout = QHBoxLayout()
        rb_csv = QRadioButton("CSV (texto)")
        rb_pdf = QRadioButton("PDF (documento)")
        rb_csv.setChecked(True)
        radios_layout.addWidget(rb_csv)
        radios_layout.addWidget(rb_pdf)
        layout.addLayout(radios_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttons)

        def accept():
            fmt = "csv" if rb_csv.isChecked() else "pdf"
            dlg.accept()
            self.export_session(format=fmt)

        buttons.accepted.connect(accept)
        buttons.rejected.connect(dlg.reject)
        dlg.exec()

    def _safe_timestamp_str(self):
        return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    def export_session(self, format="csv"):
        ts_str = self._safe_timestamp_str()
        if format == "csv":
            fname = f"historial_session_{ts_str}.csv"
            # generar CSV en memoria
            try:
                s = StringIO()
                w = csv.writer(s)
                w.writerow(["timestamp", "led", "action"])
                for row in self.history:
                    w.writerow(row)
                data_bytes = s.getvalue().encode('utf-8')
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo generar CSV en memoria: {e}")
                return

            # guardar en BD (contenido base64)
            if self.db_user_id:
                ok = db_save_export_file(self.db_user_id, "CSV", filename=fname, content_bytes=data_bytes)
                if ok:
                    QMessageBox.information(self, "Exportado", f"Historial guardado en BD como CSV (id registrado).")
                else:
                    QMessageBox.warning(self, "Exportado (parcial)", "No se pudo registrar el CSV en BD; consulta registros.")
            else:
                QMessageBox.information(self, "Exportado (local)", "CSV generado en memoria pero no hay usuario BD para guardar.")
        elif format == "pdf":
            fname = f"historial_session_{ts_str}.pdf"
            path = EXPORTS_BD / fname
            if not REPORTLAB_AVAILABLE:
                QMessageBox.warning(self, "reportlab no instalado",
                                    "No se pudo generar PDF porque 'reportlab' no está instalado.\nPuedes instalarlo con: pip install reportlab\nSe guardará CSV en su lugar.")
                self.export_session(format="csv")
                return
            try:
                # generar PDF en memoria
                bio = BytesIO()
                c = pdfcanvas.Canvas(bio)
                y = 800
                c.setFont("Helvetica", 10)
                c.drawString(30, y, f"Historial sesión - usuario: {self.username} - {datetime.now().isoformat()}")
                y -= 20
                for row in self.history:
                    line = f"{row[0]} - LED {row[1]} - {row[2]}"
                    chunks = [line[i:i+100] for i in range(0, len(line), 100)]
                    for ch in chunks:
                        if y < 60:
                            c.showPage()
                            y = 800
                            c.setFont("Helvetica", 10)
                        c.drawString(30, y, ch)
                        y -= 14
                c.save()
                try:
                    bio.seek(0)
                    data_bytes = bio.read()
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"No se pudo leer PDF en memoria: {e}")
                    return
                if self.db_user_id:
                    ok = db_save_export_file(self.db_user_id, "PDF", filename=fname, content_bytes=data_bytes)
                    if ok:
                        QMessageBox.information(self, "Exportado", "Historial guardado en BD como PDF (id registrado).")
                    else:
                        QMessageBox.warning(self, "Exportado (parcial)", "No se pudo registrar el PDF en BD; consulta registros.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo generar PDF: {e}")
        else:
            QMessageBox.warning(self, "Formato no soportado", f"Formato: {format}")

    # ---------------- show CSV in table ----------------
    def show_csv_table(self, csv_path: Path):
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo leer CSV: {e}")
            return

        if not rows:
            QMessageBox.information(self, "CSV vacío", "El archivo CSV está vacío.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"CSV: {csv_path.name}")
        dlg.resize(900, 600)
        layout = QVBoxLayout(dlg)

        headers = rows[0]
        # Use a simple text view for now to avoid adding QTableWidget import; it's fine for viewing
        txt = QPlainTextEdit()
        txt.setReadOnly(True)
        txt.setPlainText("\t".join(headers) + "\n" + "\n".join([",".join(r) for r in rows[1:]]))
        layout.addWidget(txt)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)
        dlg.exec()

    # ---------------- view exports (BD-only) ----------------
    def view_exports_dialog(self):
        """
        Muestra los archivos exportados que están registrados en la base de datos.
        El diálogo permite elegir tipo (CSV/PDF) y lista los registros encontrados en BD.
        """
        if not self.db_available or not self.db_user_id:
            QMessageBox.warning(self, "BD no disponible", "La base de datos no está disponible o el usuario no existe.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Ver archivos exportados (registrados en BD)")
        dlg.resize(700, 480)
        layout = QVBoxLayout(dlg)

        # list widget + info (mostramos todos los archivos guardados en BD)
        listw = QListWidget()
        layout.addWidget(listw)

        info = QPlainTextEdit()
        info.setReadOnly(True)
        info.setMaximumHeight(160)
        layout.addWidget(info)

        # buttons
        btns = QDialogButtonBox()
        open_btn = QPushButton("Abrir seleccionado")
        refresh_btn = QPushButton("Refrescar lista")
        close_btn = QPushButton("Cerrar")
        btns.addButton(open_btn, QDialogButtonBox.ButtonRole.ActionRole)
        btns.addButton(refresh_btn, QDialogButtonBox.ButtonRole.ActionRole)
        btns.addButton(close_btn, QDialogButtonBox.ButtonRole.RejectRole)
        layout.addWidget(btns)

        def populate():
            listw.clear()
            info.clear()
            records = db_list_exported(None)
            if not records:
                listw.addItem("(no hay archivos registrados en BD)")
                return
            # build list; for records without filename try to find local files of same format
            seen = set()
            items = []
            for rec in records:
                rec_id, fmt, filename, fecha = rec
                if filename:
                    items.append((rec_id, fmt or '?', filename, fecha))
                    seen.add(filename)
                else:
                    # Attempt to fetch content from 'contenido' column
                    try:
                        content = db_fetch_export_file(rec_id)
                        if content:
                            # if content is bytes that actually contain base64 text, decode
                            if isinstance(content, (bytes, bytearray)):
                                try:
                                    txt_try = content.decode('utf-8')
                                    if re.fullmatch(r'[A-Za-z0-9+/\s=]+', txt_try):
                                        txt_clean = re.sub(r"\s+", "", txt_try)
                                        try:
                                            decoded = base64.b64decode(txt_clean)
                                            content = decoded
                                        except Exception:
                                            pass
                                except Exception:
                                    pass
                            elif isinstance(content, str):
                                s = content.strip()
                                s_clean = re.sub(r"\s+", "", s)
                                try:
                                    decoded = base64.b64decode(s_clean)
                                    content = decoded
                                except Exception:
                                    content = s.encode('utf-8')

                            temp_filename = f"temp_{rec_id}.{fmt.lower()}"
                            temp_path = EXPORTS_SESSION / temp_filename
                            with open(temp_path, "wb") as wf:
                                wf.write(content)
                            items.append((rec_id, fmt or '?', temp_filename, fecha))
                            seen.add(temp_filename)
                    except Exception as e:
                        print(f"Error fetching content for record {rec_id}: {e}")
                        items.append((rec_id, fmt or '?', '(sin filename)', fecha))

            for rec_id, fmt, filename, fecha in items:
                display = f"{rec_id or '-'} | {fmt or '?'} | {filename or '(sin filename)'} | {fecha or '-'}"
                listw.addItem(display)

        def show_info():
            curr = listw.currentItem()
            if not curr:
                return
            info.setPlainText(curr.text())

        def open_selected():
            curr = listw.currentItem()
            if not curr:
                return
            text = curr.text()
            if text.startswith("("):
                return
            parts = [p.strip() for p in text.split("|")]
            # expected: id | formato | filename | fecha
            if len(parts) < 3:
                QMessageBox.warning(dlg, "Formato inesperado", "No se puede obtener filename del registro.")
                return
            fmt = parts[1]
            filename = parts[2]
            if filename in ("(sin filename)", "", "None"):
                QMessageBox.warning(dlg, "Sin fichero", "Este registro no tiene filename asociado en BD.")
                return
            if fmt.upper() == "CSV":
                p1 = EXPORTS_SESSION / filename
                p2 = EXPORTS_BD / filename
                file_path = p1 if p1.exists() else (p2 if p2.exists() else None)
                if not file_path:
                    # intentar recuperar desde BD si existe contenido allí
                    try:
                        data = db_fetch_export_file(parts[0])
                        print(f"[debug] fetched data for id={parts[0]} type={type(data)} len={len(data) if data else 0}")
                        if data:
                            # normalize: if bytes that are actually base64 text, try decode
                            if isinstance(data, (bytes, bytearray)):
                                try:
                                    txt = data.decode('utf-8')
                                    s_clean = re.sub(r"\s+", "", txt)
                                    if re.fullmatch(r'[A-Za-z0-9+/=]+', s_clean):
                                        try:
                                            decoded2 = base64.b64decode(s_clean)
                                            # if decoded looks like pdf or csv, use it
                                            if decoded2.startswith(b'%PDF') or (b',' in decoded2 and b'\n' in decoded2):
                                                data = decoded2
                                                print(f"[debug] secondary base64 decoded for id={parts[0]}")
                                        except Exception as e:
                                            print(f"[debug] secondary decode failed: {e}")
                                except Exception:
                                    pass
                            elif isinstance(data, str):
                                s = data.strip()
                                s_clean = re.sub(r"\s+", "", s)
                                try:
                                    decoded2 = base64.b64decode(s_clean)
                                    if decoded2.startswith(b'%PDF') or (b',' in decoded2 and b'\n' in decoded2):
                                        data = decoded2
                                        print(f"[debug] decoded string -> bytes for id={parts[0]}")
                                except Exception:
                                    data = s.encode('utf-8')

                            out_path = EXPORTS_SESSION / filename
                            with open(out_path, "wb") as wf:
                                wf.write(data if isinstance(data, (bytes, bytearray)) else data.encode('utf-8'))
                            file_path = out_path
                    except Exception as e:
                        print(f"Error retrieving file from database: {e}")
                        file_path = None
                    if not file_path:
                        QMessageBox.warning(dlg, "Archivo no encontrado", f"No se encontró el CSV localmente. Esperado: {p1} o {p2}")
                        return
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    viewer = QDialog(self)
                    viewer.setWindowTitle(f"CSV - {filename}")
                    viewer.resize(900, 600)
                    vbox = QVBoxLayout(viewer)
                    te = QPlainTextEdit()
                    te.setReadOnly(True)
                    te.setPlainText(content)
                    vbox.addWidget(te)
                    viewer.exec()
                except Exception as e:
                    QMessageBox.critical(dlg, "Error", f"No se pudo leer CSV: {e}")
                return
            else:
                # PDF: try both bd and session dirs just in case; users may have exported in either
                file_path = EXPORTS_BD / filename
                if not file_path.exists():
                    file_path = EXPORTS_SESSION / filename
                if not file_path.exists():
                    # intentar recuperar desde BD
                    try:
                        data = db_fetch_export_file(parts[0])
                        if data:
                            out_path = EXPORTS_BD / filename
                            try:
                                with open(out_path, "wb") as wf:
                                    if isinstance(data, str):
                                        wf.write(data.encode('utf-8'))
                                    else:
                                        wf.write(data)
                                file_path = out_path
                            except Exception:
                                file_path = None
                    except Exception:
                        file_path = None
                    if not file_path or not file_path.exists():
                        QMessageBox.warning(dlg, "Archivo no encontrado", f"El fichero esperado no existe en:\n{EXPORTS_BD / filename}\nAsegúrate de haber exportado el PDF desde esta máquina o colócalo en exports/bd/.")
                        return
                try:
                    if sys.platform.startswith("win"):
                        os.startfile(str(file_path))
                    else:
                        webbrowser.open(str(file_path))
                except Exception as e:
                    QMessageBox.critical(dlg, "Error", f"No se pudo abrir PDF: {e}")

        listw.itemSelectionChanged.connect(show_info)
        refresh_btn.clicked.connect(populate)
        open_btn.clicked.connect(open_selected)
        close_btn.clicked.connect(dlg.accept)

        populate()
        dlg.exec()

    # ---------------- UI update ----------------
    def update_ui(self):
        if self.sensor_last_state:
            self.sensor_status_label.setText("🔴 Sensor: Bloqueado")
            if self.current_theme == "dark":
                self.sensor_status_label.setStyleSheet("padding:6px; border-radius:6px; background:#4a1620; color:#ffdcdc; font-weight:700;")
            else:
                self.sensor_status_label.setStyleSheet("padding:6px; border-radius:6px; background:#ffdede; color:#8b1a1a; font-weight:700;")
        else:
            self.sensor_status_label.setText("🟢 Sensor: Libre")
            if self.current_theme == "dark":
                self.sensor_status_label.setStyleSheet("padding:6px; border-radius:6px; background:#163b20; color:#dfffe6; font-weight:700;")
            else:
                self.sensor_status_label.setStyleSheet("padding:6px; border-radius:6px; background:#dff5e0; color:#1a8f2a; font-weight:700;")

        self.counter_label.setText(f"📡  Contador (sensor): {self.total_counter}")

        for i in range(3):
            state = self.led_states[i]
            lbl = self.led_state_labels[i]
            btn = self.led_buttons_toggle[i]
            if state:
                lbl.setText("🟢  ON")
                btn.setText("⚪  Apagar")
                if self.current_theme == "dark":
                    lbl.setStyleSheet("padding:6px; border-radius:6px; background:#1a6b2a; color:#e6fff0; font-weight:700;")
                else:
                    lbl.setStyleSheet("padding:6px; border-radius:6px; background:#dff5e0; color:#1a8f2a; font-weight:700;")
            else:
                lbl.setText("⚪  OFF")
                btn.setText("🟢  Encender")
                if self.current_theme == "dark":
                    lbl.setStyleSheet("padding:6px; border-radius:6px; background:#131a22; color:#9fb0c8; font-weight:700;")
                else:
                    lbl.setStyleSheet("padding:6px; border-radius:6px; background:#f2f5f9; color:#6c7a89; font-weight:700;")

        state4 = self.led_states[3]
        lbl4 = self.led_state_labels[3]
        if state4:
            lbl4.setText("🟢  ON")
            if self.current_theme == "dark":
                lbl4.setStyleSheet("padding:6px; border-radius:6px; background:#1a6b2a; color:#e6fff0; font-weight:700;")
            else:
                lbl4.setStyleSheet("padding:6px; border-radius:6px; background:#dff5e0; color:#1a8f2a; font-weight:700;")
        else:
            lbl4.setText("⚪  OFF")
            if self.current_theme == "dark":
                lbl4.setStyleSheet("padding:6px; border-radius:6px; background:#131a22; color:#9fb0c8; font-weight:700;")
            else:
                lbl4.setStyleSheet("padding:6px; border-radius:6px; background:#f2f5f9; color:#6c7a89; font-weight:700;")

        recent = self.history[-200:]
        lines = [f"{t[0]} - LED {t[1]} - {t[2]}" for t in recent]
        txt = "\n".join(lines)
        self.events_view.setPlainText(txt)
        cursor = self.events_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.events_view.setTextCursor(cursor)

        if not (self.serial_thread and self.serial_thread.isRunning()):
            self.connect_btn.setText("🔌  Conectar")

    def on_toggle_theme(self):
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self.apply_theme(self.current_theme)

    def closeEvent(self, event):
        save_settings({"theme": self.current_theme})
        if self.serial_thread and self.serial_thread.isRunning():
            self.serial_thread.stop()
        self.stop_simulation()
        super().closeEvent(event)


# ---------- orphan windows cleaner ----------
def close_orphan_windows():
    app = QApplication.instance()
    if app is None:
        return
    for w in list(app.topLevelWidgets()):
        try:
            if not isinstance(w, QWidget):
                continue
            title = (w.windowTitle() or "").strip()
            wsize = w.size()
            if title == "" and wsize.width() <= 160 and wsize.height() <= 160:
                w.close()
        except Exception:
            pass


# ---------- main ----------
def main():
    app = QApplication(sys.argv)

    if LoginController is not None:
        login_win = LoginController()
        login_win.show()
        QTimer.singleShot(200, close_orphan_windows)
        sys.exit(app.exec())
        return

    w = MainWindow(username="local")
    w.show()
    QTimer.singleShot(200, close_orphan_windows)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
