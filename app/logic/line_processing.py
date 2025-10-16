from datetime import datetime
from PyQt6.QtWidgets import QMessageBox
import re
import base64
import logging

logger = logging.getLogger(__name__)

from app.utils.shared import db_save_event


def on_line(parent, line: str):
    line = line.strip()
    if not line:
        return
    
    up = line.upper()

    # handle RESET ack explicitly
    if up.startswith("ACK:RESET"):
        try:
            if parent._waiting_reset_ack:
                parent._waiting_reset_ack = False
                try:
                    parent._reset_ack_timer.stop()
                except Exception:
                    pass
                parent.total_counter = 0
                parent.history.append((datetime.now().isoformat(), 0, "ACK:RESET"))
                if parent.db_user_id:
                    db_save_event(parent.db_user_id, "RESET_CONTADOR", "CONTADOR", "CIRCUITO", "0")
                QMessageBox.information(parent, "Reset", "Contador reiniciado en ESP32 (ACK recibido).")
                parent.update_ui()
                return
        except Exception:
            pass

    if up.startswith("BTN:"):
        try:
            idx = int(line.split(":")[1]) - 1
            if 0 <= idx <= 2:
                parent.led_states[idx] = True
                parent.history.append((datetime.now().isoformat(), idx+1, "BTN"))
                if parent.db_user_id:
                    # store as numeric for clearer normalization
                    db_save_event(parent.db_user_id, "LED_ON", f"LED{idx+1}", "CIRCUITO", 1)
                parent.update_ui()
            elif idx == 3:
                handle_sensor_activation(parent, True)
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
                    parent.led_states[idx] = state
                    parent.history.append((datetime.now().isoformat(), idx+1, f"ACK:{val}"))
                    if parent.db_user_id and idx < 3:
                                tipo = "LED_ON" if state else "LED_OFF"
                                db_save_event(parent.db_user_id, tipo, f"LED{idx+1}", "CIRCUITO", 1 if state else 0)
                    if idx == 3:
                        handle_sensor_activation(parent, state)
                    parent.update_ui()
            except Exception:
                pass
        return

    if up.startswith("SENSOR:") or up.startswith("PROX:"):
        if not (parent.serial_thread and parent.serial_thread.isRunning()):
            return
        try:
            parts = line.split(":")
            val = parts[1] if len(parts) > 1 else ""
            is_on = (val == "1" or val.upper() == "ON" or val.upper() == "TRUE")
            handle_sensor_activation(parent, is_on)
        except Exception:
            pass
        return

    parent.history.append((datetime.now().isoformat(), 0, line))
    if parent.db_user_id:
        db_save_event(parent.db_user_id, "LED_OFF", "CONTADOR", "CIRCUITO", line[:50])
    parent.update_ui()


def handle_sensor_activation(parent, is_on: bool):
    prev = parent.sensor_last_state
    parent.sensor_last_state = is_on
    parent.led_states[3] = is_on
    if (not prev) and is_on:
        # primera activación (de 0 a 1)
        if getattr(parent, 'serial_thread', None) and getattr(parent.serial_thread, 'isRunning', lambda: False)():
            parent.total_counter += 1
            parent.history.append((datetime.now().isoformat(), 4, "SENSOR_ON"))
            if parent.db_user_id:
                # guardar contador exacto como 'contador=N'
                db_save_event(parent.db_user_id, "SENSOR_BLOQUEADO", "SENSOR_IR", "CIRCUITO", f"contador={parent.total_counter}")
        else:
            parent.history.append((datetime.now().isoformat(), 4, "SENSOR_ON"))
    else:
        # transiciones posteriores o OFF
        parent.history.append((datetime.now().isoformat(), 4, "SENSOR_ON" if is_on else "SENSOR_OFF"))
        if parent.db_user_id:
            if getattr(parent, 'serial_thread', None) and getattr(parent.serial_thread, 'isRunning', lambda: False)():
                tipo = "SENSOR_BLOQUEADO" if is_on else "SENSOR_LIBRE"
                db_save_event(parent.db_user_id, tipo, "SENSOR_IR", "CIRCUITO", 1 if is_on else 0)

    parent.update_ui()


def gui_toggle_led(parent, idx: int):
    if idx == 3:
        QMessageBox.information(parent, "Información", "LED4 es controlado por el sensor y no puede activarse desde la app.")
        return

    new_state = not parent.led_states[idx]
    if parent.serial_thread and parent.serial_thread.isRunning():
        cmd = f"LED:{idx+1}:{'1' if new_state else '0'}"
        parent.serial_thread.write(cmd)
        parent.led_states[idx] = new_state
        parent.history.append((datetime.now().isoformat(), idx+1, f"GUI_TOGGLE:{'1' if new_state else '0'}"))
        if parent.db_user_id:
            tipo = "LED_ON" if new_state else "LED_OFF"
            db_save_event(parent.db_user_id, tipo, f"LED{idx+1}", "APP", "1" if new_state else "0")
        parent.update_ui()
    else:
        parent.led_states[idx] = new_state
        action = "ON (GUI)" if new_state else "OFF (GUI)"
        parent.history.append((datetime.now().isoformat(), idx+1, action))
        if parent.db_user_id:
            tipo = "LED_ON" if new_state else "LED_OFF"
            db_save_event(parent.db_user_id, tipo, f"LED{idx+1}", "APP", "1" if new_state else "0")
        parent.update_ui()


def reset_total(parent):
    from app.workers.serial_thread import SerialThread as _SerialThread
    confirm = QMessageBox.question(parent, "Confirmar reset",
                                   "¿Deseas reiniciar el contador (solo cuenta activaciones del sensor)?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    if confirm == QMessageBox.StandardButton.Yes:
        parent.total_counter = 0
        parent.history.append((datetime.now().isoformat(), 0, "RESET"))
        try:
            sent = False
            if parent.serial_thread and parent.serial_thread.isRunning():
                parent.serial_thread.write("RESET")
                sent = True
            else:
                sel = parent.port_combo.currentText()
                if sel:
                    try:
                        _SerialThread.hardware_reset_port(sel, 115200, pulse_ms=0)
                    except Exception:
                        pass
            if sent:
                parent._waiting_reset_ack = True
                parent._reset_ack_timer.start(1500)
                return
            else:
                sel = parent.port_combo.currentText()
                if sel:
                    _SerialThread.hardware_reset_port(sel, 115200)
        except Exception:
            logger.exception("Reset error")
        if parent.db_user_id:
            db_save_event(parent.db_user_id, "RESET_CONTADOR", "CONTADOR", "APP", "0")
        parent.update_ui()


def on_reset_ack_timeout(parent):
    from app.workers.serial_thread import SerialThread as _SerialThread
    try:
        if parent._waiting_reset_ack:
            parent._waiting_reset_ack = False
            sel = parent.port_combo.currentText()
            if sel:
                _SerialThread.hardware_reset_port(sel, 115200)
            QMessageBox.information(parent, "Reset", "No se recibió ACK de ESP32; se ejecutó reset hardware como fallback.")
    except Exception:
        logger.exception("Reset ACK timeout handler error")
