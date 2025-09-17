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

from shared import (
    MAX_WIDTH, load_settings, save_settings, EXPORTS_SESSION, EXPORTS_BD,
    REPORTLAB_AVAILABLE, db_save_event, get_or_create_user_id, db_save_export_file,
    db_list_exported, db_fetch_export_file, pdfcanvas
)

from serial_thread import SerialThread


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
        except Exception as e:
            print("DB init error:", e)
            self.db_user_id = None
            self.db_available = False

        self.build_ui_centered()
        self.apply_theme(self.current_theme)
        self.update_ui()

        try:
            # if serial not available, start simulation; serial_thread module exposes 'serial' variable
            from serial_thread import serial
            if serial is None:
                self.start_simulation()
        except Exception:
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
        try:
            import serial
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
        try:
            import serial
            if serial is None:
                note.setText("Modo SIMULACIÓN: pyserial no instalado. Activaciones del sensor se simulan.")
            else:
                note.setText("ESP32 debe enviar: BTN:1..3 (pulsadores), SENSOR:1/0 (sensor) y opcional ACK:LED:n:v.")
        except Exception:
            note.setText("Modo SIMULACIÓN: pyserial no instalado. Activaciones del sensor se simulan.")
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
            try:
                import serial
                if serial is None:
                    self.start_simulation()
            except Exception:
                self.start_simulation()
            return

        port = self.port_combo.currentText()
        if not port:
            QMessageBox.warning(self, "Error", "Selecciona un puerto serial.")
            return

        # Detectar si el puerto seleccionado probablemente pertenece a un ESP32
        try:
            is_esp = SerialThread.detect_esp32_port(port, 115200)
        except Exception:
            is_esp = False

        if not is_esp:
            resp = QMessageBox.question(self, "Puerto no identificado",
                                        f"El puerto {port} no parece pertenecer a un ESP32. Deseas conectarte de todas formas?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if resp != QMessageBox.StandardButton.Yes:
                return

        self.stop_simulation()
        self.serial_thread = SerialThread(port, 115200)
        self.serial_thread.line_received.connect(self.on_line)
        self.serial_thread.connected.connect(self.on_connected)
        self.serial_thread.start()

    def _scan_ports(self):
        # Update available ports in the combo and try auto-connect to ESP32
        try:
            import serial
            ports_list = [p.device for p in serial.tools.list_ports.comports()]
        except Exception:
            ports_list = []

        # update combo without losing selection if possible
        curr = self.port_combo.currentText()
        self.port_combo.blockSignals(True)
        try:
            self.port_combo.clear()
            self.port_combo.addItems(ports_list)
            if curr and curr in ports_list:
                idx = self.port_combo.findText(curr)
                if idx >= 0:
                    self.port_combo.setCurrentIndex(idx)
        finally:
            self.port_combo.blockSignals(False)

        # If we're already connected, nothing to do
        if self.serial_thread and self.serial_thread.isRunning():
            return

        # Look for an ESP32 port among available ports
        for p in ports_list:
            try:
                if SerialThread.detect_esp32_port(p, 115200):
                    # debounce: avoid reconnecting the same port too often
                    import time
                    now = time.time()
                    if p == self._last_autoconnect_port and (now - self._last_autoconnect_ts) < 3.0:
                        return
                    self._last_autoconnect_port = p
                    self._last_autoconnect_ts = now
                    # auto-connect
                    self.port_combo.setCurrentText(p)
                    self.toggle_connection()
                    return
            except Exception:
                continue

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

        # handle RESET ack explicitly
        if up.startswith("ACK:RESET"):
            try:
                if self._waiting_reset_ack:
                    self._waiting_reset_ack = False
                    try:
                        self._reset_ack_timer.stop()
                    except Exception:
                        pass
                    # Confirm UI counter already reset locally; ensure sync
                    self.total_counter = 0
                    self.history.append((datetime.now().isoformat(), 0, "ACK:RESET"))
                    if self.db_user_id:
                        db_save_event(self.db_user_id, "RESET_CONTADOR", "CONTADOR", "CIRCUITO", "0")
                    QMessageBox.information(self, "Reset", "Contador reiniciado en ESP32 (ACK recibido).")
                    self.update_ui()
                    return
            except Exception:
                pass

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
            # Only process sensor events when a real ESP32 serial connection is active.
            # This avoids counting sensor-like events from unrelated PC devices.
            if not (self.serial_thread and self.serial_thread.isRunning()):
                # Silently ignore sensor events when ESP32 is not connected.
                return
            try:
                parts = line.split(":")
                val = parts[1] if len(parts) > 1 else ""
                is_on = (val == "1" or val.upper() == "ON" or val.upper() == "TRUE")
                self.handle_sensor_activation(is_on)
            except Exception:
                pass
            return

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
            try:
                # Try logical reset first (device may support it). Wait for ACK, else fallback.
                sent = False
                if self.serial_thread and self.serial_thread.isRunning():
                    self.serial_thread.write("RESET")
                    sent = True
                else:
                    sel = self.port_combo.currentText()
                    if sel:
                        # attempt to send via a temporary connection
                        try:
                            SerialThread.hardware_reset_port(sel, 115200, pulse_ms=0)
                        except Exception:
                            pass
                if sent:
                    # wait for ACK:RESET for up to 1500 ms
                    self._waiting_reset_ack = True
                    self._reset_ack_timer.start(1500)
                    return
                else:
                    # no logical path taken, perform hardware reset
                    sel = self.port_combo.currentText()
                    if sel:
                        SerialThread.hardware_reset_port(sel, 115200)
            except Exception as e:
                print("Reset error:", e)
            if self.db_user_id:
                db_save_event(self.db_user_id, "RESET_CONTADOR", "CONTADOR", "APP", "0")
            self.update_ui()

    def _on_reset_ack_timeout(self):
        # ACK not received in time -> fallback to hardware reset
        try:
            if self._waiting_reset_ack:
                self._waiting_reset_ack = False
                sel = self.port_combo.currentText()
                if sel:
                    SerialThread.hardware_reset_port(sel, 115200)
                QMessageBox.information(self, "Reset", "No se recibió ACK de ESP32; se ejecutó reset hardware como fallback.")
        except Exception as e:
            print("Reset ACK timeout handler error:", e)

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
        if not self.db_available or not self.db_user_id:
            QMessageBox.warning(self, "BD no disponible", "La base de datos no está disponible o el usuario no existe.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Ver archivos exportados (registrados en BD)")
        dlg.resize(700, 480)
        layout = QVBoxLayout(dlg)

        listw = QListWidget()
        layout.addWidget(listw)

        info = QPlainTextEdit()
        info.setReadOnly(True)
        info.setMaximumHeight(160)
        layout.addWidget(info)

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
            seen = set()
            items = []
            for rec in records:
                rec_id, fmt, filename, fecha = rec
                if filename:
                    items.append((rec_id, fmt or '?', filename, fecha))
                    seen.add(filename)
                else:
                    try:
                        content = db_fetch_export_file(rec_id)
                        if content:
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
                    try:
                        data = db_fetch_export_file(parts[0])
                        if data:
                            if isinstance(data, (bytes, bytearray)):
                                try:
                                    txt = data.decode('utf-8')
                                    s_clean = re.sub(r"\s+", "", txt)
                                    if re.fullmatch(r'[A-Za-z0-9+/=]+', s_clean):
                                        try:
                                            decoded2 = base64.b64decode(s_clean)
                                            if decoded2.startswith(b'%PDF') or (b',' in decoded2 and b'\n' in decoded2):
                                                data = decoded2
                                        except Exception as e:
                                            pass
                                except Exception:
                                    pass
                            elif isinstance(data, str):
                                s = data.strip()
                                s_clean = re.sub(r"\s+", "", s)
                                try:
                                    decoded2 = base64.b64decode(s_clean)
                                    if decoded2.startswith(b'%PDF') or (b',' in decoded2 and b'\n' in decoded2):
                                        data = decoded2
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
                file_path = EXPORTS_BD / filename
                if not file_path.exists():
                    file_path = EXPORTS_SESSION / filename
                if not file_path.exists():
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
                    import sys, os, webbrowser
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
