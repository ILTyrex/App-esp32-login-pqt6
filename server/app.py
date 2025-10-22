from flask import Flask, send_from_directory
from .config import Config
from .extensions import db, migrate, jwt
from .routes.auth import bp as auth_bp
from .routes.esp32 import bp as esp32_bp
from .routes.events import bp as events_bp
from .routes.actuador import bp as actuador_bp
from .routes.export import bp as export_bp
from flask_cors import CORS
import os

def create_app():
    app = Flask(__name__, static_folder="static_frontend", static_url_path="/")
    app.config.from_object(Config)

    cors_origins = app.config.get("CORS_ORIGINS", "*")
    if isinstance(cors_origins, str) and cors_origins != "*":
        origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
    else:
        origins = "*" if cors_origins == "*" else cors_origins
    CORS(app, origins=origins)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(esp32_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(actuador_bp)
    app.register_blueprint(export_bp)

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path):
        if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, "index.html")

    return app

if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000, debug=True)
