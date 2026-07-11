import os

from flask import Flask
from flask_cors import CORS

from app.extensions import db, migrate


def create_app():
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.environ["FLASK_SECRET_KEY"]
    # Must be absolute: Flask's send_from_directory resolves relative
    # directories against the app package's root_path, not the cwd, which
    # would silently look in the wrong place.
    app.config["STORAGE_DIR"] = os.path.abspath(
        os.environ.get("STORAGE_DIR", "storage")
    )
    app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB upload cap

    # Login sessions are a cookie shared between two different origins
    # (Vercel frontend, Render backend) in production, which only works if
    # the cookie is SameSite=None -- but that requires Secure, which in turn
    # requires HTTPS, which local dev over plain http doesn't have. `RENDER`
    # is auto-set by Render on every service, so it doubles as our "are we
    # in a real cross-origin HTTPS deployment" signal.
    is_deployed = bool(os.environ.get("RENDER"))
    app.config["SESSION_COOKIE_SAMESITE"] = "None" if is_deployed else "Lax"
    app.config["SESSION_COOKIE_SECURE"] = is_deployed

    os.makedirs(app.config["STORAGE_DIR"], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)

    frontend_origin = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
    CORS(app, supports_credentials=True, origins=[frontend_origin])

    from app.routes.auth import auth_bp
    from app.routes.drive import drive_bp
    from app.routes.files import files_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(drive_bp, url_prefix="/api/drive")
    app.register_blueprint(files_bp, url_prefix="/api/files")

    return app
