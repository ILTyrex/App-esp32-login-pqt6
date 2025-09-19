from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QMessageBox, QComboBox, QPlainTextEdit, QSizePolicy,
    QDialog, QDialogButtonBox, QListWidget, QRadioButton
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QTextCursor
from functools import partial
from pathlib import Path
from datetime import datetime
from io import BytesIO, StringIO
import re
import csv
import base64

from app.utils.shared import (
    MAX_WIDTH, load_settings, save_settings, EXPORTS_SESSION, EXPORTS_BD,
    REPORTLAB_AVAILABLE, db_save_event, get_or_create_user_id, db_save_export_file,
    db_list_exported, db_fetch_export_file, pdfcanvas
)

import logging
from app.workers.serial_thread import SerialThread
from app.logic import line_processing

logger = logging.getLogger(__name__)


class MainWindow(QWidget):
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.setWindowTitle(f"Protoboard - Usuario: {username}")
        self.resize(900, 640)

        self.history = []

        self.total_counter = 0
        self.led_states = [False, False, False, False]
        self.sensor_last_state = False

        self.serial_thread = None
        # reset ACK handling
        self._waiting_reset_ack = False
        self._reset_ack_timer = QTimer(self)
        self._reset_ack_timer.setSingleShot(True)
        self._reset_ack_timer.timeout.connect(self._on_reset_ack_timeout)

    # Port scan timer for auto-detection
        self._port_scan_timer = QTimer(self)
        self._port_scan_timer.setInterval(1500)
        self._port_scan_timer.timeout.connect(self._scan_ports)
        self._port_scan_timer.start()

        # small debounce to avoid rapid reconnect attempts
        self._last_autoconnect_port = None
        self._last_autoconnect_ts = 0

        settings = load_settings()
        self.current_theme = settings.get("theme", "light")

        self.db_user_id = None
        self.db_available = False
        try:
            if get_or_create_user_id is not None:
                self.db_user_id = get_or_create_user_id(self.username)
                if self.db_user_id:
                    self.db_available = True
        except Exception:
            logger.exception("DB init error")
            self.db_user_id = None
            self.db_available = False

        self.build_ui_centered()
        self.apply_theme(self.current_theme)
        self.update_ui()

        try:
            from app import serial as _serial_pkg
            if getattr(_serial_pkg, 'serial_ui', None) is not None:
                try:
                    _serial_pkg.serial_ui._scan_ports(self)
                except Exception:
                    pass
        except Exception:
            logger.exception("Error initializing serial ports list")

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
        try:
            import serial
            ports = [p.device for p in serial.tools.list_ports.comports()]
        except Exception:
            ports = []
        self.port_combo.addItems(ports)
        try:
            if "COM1" not in ports:
                self.port_combo.addItem("COM1")
            idx = self.port_combo.findText("COM1")
            if idx >= 0:
                self.port_combo.setCurrentIndex(idx)
        except Exception:
            pass
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
        try:
            import serial
            note.setText("ESP32 debe enviar: BTN:1..3 (pulsadores), SENSOR:1/0 (sensor) y opcional ACK:LED:n:v.")
        except Exception:
            note.setText("pyserial no instalado o no disponible. Conecta el ESP32 para funcionalidades seriales.")
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

    # Serial
    def toggle_connection(self):
        try:
            from app.serial import serial_ui
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Módulo serial no disponible: {e}")
            return False
        return serial_ui.toggle_connection(self)

    def _scan_ports(self):
        try:
            from app.serial import serial_ui
        except Exception:
            try:
                self.port_combo.clear()
            except Exception:
                pass
            return None
        return serial_ui._scan_ports(self)

    def on_connected(self, ok):
        try:
            from app.serial import serial_ui
        except Exception:
            try:
                if ok:
                    self.connect_btn.setText("🔌  Desconectar")
                else:
                    self.connect_btn.setText("🔌  Conectar")
            except Exception:
                pass
            return None
        return serial_ui.on_connected(self, ok)

    # Line processing
    def on_line(self, line: str):
        return line_processing.on_line(self, line)

    def handle_sensor_activation(self, is_on: bool):
        return line_processing.handle_sensor_activation(self, is_on)

    def gui_toggle_led(self, idx: int):
        return line_processing.gui_toggle_led(self, idx)

    def reset_total(self):
        return line_processing.reset_total(self)

    def _on_reset_ack_timeout(self):
        return line_processing.on_reset_ack_timeout(self)

    # ---------------- export logic ----------------
    def export_dialog(self):
        try:
            import importlib
            exports_ui = importlib.import_module('app.ui.exports_ui')
            return exports_ui.export_dialog(self)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Módulo de exportación no disponible: {e}")
            return None

    def _safe_timestamp_str(self):
        return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    def export_session(self, format="csv"):
        try:
            import importlib
            exports_ui = importlib.import_module('app.ui.exports_ui')
            return exports_ui.export_session(self, format=format)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Módulo de exportación no disponible: {e}")
            return None

    # ---------------- show CSV in table ----------------
    def show_csv_table(self, csv_path: Path):
        try:
            import importlib
            exports_ui = importlib.import_module('app.ui.exports_ui')
            return exports_ui.show_csv_table(self, csv_path)
        except Exception as e:
            QMessageBox.information(self, "Abrir CSV", f"No se pudo abrir CSV: {e}")
            return None

    # ---------------- view exports (BD-only) ----------------
    def view_exports_dialog(self):
        try:
            import importlib
            exports_ui = importlib.import_module('app.ui.exports_ui')
            return exports_ui.view_exports_dialog(self)
        except Exception as e:
            QMessageBox.information(self, "Ver exportados", f"No se pudo acceder a exportaciones: {e}")
            return None

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
        super().closeEvent(event)
