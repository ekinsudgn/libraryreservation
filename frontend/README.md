# 3. Kısım – Frontend (HTML / CSS / JavaScript)

Kullanıcının gördüğü kısım. Saf HTML, CSS ve JavaScript ile yazıldı, herhangi bir
framework kullanılmadı. Sayfalar veriyi backend'den `fetch` ile JSON olarak alır ve
ekrana kendisi çizer.

## Sayfalar

| Sayfa | Ne var |
|---|---|
| `index.html` | Giriş ve kayıt (sekmeli tek sayfa) |
| `reserve.html` | Gün seçimi, alan türü filtresi, saatlik doluluk tablosu, rezervasyon formu |
| `my.html` | Aktif rezervasyonlar (iptal butonu ile) ve geçmiş rezervasyonlar |

## JavaScript dosyaları

| Dosya | Ne yapar |
|---|---|
| `js/api.js` | Backend ile konuşan **tek** dosya. `api.get()` / `api.post()`; hata gelirse mesajıyla birlikte fırlatır. |
| `js/ui.js` | Ortak yardımcılar: mesaj kutusu, giriş kontrolü (`requireLogin`), çıkış, tarih biçimleme, `escapeHtml` |
| `js/login.js` | Giriş / kayıt formları |
| `js/reserve.js` | Doluluk tablosunu çizer, hücreye tıklayınca formu doldurur, rezervasyon gönderir |
| `js/my.js` | Rezervasyon listelerini çizer, iptal işlemini yapar |

## Nasıl çalışıyor? (`reserve.html` örneği)

1. Sayfa açılınca `requireLogin()` → `GET /api/auth/me`. Giriş yoksa `index.html`'e yönlendirir.
2. `load()` → `GET /api/availability?date=...&kind=...`
3. Gelen JSON'daki her alan için bir tablo satırı, her saat için bir hücre çizilir.
   Hücrenin rengi `slots` değerinden gelir: yeşil boş, kırmızı dolu, mavi benim, gri geçmiş.
4. Boş hücreye tıklanınca form (alan + saat) otomatik dolar.
5. "Rezerve Et" → `POST /api/reservations`.
   - Başarılıysa yeşil mesaj ve tablo yeniden yüklenir.
   - Çakışma varsa backend 409 döner; `api.js` bunu hataya çevirir ve kırmızı mesaj gösterilir.

Frontend kendi başına "bu masa dolu mu?" kararı vermez. Tablodaki renkler sadece bilgi
amaçlı. Son kararı her zaman veritabanı verir. Biri tam aynı anda aynı masayı alırsa
kullanıcı yine doğru uyarıyı görür.

## Güvenlik ve kullanılabilirlik

- Kullanıcıdan gelen metinler (iptal nedeni, alan adları) ekrana basılmadan önce
  `escapeHtml()` ile temizlenir. Böylece birisi iptal nedenine `<script>` yazsa bile
  kod çalışmaz, düz metin olarak görünür (XSS koruması).
- Geçmiş günlere ve 14 günden sonrasına gidilemez; ilgili butonlar pasif olur.
- Seçilen gün adres çubuğunda tutulur (`reserve.html?date=2026-11-20&kind=room`);
  sayfa yenilenince aynı gün açılır.
- Tasarım dar ekranlarda da çalışır; tablo yatay kaydırılabilir.

## Sunumda anlatılacaklar

1. Üç sayfa ve her birinin işlevi.
2. `api.js`: bütün backend iletişiminin tek bir yerde toplanması.
3. Doluluk tablosunun JSON'dan nasıl çizildiği (`reserve.js` → `render()`).
4. **Canlı demo** (ana README'deki senaryo): giriş → rezervasyon → çakışma uyarısı → iptal.
5. XSS koruması.

## Olası sorular

- **Neden React / Vue kullanmadınız?** Üç sayfalık bir arayüz için gerek görmedik; saf
  JavaScript ile tarayıcının nasıl çalıştığını daha iyi göstermek istedik.
- **Tablo renkleri yanlışsa ne olur?** Örneğin sayfa açıkken başkası masayı aldıysa,
  kullanıcı "Rezerve Et"e bastığında veritabanı reddeder ve uyarı görünür. Tablo da
  yenilenir.
- **Kullanıcı tarayıcıda JavaScript ile kuralları atlatabilir mi?** Hayır. Frontend'deki
  kısıtlar (ör. tarih sınırı) sadece kolaylık için. Asıl kurallar veritabanında ve
  backend'de kontrol ediliyor.
