from PyQt6.QtCore import QThread, pyqtSignal

try:
    import serial
    import serial.tools.list_ports
except Exception:
    serial = None


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
        except Exception:
            pass
        self.connected.emit(False)

    def stop(self):
        self._running = False
        self.wait()

    def write(self, data: str):
        if self.ser and self.ser.is_open:
            self.ser.write((data + "\n").encode())
