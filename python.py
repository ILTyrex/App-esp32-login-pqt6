# pyqt_serial_counter.py
import sys, time
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QGroupBox, QMessageBox, QLineEdit, QComboBox, QDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from datetime import datetime
import csv

try:
    import serial
    import serial.tools.list_ports
except Exception:
    serial = None

# Importar solo LoginDialog (no init_db, porque ya no usamos DB)
from Login import LoginDialog


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


class MainWindow(QWidget):
    def __init__(self, username):
        super().__init__()
        self.setWindowTitle(f"Contador LEDs - Usuario: {username}")
        self.resize(700, 400)
        self.counters = [0, 0, 0]
        self.history = []
        self.serial_thread = None

        self.build_ui()
        self.update_ui()

    def build_ui(self):
        layout = QVBoxLayout()

        # Config serial
        cfg_layout = QHBoxLayout()
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
        cfg_layout.addWidget(QLabel("Puerto:"))
        cfg_layout.addWidget(self.port_combo)
        cfg_layout.addWidget(self.connect_btn)
        layout.addLayout(cfg_layout)

        # Cards for 3 LEDs
        grid = QGridLayout()
        self.lbl_states = []
        self.lbl_counts = []
        for i in range(3):
            box = QGroupBox(f"LED {i+1}")
            v = QVBoxLayout()
            state = QLabel("OFF")
            state.setAlignment(Qt.AlignmentFlag.AlignCenter)
            state.setStyleSheet("font-weight:bold;")
            count = QLabel("0")
            count.setAlignment(Qt.AlignmentFlag.AlignCenter)
            btn_gui = QPushButton("Toggle GUI")
            btn_gui.clicked.connect(lambda _, x=i: self.toggle_led_gui(x))
            btn_reset = QPushButton("Reset contador")
            btn_reset.clicked.connect(lambda _, x=i: self.reset_counter(x))
            v.addWidget(state)
            v.addWidget(QLabel("Contador:"))
            v.addWidget(count)
            v.addWidget(btn_gui)
            v.addWidget(btn_reset)
            box.setLayout(v)
            grid.addWidget(box, 0, i)
            self.lbl_states.append(state)
            self.lbl_counts.append(count)

        layout.addLayout(grid)

        # Total y export
        bottom = QHBoxLayout()
        self.total_label = QLabel("Total: 0")
        save_btn = QPushButton("Exportar historial CSV")
        save_btn.clicked.connect(self.export_csv)
        bottom.addWidget(self.total_label)
        bottom.addStretch()
        bottom.addWidget(save_btn)
        layout.addLayout(bottom)

        # Eventos (simple)
        self.event_label = QLabel("Eventos recientes:")
        layout.addWidget(self.event_label)

        self.setLayout(layout)

    def toggle_connection(self):
        if self.serial_thread and self.serial_thread.isRunning():
            self.serial_thread.stop()
            self.serial_thread = None
            self.connect_btn.setText("Conectar")
            return
        port = self.port_combo.currentText()
        if not port:
            QMessageBox.warning(self, "Error", "Selecciona un puerto serial.")
            return
        self.serial_thread = SerialThread(port, 115200)
        self.serial_thread.line_received.connect(self.on_line)
        self.serial_thread.connected.connect(self.on_connected)
        self.serial_thread.start()

    def on_connected(self, ok):
        if ok:
            self.connect_btn.setText("Desconectar")
        else:
            self.connect_btn.setText("Conectar")
            QMessageBox.critical(self, "Serial", "No se pudo conectar al puerto (o pyserial no está instalado).")

    def on_line(self, line: str):
        print("FROM ESP32:", line)
        if line.startswith("BTN:"):
            try:
                idx = int(line.split(":")[1]) - 1
                if 0 <= idx < 3:
                    self.counters[idx] += 1
                    self.history.append((datetime.now().isoformat(), idx + 1, "ON"))
                    self.lbl_states[idx].setText("ON")
                    self.update_ui()
            except Exception:
                pass
        elif line.startswith("ACK:LED:"):
            parts = line.split(":")
            if len(parts) >= 4:
                idx = int(parts[2]) - 1
                val = parts[3]
                self.lbl_states[idx].setText("ON" if val == "1" else "OFF")
        else:
            self.history.append((datetime.now().isoformat(), 0, line))
            self.update_ui()

    def update_ui(self):
        for i in range(3):
            self.lbl_counts[i].setText(str(self.counters[i]))
        total = sum(self.counters)
        self.total_label.setText(f"Total: {total}")
        recent = self.history[-5:]
        txt = "Eventos recientes:\n" + "\n".join([f"{t[0]} - LED {t[1]} - {t[2]}" for t in recent])
        self.event_label.setText(txt)

    def toggle_led_gui(self, idx):
        cur = self.lbl_states[idx].text()
        val = "0" if cur == "ON" else "1"
        if self.serial_thread:
            self.serial_thread.write(f"LED:{idx+1}:{val}")
        else:
            # simulación local si no hay serial
            self.lbl_states[idx].setText("ON" if val == "1" else "OFF")
            if val == "1":
                self.counters[idx] += 1
                self.history.append((datetime.now().isoformat(), idx + 1, "ON (GUI)"))
            self.update_ui()

    def reset_counter(self, idx):
        self.counters[idx] = 0
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
