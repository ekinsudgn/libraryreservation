# 1. Kısım – Veritabanı (PostgreSQL)

Projenin en kritik isteri olan "çakışan rezervasyonların veritabanı seviyesinde
engellenmesi" bu klasörde çözülüyor.

## Dosyalar

| Dosya | Ne yapar |
|---|---|
| `schema.sql` | Tabloları, kısıtları, trigger'ı ve görünümü oluşturur |
| `seed.sql` | 10 masa ve 3 grup odası ekler |
| `init_db.py` | Veritabanını oluşturur, `schema.sql` ve `seed.sql`'i çalıştırır, demo kullanıcı ekler |
| `cakisma_testi.py` | 10 kullanıcının aynı anda aynı masayı istediği testi çalıştırır |

## Tablolar

```
users (1) ──────< reservations >────── (1) spaces
```

| Tablo | Önemli sütunlar |
|---|---|
| `users` | `student_no` (benzersiz), `full_name`, `email` (benzersiz), `password_hash` |
| `spaces` | `name`, `kind` (`desk` = masa, `room` = grup odası), `capacity`, `floor`, `is_active` |
| `reservations` | `user_id`, `space_id`, `starts_at`, `ends_at`, `status` (`active` / `cancelled`), `cancelled_at`, `cancel_reason` |
| `reservation_details` (görünüm) | Rezervasyonun anlık durumunu hesaplar: `upcoming`, `ongoing`, `completed`, `cancelled` |

Rezervasyonlar **hiçbir zaman silinmez**. İptal edilen kayıt `status = 'cancelled'`
olarak kalır, böylece kullanıcının geçmişi korunur.

## Çakışma engeli: EXCLUDE kısıtı

```sql
CONSTRAINT no_space_overlap EXCLUDE USING gist (
    space_id                          WITH =,
    tsrange(starts_at, ends_at, '[)') WITH &&
) WHERE (status = 'active')
```

Türkçesi: *"`space_id`'si aynı olan (`=`) iki aktif satırın zaman aralıkları kesişemez (`&&`)."*

- `tsrange(..., '[)')`: başlangıç dahil, bitiş hariç aralık. Bu yüzden 10:00–12:00 ile
  12:00–14:00 **çakışma sayılmaz**, uç uca rezervasyon yapılabilir.
- `WHERE (status = 'active')`: iptal edilen rezervasyonlar kontrole girmez, iptal edilen
  saat tekrar alınabilir.
- `btree_gist` eklentisi: sayı (`space_id`) ile zaman aralığını aynı GiST indeksinde
  karşılaştırabilmek için gerekiyor.

Aynı mantıkla `no_user_overlap` kısıtı da bir öğrencinin aynı saatte iki farklı yerde
rezervasyon tutmasını engelliyor.

### Neden uygulamada kontrol etmek yetmez?

"Önce `SELECT` ile masa boş mu bak, boşsa `INSERT` et" yöntemi tek kullanıcıda çalışır
ama iki kişi aynı anda istek gönderirse ikisi de "boş" sonucunu görür ve ikisi de kaydeder.
Buna **race condition (yarış durumu)** denir. EXCLUDE kısıtı kontrolü indeks üzerinden
atomik yapar, ikinci `INSERT` hata ile reddedilir.

## Diğer kurallar

| Kural | Nerede |
|---|---|
| Bitiş başlangıçtan sonra olmalı | `CHECK chk_order` |
| Tam saatte başlayıp bitmeli (10:00, 11:00…) | `CHECK chk_full_hours` |
| En fazla 4 saat | `CHECK chk_max_duration` |
| 08:00–22:00 arası, aynı gün | `CHECK chk_opening_hours` |
| Geçmiş saate rezervasyon yapılamaz | trigger `reservations_guard` |
| En fazla 14 gün sonrasına | trigger `reservations_guard` |
| Sadece başlamamış rezervasyon iptal edilebilir | trigger `reservations_guard` |
| İptal zamanı otomatik yazılır | trigger `reservations_guard` |
| Rezervasyonun saati / masası sonradan değiştirilemez | trigger `reservations_guard` |
| Kayıt silinemez, sadece iptal edilir | trigger `reservations_guard` |

`CHECK` kısıtlarının içinde "şu anki zaman" (`now()`) kullanılamadığı için zamana
bağlı kurallar trigger ile yazıldı.

## Çalıştırma

Proje klasöründen:
```
python database/init_db.py
python database/cakisma_testi.py
```

Beklenen test çıktısı:
```
1) 10 kullanıcı aynı anda Masa 101 / ... 10:00-12:00 istiyor
   => 1 başarılı, 9 reddedildi  ->  DOĞRU ✔
2) Sınır durumları
   11:00-13:00 (kısmi çakışma)         REDDEDİLDİ ✔
   09:00-10:00 (hemen önce, uç uca)    BAŞARILI   ✔
   12:00-13:00 (hemen sonra, uç uca)   BAŞARILI   ✔
3) İptal edilen saat tekrar rezerve edilebilir mi?   BAŞARILI ✔
```

## Sunumda anlatılacaklar

1. Üç tablo ve aralarındaki ilişki (ER şeması yukarıda).
2. `no_space_overlap` kısıtı satır satır: `=`, `&&`, `[)`, `WHERE status = 'active'`.
3. Race condition nedir, neden uygulama kontrolü yetmez.
4. **Canlı:** `python database/cakisma_testi.py` çalıştır, 1 başarılı / 9 reddedildi sonucunu göster.
5. Trigger ile korunan kurallar ve kayıtların neden silinmediği.

## Olası sorular

- **Neden PostgreSQL?** MySQL ve SQLite'ta EXCLUDE kısıtı yok. Aynı işi trigger ve kilitle
  yapmak mümkün ama daha karmaşık ve hataya açık.
- **Neden `TIMESTAMP` (saat dilimsiz)?** Kütüphane tek bir şehirde. Bütün saatler yerel
  saat (Europe/Istanbul) olarak tutuluyor; bağlantı açılırken saat dilimi ayarlanıyor.
- **İptal edilen kayıt neden silinmiyor?** Kullanıcının geçmiş rezervasyonlarını görebilmesi
  isterin bir parçası. Silseydik geçmiş kaybolurdu.
- **Test çıktısında neden bazen "deadlock sonrası tekrar denendi" yazıyor?** Eşzamanlı
  iki INSERT, EXCLUDE kontrolü sırasında birbirini bekleyebilir; PostgreSQL birini iptal
  eder. Bu bir hata değil, kısıtın bilinen bir davranışı. Tekrar denemede normal çakışma
  hatası gelir. Önemli olan sonuç değişmiyor: her zaman tam 1 kayıt kabul ediliyor.
  Test 50 kez çalıştırıldı, 50'si de geçti (18'inde deadlock + tekrar deneme oldu).
- **Performans?** EXCLUDE kısıtı otomatik olarak bir GiST indeksi oluşturur. Kontrol tüm
  tabloyu taramaz, indeks üzerinden yapılır.
