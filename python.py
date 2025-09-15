# pyqt_serial_counter.py
import sys, time, json
from functools import partial
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QMessageBox, QComboBox, QDialog, QPlainTextEdit, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QTextCursor
from datetime import datetime
import csv

# pyserial opcional
try:
    import serial
    import serial.tools.list_ports
except Exception:
    serial = None

from Login import LoginDialog  # importa el diálogo limpio que guardaste en Login.py

# ancho máximo del contenido: controla los gutters laterales
MAX_WIDTH = 820

# archivo de configuración (JSON) en la misma carpeta del script
SETTINGS_FILE = Path(__file__).parent / "settings.json"


# ----------------- Helpers para settings (JSON) -----------------
def load_settings():
    """Carga settings desde settings.json. Devuelve dict con defaults si falla."""
    defaults = {"theme": "light"}
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return defaults
            return {**defaults, **data}
    except Exception:
        # si hay error de parseo, regresar defaults
        return defaults
    return defaults


def save_settings(settings: dict):
    """Guarda settings (dict) a settings.json (intenta no romper la app si hay error)."""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("No se pudo guardar settings:", e)


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

        # contador (solo por sensor -> LED4)
        self.total_counter = 0

        # estados de 4 LEDs
        self.led_states = [False, False, False, False]

        # sensor last state
        self.sensor_last_state = False

        # historial
        self.history = []

        self.serial_thread = None

        # simulación
        self.sim_timer = None
        self.sim_interval_ms = 7000

        # tema: cargar desde settings.json
        settings = load_settings()
        self.current_theme = settings.get("theme", "light")

        # UI
        self.build_ui_centered()
        self.apply_theme(self.current_theme)
        self.update_ui()

        if serial is None:
            self.start_simulation()

    # ---------- QSS ----------
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
        # guardar elección inmediatamente
        save_settings({"theme": self.current_theme})
        # actualizar UI dependiente del tema
        self.update_ui()

    # ---------- Construir UI centrado con gutters laterales ----------
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

        # Header
        header = QHBoxLayout()
        title = QLabel("Panel Protoboard")
        title.setObjectName("title")
        header.addWidget(title)

        # Theme button
        self.theme_btn = QPushButton("🌙  Oscuro")
        self.theme_btn.setToolTip("Alternar tema claro/oscuro")
        self.theme_btn.clicked.connect(self.on_toggle_theme)
        self.theme_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        header.addWidget(self.theme_btn)

        header.addStretch()
        content_layout.addLayout(header)

        # Connection card
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

        # Sensor status + contador (centrado debajo de conexión)
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

        # LEDs area (grid) - ahora 1 botón por LED (toggle)
        leds_card = QWidget()
        leds_card.setProperty("class", "card")
        leds_layout = QGridLayout(leds_card)
        leds_layout.setContentsMargins(8, 8, 8, 8)
        leds_layout.setHorizontalSpacing(12)
        leds_layout.setVerticalSpacing(10)

        # Column configuration: 0 label, 1 button (expande), 2 estado
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

            btn = QPushButton("🟢  Encender")  # texto inicial será actualizado por update_ui()
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

        # LED4 sensor (no control app) -> ocupa columna 1 (control area) para simetría
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

        # Bottom: export + reset
        bottom_card = QWidget()
        bottom_card.setProperty("class", "card")
        bottom_layout = QHBoxLayout(bottom_card)
        bottom_layout.setContentsMargins(8, 8, 8, 8)
        bottom_layout.addStretch()
        self.export_btn = QPushButton("💾  Exportar historial")
        self.export_btn.setToolTip("Guardar historial a CSV")
        self.export_btn.clicked.connect(self.export_csv)
        self.export_btn.setMaximumWidth(180)
        self.reset_btn = QPushButton("♻️  Reset contador")
        self.reset_btn.setObjectName("resetBtn")
        self.reset_btn.setToolTip("Reiniciar contador (solo activaciones del sensor)")
        self.reset_btn.clicked.connect(self.reset_total)
        self.reset_btn.setMaximumWidth(160)
        bottom_layout.addWidget(self.export_btn)
        bottom_layout.addWidget(self.reset_btn)
        content_layout.addWidget(bottom_card)

        # Note
        note = QLabel()
        if serial is None:
            note.setText("Modo SIMULACIÓN: pyserial no instalado. Activaciones del sensor se simulan.")
        else:
            note.setText("ESP32 debe enviar: BTN:1..3 (pulsadores), SENSOR:1/0 (sensor) y opcional ACK:LED:n:v.")
        note.setProperty("class", "smallNote")
        content_layout.addWidget(note)

        # Historial (scroll)
        self.events_view = QPlainTextEdit()
        self.events_view.setReadOnly(True)
        self.events_view.setMaximumHeight(200)
        content_layout.addWidget(self.events_view)

        # add content centered with gutters
        center_h.addWidget(content)
        center_h.addStretch()
        outer.addLayout(center_h)

    # ---------- Serial / simulation ----------
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

    # ---------- Line processing ----------
    def on_line(self, line: str):
        line = line.strip()
        if not line:
            return
        print("FROM ESP32:", line)

        up = line.upper()

        # Pulsadores físicos
        if up.startswith("BTN:"):
            try:
                idx = int(line.split(":")[1]) - 1
                if 0 <= idx <= 2:
                    # pulsador físico enciende su led (no aumenta contador)
                    self.led_states[idx] = True
                    self.history.append((datetime.now().isoformat(), idx+1, "BTN"))
                    self.update_ui()
                elif idx == 3:
                    # si ESP envía BTN:4 se considera sensor ON
                    self.handle_sensor_activation(True)
            except Exception:
                pass
            return

        # ACK:LED:n:v
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
                        if idx == 3:
                            self.handle_sensor_activation(state)
                        self.update_ui()
                except Exception:
                    pass
            return

        # Sensor/proximity
        if up.startswith("SENSOR:") or up.startswith("PROX:"):
            try:
                parts = line.split(":")
                val = parts[1] if len(parts) > 1 else ""
                is_on = (val == "1" or val.upper() == "ON" or val.upper() == "TRUE")
                self.handle_sensor_activation(is_on)
            except Exception:
                pass
            return

        # Otros
        self.history.append((datetime.now().isoformat(), 0, line))
        self.update_ui()

    def handle_sensor_activation(self, is_on: bool):
        prev = self.sensor_last_state
        self.sensor_last_state = is_on

        # actualizar LED4
        self.led_states[3] = is_on

        if (not prev) and is_on:
            # solo aumentar cuando pasa de 0 -> 1
            self.total_counter += 1
            self.history.append((datetime.now().isoformat(), 4, "SENSOR_ON"))
        else:
            self.history.append((datetime.now().isoformat(), 4, "SENSOR_ON" if is_on else "SENSOR_OFF"))

        self.update_ui()

    # ---------- GUI actions ----------
    def gui_toggle_led(self, idx: int):
        """Alterna estado: si está ON -> envía apagar; si OFF -> enviar encender."""
        if idx == 3:
            QMessageBox.information(self, "Información", "LED4 es controlado por el sensor y no puede activarse desde la app.")
            return

        new_state = not self.led_states[idx]
        # enviar comando al ESP32 si está conectado
        if self.serial_thread and self.serial_thread.isRunning():
            cmd = f"LED:{idx+1}:{'1' if new_state else '0'}"
            self.serial_thread.write(cmd)
            # optimistamente actualizamos el estado local (ACK puede corregir después)
            self.led_states[idx] = new_state
            self.history.append((datetime.now().isoformat(), idx+1, f"GUI_TOGGLE:{'1' if new_state else '0'}"))
            self.update_ui()
        else:
            # simulación local
            self.led_states[idx] = new_state
            action = "ON (GUI)" if new_state else "OFF (GUI)"
            self.history.append((datetime.now().isoformat(), idx+1, action))
            self.update_ui()

    def reset_total(self):
        confirm = QMessageBox.question(self, "Confirmar reset",
                                       "¿Deseas reiniciar el contador (solo cuenta activaciones del sensor)?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            self.total_counter = 0
            self.history.append((datetime.now().isoformat(), 0, "RESET"))
            self.update_ui()

    def export_csv(self):
        fn = f"historial_{int(time.time())}.csv"
        with open(fn, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "led", "action"])
            for row in self.history:
                writer.writerow(row)
        QMessageBox.information(self, "Exportado", f"Historial guardado en {fn}")

    # ---------- UI update ----------
    def update_ui(self):
        # indicador explícito del sensor (bloqueado / libre)
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

        # contador (con icono)
        self.counter_label.setText(f"📡  Contador (sensor): {self.total_counter}")

        # LED states labels & toggle buttons text
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

        # LED4 label
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

        # events recent -> QPlainTextEdit con scroll
        recent = self.history[-200:]
        lines = [f"{t[0]} - LED {t[1]} - {t[2]}" for t in recent]
        txt = "\n".join(lines)
        self.events_view.setPlainText(txt)
        cursor = self.events_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.events_view.setTextCursor(cursor)

        # actualizar connect button icon/text si no conectado (in case)
        if not (self.serial_thread and self.serial_thread.isRunning()):
            self.connect_btn.setText("🔌  Conectar")

    # ---------- Theme ----------
    def on_toggle_theme(self):
        # alterna y aplica; apply_theme ya guarda settings
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self.apply_theme(self.current_theme)

    # ---------- cleanup ----------
    def closeEvent(self, event):
        # guardar settings antes de salir
        save_settings({"theme": self.current_theme})
        if self.serial_thread and self.serial_thread.isRunning():
            self.serial_thread.stop()
        self.stop_simulation()
        super().closeEvent(event)


# ----------------- Arranque -----------------
def main():
    app = QApplication(sys.argv)

    login = LoginDialog()
    if login.exec() == QDialog.DialogCode.Accepted:
        user = login.result_username
        w = MainWindow(username=user)
        w.show()
        sys.exit(app.exec())
    else:
        print("Login cancelado.")
        sys.exit(0)


if __name__ == "__main__":
    main()
