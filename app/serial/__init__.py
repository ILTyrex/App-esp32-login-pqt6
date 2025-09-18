"""app.serial package

Expose `serial_ui` for compatibility with imports like
`from app.serial import serial_ui`.
"""

try:
	from . import serial_ui  # noqa: F401
except Exception:
	serial_ui = None
