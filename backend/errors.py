"""Hata yönetimi.

API her hatada {"error": "mesaj"} biçiminde JSON döndürür. Veritabanının
fırlattığı kısıt hataları burada kullanıcıya gösterilecek mesajlara çevrilir.
"""
import psycopg
from flask import jsonify
from psycopg import errors

from . import config


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


# Veritabanı kısıt adı -> kullanıcıya gösterilecek mesaj
CONSTRAINT_MESSAGES = {
    "no_space_overlap": "Bu alan seçtiğiniz saat aralığında dolu; lütfen başka bir saat veya alan seçin.",
    "no_user_overlap": "Bu saat aralığında zaten başka bir aktif rezervasyonunuz var.",
    "chk_order": "Bitiş saati başlangıçtan sonra olmalıdır.",
    "chk_full_hours": "Rezervasyonlar tam saat başında başlayıp bitmelidir.",
    "chk_max_duration": f"Tek seferde en fazla {config.MAX_HOURS} saat rezervasyon yapılabilir.",
    "chk_opening_hours": f"Rezervasyonlar {config.OPEN_HOUR:02d}:00 - {config.CLOSE_HOUR:02d}:00 arasında olmalıdır.",
}


def from_db_error(exc):
    """Veritabanı hatasını uygun HTTP koduyla bir ApiError'a çevirir."""
    if isinstance(exc, errors.ExclusionViolation):    # çakışma -> 409 Conflict
        return ApiError(409, CONSTRAINT_MESSAGES.get(exc.diag.constraint_name, "Rezervasyon çakışıyor."))
    if isinstance(exc, errors.CheckViolation):        # kural ihlali -> 422
        return ApiError(422, CONSTRAINT_MESSAGES.get(exc.diag.constraint_name, "Geçersiz rezervasyon."))
    if isinstance(exc, errors.RaiseException):        # trigger'daki RAISE EXCEPTION
        return ApiError(422, exc.diag.message_primary)
    raise exc


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(exc):
        return jsonify(error=exc.message), exc.status

    @app.errorhandler(psycopg.OperationalError)
    def handle_db_down(_exc):
        return jsonify(error="Veritabanına bağlanılamıyor. PostgreSQL servisinin çalıştığından emin olun."), 503

    @app.errorhandler(404)
    def handle_not_found(_exc):
        return jsonify(error="Adres bulunamadı."), 404

    @app.errorhandler(405)
    def handle_method(_exc):
        return jsonify(error="Bu adres bu yöntemi desteklemiyor."), 405
