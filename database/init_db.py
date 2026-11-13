"""Veritabanını oluşturur, şemayı kurar ve örnek verileri yükler.

UYARI: Mevcut tabloları silip yeniden oluşturur (tüm rezervasyonlar silinir).
Kullanım (proje klasöründen):  python database/init_db.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # backend paketini bulabilmek için

import psycopg  # noqa: E402
from psycopg import sql  # noqa: E402
from psycopg.conninfo import conninfo_to_dict, make_conninfo  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

from backend import config, db  # noqa: E402


def create_database_if_missing():
    dbname = conninfo_to_dict(config.DATABASE_URL).get("dbname", "kutuphane")
    admin_url = make_conninfo(config.DATABASE_URL, dbname="postgres")
    with psycopg.connect(admin_url, autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,)).fetchone()
        if not exists:
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))
            print(f"'{dbname}' veritabanı oluşturuldu.")
        # psql gibi dış araçlarla bağlanınca da yerel saat kullanılsın
        conn.execute(
            sql.SQL("ALTER DATABASE {} SET timezone = {}").format(
                sql.Identifier(dbname), sql.Literal(config.TIMEZONE)
            )
        )


def main():
    create_database_if_missing()
    with db.connect() as conn:
        conn.execute((HERE / "schema.sql").read_text(encoding="utf-8"))
        conn.execute((HERE / "seed.sql").read_text(encoding="utf-8"))
        conn.execute(
            """INSERT INTO users (student_no, full_name, email, password_hash)
               VALUES (%s, %s, %s, %s)""",
            ("20230001", "Demo Öğrenci", "demo@ogrenci.edu.tr", generate_password_hash("demo1234")),
        )
    print("Şema ve örnek veriler yüklendi.")
    print("Demo giriş -> öğrenci no: 20230001  şifre: demo1234")


if __name__ == "__main__":
    main()
