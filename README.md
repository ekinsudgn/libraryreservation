# Kütüphane Masa / Grup Odası Rezervasyon Sistemi

Üniversite kütüphanesindeki çalışma masalarının ve grup odalarının saatlik olarak
rezerve edildiği web tabanlı sistem.

**Proje isterleri**
1. Masa ve grup odaları saatlik olarak rezerve edilebilmeli.
2. Aynı masa için aynı saat diliminde çakışan rezervasyonlar **veritabanı seviyesinde** engellenmeli.
3. Kullanıcılar geçmiş ve aktif rezervasyonlarını görebilmeli, iptal edebilmeli.

## Proje üç parçadan oluşuyor

```
kutuphane-rezervasyon/
│
├── database/            1. KİŞİ  –  Veritabanı (PostgreSQL)
│   ├── schema.sql           tablolar, kısıtlar, trigger, görünüm
│   ├── seed.sql             örnek masa ve odalar
│   ├── init_db.py           veritabanını kurar
│   └── cakisma_testi.py     çakışma engelini kanıtlayan test
│
├── backend/             2. KİŞİ  –  Sunucu tarafı (Python / Flask, JSON API)
│   ├── app.py               uygulamayı kurar, parçaları birleştirir
│   ├── auth.py              kayıt, giriş, çıkış
│   ├── reservations.py      doluluk, rezervasyon, iptal
│   ├── errors.py            hata mesajları ve HTTP kodları
│   ├── db.py                veritabanı bağlantısı
│   └── config.py            ayarlar (çalışma saatleri, limitler)
│
├── frontend/            3. KİŞİ  –  Kullanıcı arayüzü (HTML / CSS / JavaScript)
│   ├── index.html           giriş ve kayıt sayfası
│   ├── reserve.html         doluluk tablosu ve rezervasyon formu
│   ├── my.html              rezervasyonlarım (aktif / geçmiş, iptal)
│   ├── css/style.css
│   └── js/                  api.js, ui.js, login.js, reserve.js, my.js
│
├── run.py               uygulamayı başlatır
└── requirements.txt     Python paketleri
```

Her klasörün içinde, o kısmı sunacak kişi için ayrıca bir **README.md** var:
dosyaların ne yaptığı, sunumda neyin anlatılacağı ve hocanın sorabileceği sorular.

## Parçalar birbiriyle nasıl konuşuyor?

```
 Tarayıcı (frontend)            Sunucu (backend)                 Veritabanı (database)
 ───────────────────            ─────────────────                ─────────────────────
 reserve.js                     reservations.py                  reservations tablosu
   "Rezerve Et" tıklandı
   api.post('/reservations') ──► POST /api/reservations
                                  oturumu kontrol et
                                  INSERT INTO reservations ──────► EXCLUDE kısıtı kontrol eder
                                                                    • boşsa  -> kaydeder
                                                                    • doluysa -> hata verir
                                ◄─ 201 Created   veya  409 Conflict
   mesajı göster, tabloyu  ◄────  {"message": ...} / {"error": ...}
   yeniden çiz
```

- Frontend veritabanını hiç görmez, sadece backend'in `/api/...` adreslerine istek atar.
- Backend HTML üretmez, sadece JSON döndürür.
- Çakışma kararını backend değil **veritabanı** verir. İki kişi aynı anda aynı masayı
  istese bile yalnızca biri kaydedilir.

## Kurulum ve çalıştırma

Gerekenler: Python 3.12, PostgreSQL 16 (servis çalışıyor olmalı).

Proje klasöründe (`kutuphane-rezervasyon`) sırasıyla:

```
pip install -r requirements.txt
python database/init_db.py
python run.py
```

Tarayıcıda **http://127.0.0.1:5000** adresini açın.
Demo hesap: öğrenci no `20230001`, şifre `demo1234`

Çakışma testini çalıştırmak için:
```
python database/cakisma_testi.py
```

> `init_db.py` tabloları silip yeniden kurar; tüm rezervasyonlar silinir.
> Veritabanı şifresi farklıysa önce `DATABASE_URL` ortam değişkenini ayarlayın:
> `set DATABASE_URL=postgresql://postgres:SIFRE@localhost:5432/kutuphane`

> Giriş yaparken "Veritabanına bağlanılamıyor" mesajı çıkarsa PostgreSQL servisi
> kapalıdır: Win + R → `services.msc` → **postgresql-x64-16** → Başlat.

## Sunum akışı önerisi

| Sıra | Kim | Konu | Süre |
|---|---|---|---|
| 1 | Herkes / 1. kişi | Problem ve isterler, genel mimari (yukarıdaki şema) | 2 dk |
| 2 | 1. kişi | Veritabanı tasarımı, EXCLUDE kısıtı, trigger'lar, **çakışma testi canlı** | 5 dk |
| 3 | 2. kişi | API uçları, bir isteğin yolculuğu, hata kodları | 5 dk |
| 4 | 3. kişi | Arayüz, **canlı demo**: giriş → rezervasyon → çakışma uyarısı → iptal | 5 dk |
| 5 | Herkes | Sorular | – |

**Canlı demo senaryosu (3. kişi):**
1. Demo hesapla giriş yap.
2. Tablodan boş bir hücreye tıkla, 2 saat seç, "Rezerve Et". Hücreler maviye döner.
3. Aynı masa ve saati tekrar dene. "Bu alan dolu" uyarısı çıkar (bu uyarıyı veritabanı üretir).
4. "Rezervasyonlarım" sayfasına geç, neden yazarak iptal et. Kayıt "Geçmiş" bölümüne geçer.
5. Rezervasyon sayfasına dön; iptal edilen saatin tekrar boş göründüğünü göster.
