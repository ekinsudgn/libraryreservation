-- =====================================================================
--  Kütüphane Masa / Grup Odası Rezervasyon Sistemi - Veritabanı Şeması
--  PostgreSQL 12+
--
--  Tüm saatler kütüphanenin yerel saatidir (Europe/Istanbul) ve
--  TIMESTAMP (saat dilimsiz) olarak tutulur.
-- =====================================================================

-- GiST indeksinde "space_id WITH =" kullanabilmek için gerekli eklenti
CREATE EXTENSION IF NOT EXISTS btree_gist;

DROP VIEW  IF EXISTS reservation_details;
DROP TABLE IF EXISTS reservations;
DROP TABLE IF EXISTS spaces;
DROP TABLE IF EXISTS users;
DROP FUNCTION IF EXISTS reservations_guard();

-- ---------------------------------------------------------------------
--  Kullanıcılar
-- ---------------------------------------------------------------------
CREATE TABLE users (
    id            SERIAL       PRIMARY KEY,
    student_no    VARCHAR(20)  NOT NULL UNIQUE,
    full_name     VARCHAR(100) NOT NULL,
    email         VARCHAR(120) NOT NULL UNIQUE,
    password_hash TEXT         NOT NULL,
    created_at    TIMESTAMP    NOT NULL DEFAULT LOCALTIMESTAMP
);

-- ---------------------------------------------------------------------
--  Rezerve edilebilir alanlar (çalışma masası veya grup odası)
-- ---------------------------------------------------------------------
CREATE TABLE spaces (
    id        SERIAL      PRIMARY KEY,
    name      VARCHAR(50) NOT NULL UNIQUE,
    kind      VARCHAR(10) NOT NULL CHECK (kind IN ('desk', 'room')),
    capacity  SMALLINT    NOT NULL CHECK (capacity > 0),
    floor     SMALLINT    NOT NULL,
    is_active BOOLEAN     NOT NULL DEFAULT TRUE
);

-- ---------------------------------------------------------------------
--  Rezervasyonlar
--  Kayıtlar asla silinmez; iptal edilen rezervasyon status='cancelled'
--  olarak kalır. Böylece kullanıcının geçmişi korunur.
-- ---------------------------------------------------------------------
CREATE TABLE reservations (
    id            SERIAL       PRIMARY KEY,
    user_id       INT          NOT NULL REFERENCES users(id)  ON DELETE RESTRICT,
    space_id      INT          NOT NULL REFERENCES spaces(id) ON DELETE RESTRICT,
    starts_at     TIMESTAMP    NOT NULL,
    ends_at       TIMESTAMP    NOT NULL,
    status        VARCHAR(10)  NOT NULL DEFAULT 'active'
                               CHECK (status IN ('active', 'cancelled')),
    created_at    TIMESTAMP    NOT NULL DEFAULT LOCALTIMESTAMP,
    cancelled_at  TIMESTAMP,
    cancel_reason VARCHAR(200),

    -- Bitiş başlangıçtan sonra olmalı
    CONSTRAINT chk_order          CHECK (ends_at > starts_at),
    -- Saatlik rezervasyon: başlangıç ve bitiş tam saat olmalı (10:00, 11:00 ...)
    CONSTRAINT chk_full_hours     CHECK (date_trunc('hour', starts_at) = starts_at
                                     AND date_trunc('hour', ends_at)   = ends_at),
    -- Tek seferde en fazla 4 saat
    CONSTRAINT chk_max_duration   CHECK (ends_at - starts_at <= INTERVAL '4 hours'),
    -- Çalışma saatleri 08:00 - 22:00, aynı gün içinde
    CONSTRAINT chk_opening_hours  CHECK (starts_at::time >= TIME '08:00'
                                     AND ends_at::time   <= TIME '22:00'
                                     AND ends_at::date    = starts_at::date),
    -- İptal bilgisi yalnızca iptal edilmiş kayıtta bulunur
    CONSTRAINT chk_cancel_fields  CHECK ((status = 'cancelled') = (cancelled_at IS NOT NULL)),

    -- *** ÇAKIŞMA ENGELİ ***
    -- Aynı alan için, aktif rezervasyonların [başlangıç, bitiş) aralıkları
    -- kesişemez. '[)' sayesinde 10-12 ile 12-14 çakışma sayılmaz.
    -- İptal edilenler (status='cancelled') kontrole dahil değildir, yani
    -- iptal edilen saat tekrar rezerve edilebilir.
    CONSTRAINT no_space_overlap EXCLUDE USING gist (
        space_id                              WITH =,
        tsrange(starts_at, ends_at, '[)')     WITH &&
    ) WHERE (status = 'active'),

    -- Bir kullanıcı aynı saatte iki farklı yerde rezervasyon tutamaz
    CONSTRAINT no_user_overlap EXCLUDE USING gist (
        user_id                               WITH =,
        tsrange(starts_at, ends_at, '[)')     WITH &&
    ) WHERE (status = 'active')
);

CREATE INDEX idx_reservations_user ON reservations (user_id, starts_at DESC);

-- ---------------------------------------------------------------------
--  Zamana bağlı kurallar (CHECK içinde now() kullanılamadığı için trigger)
-- ---------------------------------------------------------------------
CREATE FUNCTION reservations_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.starts_at < date_trunc('hour', LOCALTIMESTAMP) THEN
            RAISE EXCEPTION 'Geçmiş bir saat için rezervasyon yapılamaz.';
        END IF;
        IF NEW.starts_at > LOCALTIMESTAMP + INTERVAL '14 days' THEN
            RAISE EXCEPTION 'En fazla 14 gün sonrasına rezervasyon yapılabilir.';
        END IF;
        IF NOT EXISTS (SELECT 1 FROM spaces WHERE id = NEW.space_id AND is_active) THEN
            RAISE EXCEPTION 'Bu alan şu anda rezervasyona kapalı.';
        END IF;
        NEW.status        := 'active';
        NEW.cancelled_at  := NULL;
        NEW.cancel_reason := NULL;
        RETURN NEW;

    ELSIF TG_OP = 'UPDATE' THEN
        -- Rezervasyonun kendisi değiştirilemez; sadece iptal edilebilir
        IF NEW.user_id   <> OLD.user_id  OR NEW.space_id <> OLD.space_id
        OR NEW.starts_at <> OLD.starts_at OR NEW.ends_at <> OLD.ends_at THEN
            RAISE EXCEPTION 'Rezervasyon bilgileri değiştirilemez; iptal edip yeniden oluşturun.';
        END IF;

        IF OLD.status = 'cancelled' THEN
            RAISE EXCEPTION 'Bu rezervasyon zaten iptal edilmiş.';
        END IF;

        IF NEW.status = 'cancelled' THEN
            IF OLD.starts_at <= LOCALTIMESTAMP THEN
                RAISE EXCEPTION 'Başlamış veya geçmiş bir rezervasyon iptal edilemez.';
            END IF;
            NEW.cancelled_at := LOCALTIMESTAMP;
        END IF;
        RETURN NEW;

    ELSIF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Rezervasyon kayıtları silinemez; iptal edilmelidir.';
    END IF;
    RETURN NULL;
END;
$$;

CREATE TRIGGER trg_reservations_guard
BEFORE INSERT OR UPDATE OR DELETE ON reservations
FOR EACH ROW EXECUTE FUNCTION reservations_guard();

-- ---------------------------------------------------------------------
--  Geçmiş / aktif ayrımı için görünüm
--    upcoming  : henüz başlamamış  (iptal edilebilir)
--    ongoing   : şu an devam ediyor
--    completed : süresi dolmuş     (geçmiş)
--    cancelled : iptal edilmiş     (geçmiş)
-- ---------------------------------------------------------------------
CREATE VIEW reservation_details AS
SELECT r.id, r.user_id, r.space_id, r.starts_at, r.ends_at, r.status,
       r.created_at, r.cancelled_at, r.cancel_reason,
       s.name AS space_name, s.kind AS space_kind, s.floor, s.capacity,
       CASE
           WHEN r.status = 'cancelled'        THEN 'cancelled'
           WHEN r.ends_at   <= LOCALTIMESTAMP THEN 'completed'
           WHEN r.starts_at <= LOCALTIMESTAMP THEN 'ongoing'
           ELSE 'upcoming'
       END AS state
FROM reservations r
JOIN spaces s ON s.id = r.space_id;
