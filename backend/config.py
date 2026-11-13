"""Uygulama ayarları. Ortam değişkenleriyle değiştirilebilir."""
import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/kutuphane"
)
SECRET_KEY = os.environ.get("SECRET_KEY", "gelistirme-anahtari-degistirin")
TIMEZONE = "Europe/Istanbul"

OPEN_HOUR = 8        # kütüphane açılış saati (08:00)
CLOSE_HOUR = 22      # kapanış saati (22:00)
MAX_HOURS = 4        # tek rezervasyonda en fazla kaç saat
MAX_DAYS_AHEAD = 14  # en fazla kaç gün sonrasına rezervasyon yapılabilir
