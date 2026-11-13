"""Flask uygulamasını kurar.

- /api/...  adresleri: backend (JSON API)
- diğer adresler: frontend klasöründeki statik dosyalar (HTML, CSS, JS)

Ön yüz ve API aynı adresten sunulduğu için tarayıcı oturum çerezini
API isteklerine otomatik ekler; ayrıca CORS ayarı gerekmez.
"""
from pathlib import Path

from flask import Flask

from . import auth, config, db, reservations
from .errors import register_error_handlers

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


def create_app():
    app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
    app.secret_key = config.SECRET_KEY
    app.json.ensure_ascii = False  # Türkçe karakterler JSON'da okunur kalsın

    app.register_blueprint(auth.bp)
    app.register_blueprint(reservations.bp)
    register_error_handlers(app)
    app.teardown_appcontext(db.close_db)

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    return app
