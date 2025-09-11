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
        # Si pyserial no está, indicar desconectado
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


# ----------------- Ventana principal simplificada -----------------
class MainWindow(QWidget):
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.setWindowTitle(f"Contador LEDs - Usuario: {username}")
        self.resize(520, 300)

        self.total_counter = 0

        self.led_states = [False, False, False]

        self.history = []

        self.serial_thread = None

        self.build_ui()
        self.update_ui()

    def build_ui(self):
        main = QVBoxLayout()

        conn_layout = QHBoxLayout()
        self.port_combo = QComboBox()
        ports = []
        if serial is not None:
            try:
                ports = [p.device for p in serial.tools.list_ports.comports()]
            except Exception:
                ports = []
        self.port_combo.addItems(ports)
        self.connect_btn = QPushButton("Conectar")
        self.connect_btn.clicked.connect(self.toggle_connection)
        conn_layout.addWidget(QLabel("Puerto:"))
        conn_layout.addWidget(self.port_combo)
        conn_layout.addWidget(self.connect_btn)
        main.addLayout(conn_layout)

        ctr_layout = QHBoxLayout()
        self.counter_label = QLabel("Contador total: 0")
        self.counter_label.setStyleSheet("font-weight:bold; font-size:16px;")
        ctr_layout.addWidget(self.counter_label)
        ctr_layout.addStretch()
        self.reset_btn = QPushButton("Reset contador")
        self.reset_btn.clicked.connect(self.reset_total)
        ctr_layout.addWidget(self.reset_btn)
        main.addLayout(ctr_layout)

        # Botones para cada LED (toggle) + etiqueta de estado
        leds_layout = QGridLayout()
        self.led_buttons = []
        self.led_state_labels = []
        for i in range(3):
            btn = QPushButton(f"Encender/Apagar LED {i+1}")
            btn.clicked.connect(lambda _, x=i: self.toggle_led_gui(x))
            state_lbl = QLabel("OFF")
            state_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            state_lbl.setStyleSheet("font-weight:bold;")
            self.led_buttons.append(btn)
            self.led_state_labels.append(state_lbl)
            leds_layout.addWidget(btn, i, 0)
            leds_layout.addWidget(state_lbl, i, 1)
        main.addLayout(leds_layout)

        # Botón exportar historial (opcional)
        bottom = QHBoxLayout()
        self.export_btn = QPushButton("Exportar historial CSV")
        self.export_btn.clicked.connect(self.export_csv)
        bottom.addStretch()
        bottom.addWidget(self.export_btn)
        main.addLayout(bottom)

        self.event_label = QLabel("Eventos recientes:")
        main.addWidget(self.event_label)

        if serial is None:
            note = QLabel("<i>pyserial no instalado: la app funciona en modo simulación (sin puerto físico).</i>")
            main.addWidget(note)

        self.setLayout(main)

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
                    self.led_state_labels[idx].setText("ON")
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
                        self.led_state_labels[idx].setText("ON" if state else "OFF")
                except Exception:
                    pass
                self.update_ui()
        else:
            self.history.append((datetime.now().isoformat(), 0, line))
            self.update_ui()

    def update_ui(self):
        self.counter_label.setText(f"Contador total: {self.total_counter}")
        for i in range(3):
            self.led_state_labels[i].setText("ON" if self.led_states[i] else "OFF")
        recent = self.history[-6:]
        txt = "Eventos recientes:\n" + "\n".join([f"{t[0]} - LED {t[1]} - {t[2]}" for t in recent])
        self.event_label.setText(txt)

    def toggle_led_gui(self, idx):
        """Toggle de LED desde la GUI (envía por serial si está conectado;
           en modo simulación cambia estado local y aumenta el contador)."""
        new_state = not self.led_states[idx]
        if self.serial_thread and self.serial_thread.isRunning():
            cmd = f"LED:{idx+1}:{'1' if new_state else '0'}"
            self.serial_thread.write(cmd)
            self.led_state_labels[idx].setText("ON" if new_state else "OFF")
        else:

            self.led_states[idx] = new_state
            self.led_state_labels[idx].setText("ON" if new_state else "OFF")
            if new_state:
                self.total_counter += 1
                self.history.append((datetime.now().isoformat(), idx+1, "ON (GUI)"))
            else:
                self.history.append((datetime.now().isoformat(), idx+1, "OFF (GUI)"))
            self.update_ui()

    def reset_total(self):
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
