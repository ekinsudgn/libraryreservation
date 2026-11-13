"""Çakışma engelinin veritabanı seviyesinde çalıştığını gösteren test.

10 farklı kullanıcı, AYNI ANDA, aynı masanın aynı saatini rezerve etmeye
çalışır. Uygulamada hiçbir ön kontrol yoktur; yine de yalnızca 1 tanesi
başarılı olmalı, diğer 9'u PostgreSQL tarafından reddedilmelidir.

Ardından kısmi çakışma, uç uca rezervasyon ve iptal sonrası yeniden
rezervasyon senaryolarını dener.

Kullanım (proje klasöründen):  python database/cakisma_testi.py
"""
import random
import sys
import threading
import time as time_module
from datetime import date, datetime, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # backend paketini bulabilmek için

from psycopg import errors  # noqa: E402

from backend import db  # noqa: E402

N = 10
DAY = date.today() + timedelta(days=7)
SLOT_START = datetime.combine(DAY, time(10))
SLOT_END = datetime.combine(DAY, time(12))


def setup():
    with db.connect() as conn:
        user_ids = []
        for i in range(1, N + 1):
            row = conn.execute(
                """INSERT INTO users (student_no, full_name, email, password_hash)
                   VALUES (%s, %s, %s, 'x')
                   ON CONFLICT (student_no) DO UPDATE SET full_name = EXCLUDED.full_name
                   RETURNING id""",
                (f"TEST{i:03d}", f"Test Kullanıcı {i}", f"test{i}@test.local"),
            ).fetchone()
            user_ids.append(row["id"])
        space_id = conn.execute("SELECT id FROM spaces WHERE name = 'Masa 101'").fetchone()["id"]
        # Önceki çalıştırmadan kalan test rezervasyonlarını iptal et
        conn.execute(
            """UPDATE reservations SET status = 'cancelled', cancel_reason = 'test temizliği'
               WHERE status = 'active' AND starts_at::date = %s
                 AND (space_id = %s OR user_id = ANY(%s))""",
            (DAY, space_id, user_ids),
        )
    return user_ids, space_id


def try_reserve(conn, user_id, space_id, start, end, attempts=5):
    """Backend'deki gibi: deadlock olursa kısa, rastgele bir beklemeden sonra
    tekrar dener. Aynı anda gelen iki INSERT birbirini bekleyebilir; PostgreSQL
    birini deadlock ile iptal eder. Tekrar denemede normal çakışma hatası gelir."""
    deadlocks = 0
    for attempt in range(attempts):
        if attempt:
            time_module.sleep(random.uniform(0.01, 0.05) * attempt)
        try:
            with conn.transaction():
                conn.execute(
                    "INSERT INTO reservations (user_id, space_id, starts_at, ends_at) VALUES (%s, %s, %s, %s)",
                    (user_id, space_id, start, end),
                )
            result = "BAŞARILI"
        except errors.DeadlockDetected:
            deadlocks += 1
            continue
        except errors.ExclusionViolation as e:
            result = f"REDDEDİLDİ ({e.diag.constraint_name})"
        return result + (f"  [{deadlocks} deadlock sonrası tekrar denendi]" if deadlocks else "")
    return f"SONUÇSUZ ({deadlocks} deadlock)"


def concurrent_test(user_ids, space_id):
    print(f"\n1) {N} kullanıcı aynı anda Masa 101 / {SLOT_START:%d.%m %H:%M}-{SLOT_END:%H:%M} istiyor")
    barrier = threading.Barrier(N)
    results = [None] * N

    def worker(i):
        with db.connect(autocommit=True) as conn:
            barrier.wait()  # hepsi aynı anda başlasın
            results[i] = try_reserve(conn, user_ids[i], space_id, SLOT_START, SLOT_END)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(N)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    for i, r in enumerate(results):
        print(f"   kullanıcı {i + 1:2d}: {r}")
    ok = sum(r.startswith("BAŞARILI") for r in results)
    rejected = sum(r.startswith("REDDEDİLDİ") for r in results)
    passed = ok == 1 and rejected == N - 1
    print(f"   => {ok} başarılı, {rejected} reddedildi  ->  {'DOĞRU ✔' if passed else 'HATALI ✘'}")
    return passed


def edge_cases(user_ids, space_id):
    checks = []
    with db.connect(autocommit=True) as conn:
        def check(title, user, start_h, end_h, expected):
            res = try_reserve(conn, user, space_id,
                              datetime.combine(DAY, time(start_h)), datetime.combine(DAY, time(end_h)))
            ok = res.startswith(expected)
            checks.append(ok)
            print(f"   {title:<45} {res:<35} {'✔' if ok else '✘'}")

        print("\n2) Sınır durumları (Masa 101'de 10:00-12:00 dolu)")
        check("11:00-13:00 (kısmi çakışma)", user_ids[1], 11, 13, "REDDEDİLDİ")
        check("09:00-10:00 (hemen önce, uç uca)", user_ids[2], 9, 10, "BAŞARILI")
        check("12:00-13:00 (hemen sonra, uç uca)", user_ids[3], 12, 13, "BAŞARILI")

        print("\n3) İptal edilen saat tekrar rezerve edilebilir mi?")
        conn.execute(
            """UPDATE reservations SET status = 'cancelled'
               WHERE space_id = %s AND starts_at = %s AND status = 'active'""",
            (space_id, SLOT_START),
        )
        check("10:00-12:00 iptal sonrası yeniden", user_ids[4], 10, 12, "BAŞARILI")
    return all(checks)


if __name__ == "__main__":
    users, space = setup()
    a = concurrent_test(users, space)
    b = edge_cases(users, space)
    print("\nSONUÇ:", "Tüm testler geçti ✔" if a and b else "Bazı testler başarısız ✘")
