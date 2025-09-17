from PyQt6.QtCore import QThread, pyqtSignal
import time
import re

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

    def hardware_reset(self, pulse_ms: float = 0.05) -> bool:
        """
        Perform a hardware reset by toggling DTR/RTS lines on the open serial port.
        If the internal serial is not open, try opening a temporary Serial to perform the pulse.
        Returns True on success, False otherwise.
        """
        if serial is None:
            return False

        try:
            if self.ser and getattr(self.ser, 'is_open', False):
                try:
                    # apply a short pulse
                    self.ser.setDTR(False)
                    self.ser.setRTS(True)
                    time.sleep(pulse_ms)
                    self.ser.setDTR(True)
                    self.ser.setRTS(False)
                    return True
                except Exception:
                    # fallthrough to try temporary open
                    pass

            # try opening a temporary serial port to pulse DTR/RTS
            tmp = None
            try:
                tmp = serial.Serial(self.port, self.baud, timeout=1)
                tmp.setDTR(False)
                tmp.setRTS(True)
                time.sleep(pulse_ms)
                tmp.setDTR(True)
                tmp.setRTS(False)
                try:
                    tmp.close()
                except Exception:
                    pass
                return True
            except Exception:
                try:
                    if tmp:
                        tmp.close()
                except Exception:
                    pass
                return False
        except Exception:
            return False

    @staticmethod
    def hardware_reset_port(port: str, baud: int = 115200, pulse_ms: float = 0.05) -> bool:
        """Static helper: perform hardware reset on given port even if no SerialThread exists."""
        if serial is None:
            return False
        try:
            tmp = serial.Serial(port, baud, timeout=1)
            tmp.setDTR(False)
            tmp.setRTS(True)
            time.sleep(pulse_ms)
            tmp.setDTR(True)
            tmp.setRTS(False)
            try:
                tmp.close()
            except Exception:
                pass
            return True
        except Exception:
            try:
                tmp.close()
            except Exception:
                pass
            return False

    @staticmethod
    def detect_esp32_port(port: str, baud: int = 115200, timeout: float = 1.5) -> bool:
        """
        Heurística para detectar si el dispositivo en `port` es un ESP32.
        - Primero inspecciona `serial.tools.list_ports` buscando VID/PID/description conocidas.
        - Si eso no confirma, intenta un pulso DTR corto para forzar mensajes de arranque
          y busca patrones típicos en la salida serie (p.ej. 'ets', 'rst:', 'ESP32').
        Devuelve True si parece ESP32, False si no.
        """
        if serial is None:
            return False

        try:
            ports = list(serial.tools.list_ports.comports())
            for p in ports:
                try:
                    if p.device == port:
                        info = " ".join([str(p.vid or ''), str(p.pid or ''), str(p.manufacturer or ''), str(p.product or ''), str(p.description or '')])
                        info_l = info.lower()
                        # common markers for ESP32 dev boards / usb-serial chips
                        markers = ["silicon labs", "cp210", "ch340", "ch915", "ftdi", "usb-serial", "esp32", "espressif"]
                        for m in markers:
                            if m in info_l:
                                return True
                except Exception:
                    continue

            # fallback: open port, pulse DTR to force boot messages, read output
            ser = None
            try:
                ser = serial.Serial(port, baud, timeout=0.2)
                # pulse DTR/RTS
                try:
                    ser.setDTR(False)
                    ser.setRTS(True)
                    time.sleep(0.05)
                    ser.setDTR(True)
                    ser.setRTS(False)
                except Exception:
                    pass

                deadline = time.time() + timeout
                buf = ""
                while time.time() < deadline:
                    try:
                        if ser.in_waiting:
                            chunk = ser.read(ser.in_waiting).decode(errors='ignore')
                            buf += chunk
                            # look for typical ESP32 boot/ROM markers
                            if re.search(r"ets |rst:|esp32|espressif|chip", buf, re.IGNORECASE):
                                try:
                                    ser.close()
                                except Exception:
                                    pass
                                return True
                    except Exception:
                        break
                    time.sleep(0.05)
            except Exception:
                pass
            finally:
                try:
                    if ser and ser.is_open:
                        ser.close()
                except Exception:
                    pass

        except Exception:
            return False

        return False
