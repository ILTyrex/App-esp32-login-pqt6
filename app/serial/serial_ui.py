"""Serial UI helpers for MainWindow: connection toggles and port scanning."""
from app.workers.serial_thread import SerialThread

try:
    import serial as _pyserial
except Exception:
    _pyserial = None


def _scan_ports(parent):
    ports = []
    if _pyserial is not None:
        try:
            ports = [p.device for p in _pyserial.tools.list_ports.comports()]
        except Exception:
            ports = []
    try:
        parent.port_combo.clear()
        parent.port_combo.addItems(ports)
    except Exception:
        pass


def toggle_connection(parent):
    # disconnect if already running
    if parent.serial_thread and getattr(parent.serial_thread, 'isRunning', lambda: False)():
        parent.serial_thread.stop()
        try:
            parent.connect_btn.setText("🔌  Conectar")
        except Exception:
            pass
        return False

    # ensure pyserial is available
    try:
        import serial as _pyserial
    except Exception:
        QMessage = None
        try:
            from PyQt6.QtWidgets import QMessageBox as QMessage
        except Exception:
            QMessage = None
        if QMessage:
            try:
                QMessage.information(parent, "Serial no disponible", "pyserial no está instalado o no está disponible en este entorno. Instala 'pyserial' para usar funcionalidades seriales.")
            except Exception:
                pass
        return False

    port = parent.port_combo.currentText()
    if not port:
        # try to auto-detect a likely ESP32 port
        try:
            ports = [p.device for p in _pyserial.tools.list_ports.comports()]
            for p in ports:
                try:
                    if SerialThread.detect_esp32_port(p):
                        port = p
                        break
                except Exception:
                    continue
        except Exception:
            ports = []
        if not port:
            return False

    # quick check: is this port likely an esp32?
    try:
        ok = SerialThread.detect_esp32_port(port)
    except Exception:
        ok = False

    if not ok:
        # still proceed but inform user that the chosen port may not be ESP32
        try:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(parent, "Puerto no verificado", f"El puerto {port} no parece ser un dispositivo ESP32 según heurísticas. Intentando conectar de todas formas.")
        except Exception:
            pass

    st = SerialThread(port)
    parent.serial_thread = st
    try:
        st.connected.connect(lambda ok: parent.on_connected(ok))
        st.line_received.connect(lambda line: parent.on_line(line))
    except Exception:
        pass
    try:
        st.start()
        try:
            parent.connect_btn.setText("⏳  Conectando...")
        except Exception:
            pass
        return True
    except Exception as e:
        try:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(parent, "Error", f"No se pudo iniciar hilo serial: {e}")
        except Exception:
            pass
        return False


def on_connected(parent, ok: bool):
    try:
        if ok:
            parent.connect_btn.setText("🔌  Desconectar")
        else:
            parent.connect_btn.setText("🔌  Conectar")
    except Exception:
        pass
