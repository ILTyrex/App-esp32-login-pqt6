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
    if parent.serial_thread and getattr(parent.serial_thread, 'isRunning', lambda: False)():
        parent.serial_thread.stop()
        try:
            parent.connect_btn.setText("🔌  Conectar")
        except Exception:
            pass
        return False

    port = parent.port_combo.currentText()
    if not port:
        return False
    st = SerialThread(port)
    parent.serial_thread = st
    try:
        st.connected.connect(lambda ok: parent.on_connected(ok))
        st.line_received.connect(lambda line: parent.on_line(line))
    except Exception:
        pass
    st.start()
    try:
        parent.connect_btn.setText("⏳  Conectando...")
    except Exception:
        pass
    return True


def on_connected(parent, ok: bool):
    try:
        if ok:
            parent.connect_btn.setText("🔌  Desconectar")
        else:
            parent.connect_btn.setText("🔌  Conectar")
    except Exception:
        pass
