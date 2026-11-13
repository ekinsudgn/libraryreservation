"""PostgreSQL bağlantısı.

Her HTTP isteği için tek bir bağlantı açılır (flask.g içinde tutulur)
ve istek bitince kapatılır.
"""
import psycopg
from flask import g
from psycopg.rows import dict_row

from . import config


def connect(**kwargs):
    """Yeni bir bağlantı açar. Oturum saat dilimi kütüphane saatine
    ayarlanır, böylece SQL içindeki LOCALTIMESTAMP doğru saati verir."""
    return psycopg.connect(
        config.DATABASE_URL,
        row_factory=dict_row,
        options=f"-c timezone={config.TIMEZONE}",
        connect_timeout=3,  # veritabanı kapalıysa istek takılıp kalmasın
        **kwargs,
    )


def get_db():
    if "db" not in g:
        g.db = connect()
    return g.db


def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()
