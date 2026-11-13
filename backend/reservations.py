"""Rezervasyon işlemleri: doluluk tablosu, rezervasyon oluşturma,
kullanıcının rezervasyonları ve iptal.
"""
import random
import time as clock
from datetime import date, datetime, time, timedelta

from flask import Blueprint, request
from psycopg import errors

from . import config
from .auth import current_user_id, login_required
from .db import get_db
from .errors import ApiError, from_db_error

bp = Blueprint("reservations", __name__, url_prefix="/api")

HOURS = list(range(config.OPEN_HOUR, config.CLOSE_HOUR))
KINDS = ("all", "desk", "room")
MAX_ATTEMPTS = 5  # deadlock durumunda INSERT en fazla kaç kez denenir


def iso(value):
    return value.isoformat() if value else None


def parse_date(text, default=None):
    try:
        return date.fromisoformat(text)
    except (TypeError, ValueError):
        if default is not None:
            return default
        raise ApiError(400, "Tarih YYYY-AA-GG biçiminde olmalı.")


@bp.get("/availability")
@login_required
def availability():
    """Seçilen gün için her alanın saat saat durumunu döndürür.
    Her hücre: free (boş), taken (dolu), mine (benim), past (geçmiş)."""
    today = date.today()
    day = parse_date(request.args.get("date"), default=today)
    kind = request.args.get("kind", "all")
    if kind not in KINDS:
        raise ApiError(400, "Geçersiz alan türü.")

    conn = get_db()
    spaces = conn.execute(
        """SELECT id, name, kind, capacity, floor FROM spaces
           WHERE is_active AND (%(kind)s = 'all' OR kind = %(kind)s)
           ORDER BY kind, name""",
        {"kind": kind},
    ).fetchall()
    rows = conn.execute(
        """SELECT space_id, user_id, starts_at, ends_at FROM reservations
           WHERE status = 'active' AND starts_at::date = %s""",
        (day,),
    ).fetchall()

    occupied = {}  # (alan_id, saat) -> 'mine' | 'taken'
    for r in rows:
        state = "mine" if r["user_id"] == current_user_id() else "taken"
        for h in range(r["starts_at"].hour, r["ends_at"].hour):
            occupied[(r["space_id"], h)] = state

    current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
    for s in spaces:
        s["slots"] = [
            occupied.get((s["id"], h))
            or ("past" if datetime.combine(day, time(h)) < current_hour else "free")
            for h in HOURS
        ]

    return {
        "date": day.isoformat(),
        "today": today.isoformat(),
        "max_date": (today + timedelta(days=config.MAX_DAYS_AHEAD)).isoformat(),
        "hours": HOURS,
        "max_hours": config.MAX_HOURS,
        "spaces": spaces,
    }


@bp.post("/reservations")
@login_required
def create_reservation():
    data = request.get_json(silent=True) or {}
    try:
        space_id = int(data["space_id"])
        day = date.fromisoformat(data["date"])
        start_hour = int(data["start_hour"])
        duration = int(data["duration"])
    except (KeyError, TypeError, ValueError):
        raise ApiError(400, "Form bilgileri eksik veya geçersiz.")

    starts_at = datetime.combine(day, time()) + timedelta(hours=start_hour)
    ends_at = starts_at + timedelta(hours=duration)

    # Masanın boş olup olmadığı burada bilerek kontrol EDİLMİYOR.
    # Önce SELECT ile bakıp sonra INSERT etmek, iki kişi aynı anda istek
    # gönderdiğinde ikisinin de kaydedilmesine yol açar (race condition).
    # Kararı veritabanındaki EXCLUDE kısıtı verir; ikinci istek
    # ExclusionViolation hatasıyla reddedilir ve 409 döner.
    conn = get_db()
    for _attempt in range(MAX_ATTEMPTS):
        try:
            row = conn.execute(
                """INSERT INTO reservations (user_id, space_id, starts_at, ends_at)
                   VALUES (%s, %s, %s, %s) RETURNING id""",
                (current_user_id(), space_id, starts_at, ends_at),
            ).fetchone()
            conn.commit()
            break
        except errors.DeadlockDetected:
            # Aynı masa için aynı anda gelen iki INSERT birbirinin bitmesini
            # bekleyebilir; PostgreSQL birini deadlock ile iptal eder.
            # Kısa ve rastgele bir beklemeden sonra tekrar deneriz; bu sefer
            # diğer kayıt görünür olduğu için normal ExclusionViolation (409) gelir.
            conn.rollback()
            clock.sleep(random.uniform(0.01, 0.05) * (_attempt + 1))
        except (errors.ExclusionViolation, errors.CheckViolation, errors.RaiseException) as exc:
            conn.rollback()
            raise from_db_error(exc)
        except errors.ForeignKeyViolation:
            conn.rollback()
            raise ApiError(404, "Seçilen alan bulunamadı.")
    else:
        raise ApiError(503, "Sistem şu an çok yoğun, lütfen tekrar deneyin.")

    return {
        "message": f"Rezervasyon oluşturuldu: {starts_at:%d.%m.%Y %H:%M} - {ends_at:%H:%M}",
        "id": row["id"],
    }, 201


@bp.get("/reservations/mine")
@login_required
def my_reservations():
    """Kullanıcının rezervasyonlarını aktif ve geçmiş olarak ayırır.
    Durum (state) veritabanındaki reservation_details görünümünde hesaplanır."""
    rows = get_db().execute(
        """SELECT id, space_name, space_kind, floor, starts_at, ends_at,
                  state, cancelled_at, cancel_reason
           FROM reservation_details
           WHERE user_id = %s
           ORDER BY starts_at DESC""",
        (current_user_id(),),
    ).fetchall()

    for r in rows:
        r["starts_at"] = iso(r["starts_at"])
        r["ends_at"] = iso(r["ends_at"])
        r["cancelled_at"] = iso(r["cancelled_at"])
        r["can_cancel"] = r["state"] == "upcoming"

    active = sorted((r for r in rows if r["state"] in ("upcoming", "ongoing")),
                    key=lambda r: r["starts_at"])
    past = [r for r in rows if r["state"] in ("completed", "cancelled")]
    return {"active": active, "past": past}


@bp.post("/reservations/<int:reservation_id>/cancel")
@login_required
def cancel_reservation(reservation_id):
    data = request.get_json(silent=True) or {}
    reason = str(data.get("reason") or "").strip()[:200] or None

    conn = get_db()
    try:
        row = conn.execute(
            """UPDATE reservations
               SET status = 'cancelled', cancel_reason = %s
               WHERE id = %s AND user_id = %s
               RETURNING id""",
            (reason, reservation_id, current_user_id()),
        ).fetchone()
        conn.commit()
    except (errors.RaiseException, errors.CheckViolation) as exc:
        conn.rollback()
        raise from_db_error(exc)

    if not row:
        raise ApiError(404, "Rezervasyon bulunamadı.")
    return {"message": "Rezervasyon iptal edildi."}
