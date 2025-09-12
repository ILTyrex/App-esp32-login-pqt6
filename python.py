# pyqt_serial_counter.py
import sys, time
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QMessageBox, QComboBox, QDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from datetime import datetime
import csv

try:
    import serial
    import serial.tools.list_ports
except Exception:
    serial = None

from Login import LoginDialog

# ----------------- Hilo serial -----------------
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


# ----------------- Ventana principal con temas -----------------
class MainWindow(QWidget):
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.setWindowTitle(f"Contador LEDs - Usuario: {username}")
        self.resize(620, 380)

        self.total_counter = 0
        self.led_states = [False, False, False]
        self.history = []
        self.serial_thread = None

        self.current_theme = "light"

        self.build_ui()
        self.apply_theme(self.current_theme)
        self.update_ui()

    # --------- QSS para los temas ---------
    def qss_light(self):
        return """
        QWidget {
            background: #f3f6fb;
            font-family: "Segoe UI", Roboto, Arial, sans-serif;
            color: #222;
        }
        QLabel#title {
            font-size: 20px;
            font-weight: 700;
            color: #23395d;
        }
        QLabel#counter {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #6a89ff, stop:1 #5ecbe6);
            color: white;
            padding: 10px 16px;
            border-radius: 10px;
            font-size: 18px;
            font-weight: 700;
            min-width: 220px;
        }
        QPushButton {
            background: white;
            border: 1px solid #d7e0ef;
            padding: 8px 12px;
            border-radius: 10px;
            font-weight: 600;
        }
        QPushButton:hover {
            background: #f0f6ff;
            border: 1px solid #adcfff;
        }
        QPushButton:pressed {
            background: #e6f0ff;
        }
        QPushButton#connectBtn {
            background: #23395d;
            color: white;
            border: none;
            min-width: 110px;
        }
        QPushButton#connectBtn:hover {
            background: #1b2d4a;
        }
        QPushButton#resetBtn {
            background: #ff6b6b;
            color: white;
            border: none;
        }
        QWidget.card {
            background: white;
            border-radius: 10px;
            padding: 10px;
            border: 1px solid rgba(0,0,0,0.04);
        }
        QLabel.smallNote { color: #6c7a89; font-size: 12px; }
        """

    def qss_dark(self):
        return """
        QWidget {
            background: #0f1724;
            font-family: "Segoe UI", Roboto, Arial, sans-serif;
            color: #e6eef8;
        }
        QLabel#title {
            font-size: 20px;
            font-weight: 700;
            color: #9bd1ff;
        }
        QLabel#counter {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #2b6bff, stop:1 #00c1d4);
            color: #021029;
            padding: 10px 16px;
            border-radius: 10px;
            font-size: 18px;
            font-weight: 700;
            min-width: 220px;
        }
        QPushButton {
            background: #101826;
            border: 1px solid #243444;
            padding: 8px 12px;
            border-radius: 10px;
            font-weight: 600;
            color: #e6eef8;
        }
        QPushButton:hover {
            background: #162134;
            border: 1px solid #3a5a7a;
        }
        QPushButton:pressed {
            background: #0e1726;
        }
        QPushButton#connectBtn {
            background: #0b2946;
            color: #bfe7ff;
            border: 1px solid #24455f;
        }
        QPushButton#resetBtn {
            background: #b94a4a;
            color: white;
            border: none;
        }
        QWidget.card {
            background: #0b1520;
            border-radius: 10px;
            padding: 10px;
            border: 1px solid #112233;
        }
        QLabel.smallNote { color: #9fb0c8; font-size: 12px; }
        """

    def apply_theme(self, theme: str):
        """Aplica el tema 'light' o 'dark' globalmente."""
        if theme == "dark":
            self.setStyleSheet(self.qss_dark())
            self.theme_btn.setText("Claro")
        else:
            self.setStyleSheet(self.qss_light())
            self.theme_btn.setText("Oscuro")
        self.current_theme = theme
        self.update_ui()

    # --------- UI ---------
    def build_ui(self):
        main = QVBoxLayout()
        main.setContentsMargins(16, 16, 16, 16)
        main.setSpacing(12)

        header_layout = QHBoxLayout()
        title = QLabel("Panel de control")
        title.setObjectName("title")
        header_layout.addWidget(title)

        self.theme_btn = QPushButton("Oscuro")
        self.theme_btn.setToolTip("Alternar tema claro/oscuro")
        self.theme_btn.clicked.connect(self.on_toggle_theme)
        header_layout.addWidget(self.theme_btn)

        header_layout.addStretch()
        self.counter_label = QLabel("Contador total: 0")
        self.counter_label.setObjectName("counter")
        header_layout.addWidget(self.counter_label)
        main.addLayout(header_layout)

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
        self.connect_btn = QPushButton("Conectar")
        self.connect_btn.setObjectName("connectBtn")
        self.connect_btn.clicked.connect(self.toggle_connection)
        conn_layout.addWidget(QLabel("Puerto:"))
        conn_layout.addWidget(self.port_combo)
        conn_layout.addStretch()
        conn_layout.addWidget(self.connect_btn)
        main.addWidget(conn_card)

        self.led_buttons = []
        self.led_state_labels = []
        for i in range(3):
            row_card = QWidget()
            row_card.setProperty("class", "card")
            row_layout = QHBoxLayout(row_card)
            row_layout.setContentsMargins(10, 8, 10, 8)
            row_layout.setSpacing(12)

            led_btn = QPushButton(f"Encender LED {i+1}")
            led_btn.setProperty("ledIndex", i)
            led_btn.clicked.connect(lambda _, x=i: self.toggle_led_gui(x))

            state_lbl = QLabel("OFF")
            state_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            state_lbl.setFixedWidth(60)

            row_layout.addWidget(led_btn, stretch=1)
            row_layout.addWidget(state_lbl, stretch=0)
            main.addWidget(row_card)

            self.led_buttons.append(led_btn)
            self.led_state_labels.append(state_lbl)

        bottom_card = QWidget()
        bottom_card.setProperty("class", "card")
        bottom_layout = QHBoxLayout(bottom_card)
        bottom_layout.setContentsMargins(8, 8, 8, 8)
        bottom_layout.setSpacing(10)
        self.reset_btn = QPushButton("Reset contador")
        self.reset_btn.setObjectName("resetBtn")
        self.reset_btn.clicked.connect(self.reset_total)
        self.export_btn = QPushButton("Exportar historial CSV")
        self.export_btn.clicked.connect(self.export_csv)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.export_btn)
        bottom_layout.addWidget(self.reset_btn)
        main.addWidget(bottom_card)

        note = QLabel()
        if serial is None:
            note.setText("pyserial no instalado: la app funciona en modo simulación (sin puerto físico).")
        else:
            note.setText("Conecta tu ESP32 y selecciona el puerto. El dispositivo debe enviar 'BTN:n' o 'ACK:LED:n:v'.")
        note.setProperty("class", "smallNote")
        main.addWidget(note)

        self.event_label = QLabel("Eventos recientes:")
        self.event_label.setProperty("class", "smallNote")
        main.addWidget(self.event_label)

        self.setLayout(main)

    # --------- Conexión serial ---------
    def toggle_connection(self):
        if self.serial_thread and self.serial_thread.isRunning():
            self.serial_thread.stop()
            self.serial_thread = None
            self.connect_btn.setText("Conectar")
            return

        port = self.port_combo.currentText()
        if not port:
            QMessageBox.warning(self, "Error", "Selecciona un puerto serial (o instala pyserial).")
            return

        self.serial_thread = SerialThread(port, 115200)
        self.serial_thread.line_received.connect(self.on_line)
        self.serial_thread.connected.connect(self.on_connected)
        self.serial_thread.start()

    def on_connected(self, ok):
        if ok:
            self.connect_btn.setText("Desconectar")
            QMessageBox.information(self, "Serial", "Conectado al puerto serial.")
        else:
            self.connect_btn.setText("Conectar")
            QMessageBox.critical(self, "Serial", "No se pudo conectar al puerto (o pyserial no está instalado).")

    # --------- Manejo mensajes ESP32 ---------
    def on_line(self, line: str):
        """Maneja mensajes desde ESP32. Protocolo: BTN:n  o ACK:LED:n:v"""
        print("FROM ESP32:", line)
        if line.startswith("BTN:"):
            try:
                idx = int(line.split(":")[1]) - 1
                if 0 <= idx < 3:
                    self.total_counter += 1
                    self.history.append((datetime.now().isoformat(), idx+1, "BTN"))
                    self.led_states[idx] = True
                    self.update_ui()
            except Exception:
                pass
        elif line.startswith("ACK:LED:"):
            parts = line.split(":")
            if len(parts) >= 4:
                try:
                    idx = int(parts[2]) - 1
                    val = parts[3]
                    state = (val == "1")
                    if 0 <= idx < 3:
                        self.led_states[idx] = state
                        self.history.append((datetime.now().isoformat(), idx+1, f"ACK:{val}"))
                        self.update_ui()
                except Exception:
                    pass
        else:

            self.history.append((datetime.now().isoformat(), 0, line))
            self.update_ui()

    # --------- UI updates ---------
    def update_ui(self):

        self.counter_label.setText(f"Contador total: {self.total_counter}")

        for i in range(3):
            lbl = self.led_state_labels[i]
            state = self.led_states[i]
            if state:
                lbl.setText("ON")
                if self.current_theme == "dark":
                    lbl.setStyleSheet("padding:6px 8px; border-radius:8px; background:#1a6b2a; color:#e6fff0; font-weight:700;")
                else:
                    lbl.setStyleSheet("padding:6px 8px; border-radius:8px; background:#dff5e0; color:#1a8f2a; font-weight:700;")
            else:
                # OFF
                lbl.setText("OFF")
                if self.current_theme == "dark":
                    lbl.setStyleSheet("padding:6px 8px; border-radius:8px; background:#131a22; color:#9fb0c8; font-weight:700;")
                else:
                    lbl.setStyleSheet("padding:6px 8px; border-radius:8px; background:#f2f5f9; color:#6c7a89; font-weight:700;")

        recent = self.history[-6:]
        txt = "Eventos recientes:\n" + "\n".join([f"{t[0]} - LED {t[1]} - {t[2]}" for t in recent])
        self.event_label.setText(txt)

    # --------- Toggle LED desde GUI ---------
    def toggle_led_gui(self, idx):
        new_state = not self.led_states[idx]
        if self.serial_thread and self.serial_thread.isRunning():
            cmd = f"LED:{idx+1}:{'1' if new_state else '0'}"
            self.serial_thread.write(cmd)
            self.led_states[idx] = new_state
            self.update_ui()
        else:
            self.led_states[idx] = new_state
            if new_state:
                self.total_counter += 1
                self.history.append((datetime.now().isoformat(), idx+1, "ON (GUI)"))
            else:
                self.history.append((datetime.now().isoformat(), idx+1, "OFF (GUI)"))
            self.update_ui()

    # --------- Reset, export ---------
    def reset_total(self):
        confirm = QMessageBox.question(self, "Confirmar reset", "¿Deseas reiniciar el contador total?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
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

    # --------- Tema handler ---------
    def on_toggle_theme(self):
        if self.current_theme == "light":
            self.current_theme = "dark"
        else:
            self.current_theme = "light"
        self.apply_theme(self.current_theme)

    def closeEvent(self, event):
        if self.serial_thread and self.serial_thread.isRunning():
            self.serial_thread.stop()
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
