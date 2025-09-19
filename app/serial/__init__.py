"""app.serial package

Expose `serial_ui` for compatibility with imports like
`from app.serial import serial_ui` will import the `serial_ui` submodule on demand.
This package intentionally avoids importing submodules at package import time to
prevent circular import problems.
"""

__all__ = ["serial_ui"]
