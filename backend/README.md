# 2. Kısım – Backend (Python / Flask, JSON API)

Backend, arayüz ile veritabanı arasındaki katman. Tarayıcıdan gelen istekleri alır,
kullanıcının giriş yapıp yapmadığını kontrol eder, veritabanına sorgu gönderir ve
sonucu **JSON** olarak döndürür. HTML üretmez.

## Dosyalar

| Dosya | Ne yapar |
|---|---|
| `app.py` | Flask uygulamasını kurar; `auth` ve `reservations` modüllerini, hata yöneticisini bağlar. Frontend dosyalarını da sunar. |
| `auth.py` | Kayıt, giriş, çıkış, "ben kimim" uçları; `login_required` kontrolü |
| `reservations.py` | Doluluk tablosu, rezervasyon oluşturma, rezervasyonlarım, iptal |
| `errors.py` | Veritabanı hatalarını anlaşılır Türkçe mesajlara ve doğru HTTP koduna çevirir |
| `db.py` | PostgreSQL bağlantısı (her istek için bir bağlantı) |
| `config.py` | Çalışma saatleri (08–22), en fazla 4 saat, en fazla 14 gün ileri |

## API uçları

| Yöntem | Adres | Ne yapar | Başarılı cevap |
|---|---|---|---|
| POST | `/api/auth/register` | Yeni öğrenci kaydı | 201 |
| POST | `/api/auth/login` | Giriş, oturum çerezi verir | 200 `{user}` |
| POST | `/api/auth/logout` | Çıkış | 200 |
| GET | `/api/auth/me` | Giriş yapan kullanıcı | 200 `{user}` |
| GET | `/api/availability?date=2026-11-20&kind=all` | Günün doluluk tablosu | 200 `{spaces: [{..., slots: [...]}]}` |
| POST | `/api/reservations` | Rezervasyon oluştur `{space_id, date, start_hour, duration}` | 201 |
| GET | `/api/reservations/mine` | Kullanıcının rezervasyonları | 200 `{active: [...], past: [...]}` |
| POST | `/api/reservations/<id>/cancel` | İptal `{reason}` | 200 |

`slots` dizisindeki her eleman bir saati temsil eder: `free` (boş), `taken` (dolu),
`mine` (benim), `past` (geçmiş saat).

## Hata kodları

Her hata `{"error": "mesaj"}` biçiminde döner.

| Kod | Ne zaman | Örnek |
|---|---|---|
| 400 | Eksik / bozuk istek | "Form bilgileri eksik veya geçersiz." |
| 401 | Giriş yapılmamış / şifre yanlış | "Devam etmek için giriş yapın." |
| 404 | Kayıt bulunamadı | "Rezervasyon bulunamadı." |
| 409 | **Çakışma** (EXCLUDE kısıtı) veya aynı öğrenci no ile kayıt | "Bu alan seçtiğiniz saat aralığında dolu…" |
| 422 | Kurala aykırı (CHECK veya trigger) | "Tek seferde en fazla 4 saat rezervasyon yapılabilir." |
| 503 | Veritabanı kapalı | "Veritabanına bağlanılamıyor…" |

## Bir rezervasyon isteğinin yolculuğu

`reservations.py` → `create_reservation()`:

1. `@login_required` oturumda `user_id` var mı bakar; yoksa 401.
2. JSON'dan `space_id`, `date`, `start_hour`, `duration` okunur; bozuksa 400.
3. Başlangıç ve bitiş zamanı hesaplanır.
4. **Masanın boş olup olmadığına bakılmadan** doğrudan `INSERT` yapılır.
5. Veritabanı kabul ederse `commit` → 201.
   Reddederse hata yakalanır, `errors.from_db_error()` ile mesaja çevrilir:
   - `ExclusionViolation` → 409 (çakışma)
   - `CheckViolation` → 422 (ör. 5 saatlik istek)
   - `RaiseException` → 422 (trigger mesajı, ör. "Geçmiş bir saat için rezervasyon yapılamaz.")
   - `DeadlockDetected` → kısa, rastgele bir beklemeden sonra INSERT tekrar denenir (en fazla 5 kez).

4. adım bilerek böyle. Önce `SELECT` ile kontrol etseydik, aynı anda gelen iki istek
ikisi de "boş" görüp kaydedebilirdi. Karar veritabanında verildiği için backend kodu
daha basit ve güvenli.

## Güvenlik

- Şifreler `werkzeug` ile **hash'lenerek** saklanır, düz metin tutulmaz.
- Oturum, imzalı bir çerezde (`session`) tutulur; kullanıcı id'si istemciden alınmaz.
- Tüm SQL sorguları **parametreli** (`%s`); SQL injection'a karşı korumalı.
- Bir kullanıcı başkasının rezervasyonunu iptal edemez: `WHERE id = %s AND user_id = %s`.

## Sunumda anlatılacaklar

1. Katmanlı yapı: frontend → backend → veritabanı; backend'in görevi.
2. API uçları tablosu.
3. `create_reservation()` fonksiyonu adım adım ve neden ön kontrol yapılmadığı.
4. Hata kodları: 409 ile 422 arasındaki fark.
5. Güvenlik önlemleri.

İstersen sunumda API'yi doğrudan tarayıcıdan da gösterebilirsin: giriş yaptıktan sonra
`http://127.0.0.1:5000/api/reservations/mine` adresini açınca ham JSON görünür.

## Olası sorular

- **Neden Flask?** Küçük ve anlaşılır bir framework; bu projenin ihtiyacı birkaç API ucu.
- **Neden JSON API, neden sunucuda HTML üretmiyoruz?** Frontend ve backend birbirinden
  bağımsız geliştirilebiliyor. İleride bir mobil uygulama aynı API'yi kullanabilir.
- **Kullanıcı nasıl hatırlanıyor?** Girişte Flask oturumuna `user_id` yazılıyor; tarayıcı
  bunu imzalı bir çerezde saklıyor ve her istekte gönderiyor.
- **Deadlock neden oluyor, ne yapıyorsunuz?** Aynı masaya aynı anda iki INSERT gelirse
  ikisi de kendi satırını ekler ve diğerinin işleminin bitmesini bekler. PostgreSQL bunu
  fark edip birini "deadlock" hatasıyla iptal eder. Backend bu hatayı yakalar ve kısa bir
  beklemeden sonra tekrar dener. İkinci denemede diğer kayıt görünür olduğu için normal
  "dolu" (409) cevabı döner. 10 eşzamanlı HTTP isteğiyle 10 tur denedik: her turda
  1 kabul, 9 ret, hiç 500 hatası yok.
- **Veritabanı kapalıysa ne olur?** Bağlantı 3 saniyede zaman aşımına uğrar, 503 hatası
  ve açıklayıcı bir mesaj döner; sayfa donmaz.
