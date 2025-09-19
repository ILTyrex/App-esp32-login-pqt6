"""app.serial package

Expose `serial_ui` for compatibility with imports like
`from app.serial import serial_ui`.
"""

import logging
logger = logging.getLogger(__name__)

try:
	from . import serial_ui  # noqa: F401
except Exception as e:
	# Surface the import error instead of silently returning None
	logger.exception("Failed to import serial_ui from app.serial")
	raise
