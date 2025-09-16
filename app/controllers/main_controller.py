from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow, QPushButton, QLabel


class MainController(QMainWindow):
    def __init__(self, username=None):
        super().__init__()
        uic.loadUi("app/gui/main_window.ui", self)

        # Widgets de la UI
        self.label: QLabel = self.findChild(QLabel, "label")
        self.pushButton: QPushButton = self.findChild(QPushButton, "pushButton")

        # Personalizar bienvenida
        if username:
            self.label.setText(f"Bienvenido {username} 🚀")

        # Evento del botón (ejemplo: cambiar el texto o abrir otro módulo)
        self.pushButton.clicked.connect(self.toggle_theme)

    def toggle_theme(self):
        """Ejemplo de acción: alternar texto del botón."""
        if self.pushButton.text() == "☀️  Claro":
            self.pushButton.setText("🌙 Oscuro")
        else:
            self.pushButton.setText("☀️  Claro")
