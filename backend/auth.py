"""Kimlik doğrulama: kayıt, giriş, çıkış.

Giriş yapan kullanıcının id'si Flask oturumunda (imzalı çerez) tutulur.
Şifreler veritabanına düz metin olarak değil, hash'lenerek yazılır.
"""
from functools import wraps

from flask import Blueprint, request, session
from psycopg import errors
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db
from .errors import ApiError

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            raise ApiError(401, "Devam etmek için giriş yapın.")
        return view(*args, **kwargs)
    return wrapper


def current_user_id():
    return session["user_id"]


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    student_no = str(data.get("student_no", "")).strip()
    full_name = str(data.get("full_name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not (student_no and full_name and email):
        raise ApiError(400, "Tüm alanları doldurun.")
    if len(password) < 6:
        raise ApiError(400, "Şifre en az 6 karakter olmalı.")

    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO users (student_no, full_name, email, password_hash)
               VALUES (%s, %s, %s, %s)""",
            (student_no, full_name, email, generate_password_hash(password)),
        )
        conn.commit()
    except errors.UniqueViolation:
        conn.rollback()
        raise ApiError(409, "Bu öğrenci numarası veya e-posta zaten kayıtlı.")
    return {"message": "Kayıt başarılı, şimdi giriş yapabilirsiniz."}, 201


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    user = get_db().execute(
        "SELECT id, student_no, full_name, password_hash FROM users WHERE student_no = %s",
        (str(data.get("student_no", "")).strip(),),
    ).fetchone()
    if not user or not check_password_hash(user["password_hash"], str(data.get("password", ""))):
        raise ApiError(401, "Öğrenci numarası veya şifre hatalı.")

    session.clear()
    session["user_id"] = user["id"]
    return {"user": {"id": user["id"], "student_no": user["student_no"], "full_name": user["full_name"]}}


@bp.post("/logout")
def logout():
    session.clear()
    return {"message": "Çıkış yapıldı."}


@bp.get("/me")
@login_required
def me():
    user = get_db().execute(
        "SELECT id, student_no, full_name FROM users WHERE id = %s", (current_user_id(),)
    ).fetchone()
    if not user:
        session.clear()
        raise ApiError(401, "Oturum geçersiz, tekrar giriş yapın.")
    return {"user": user}
