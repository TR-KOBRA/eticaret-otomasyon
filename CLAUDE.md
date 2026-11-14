# E-ticaret otomasyonu

Türkiye pazarı için AliExpress'ten ürün bulup marka, mağaza, içerik ve reklama giden modüler hat.
Her modül `eticaret/<modul>/` altında; bir öncekinin JSON çıktısını okur, kendi JSON + .md raporunu `cikti/` altına yazar.

## Bilgi bankası (her işten önce ilgili özeti oku)
`kaynaklar/ozetler/` — kullanıcının e-ticaret eğitim dokümanlarından çıkarılmış kurallar:
- `arastirma.md` — 8 kriter, 20 puanlık skor kartı (15+ teste al), viral 5 soru, rekabet analizi
- `fiyat-kar.md` — kâr formülü, hedef net marj ≥ %20, iade %15–30, başabaş ROAS/CPA, sermaye/nakit
- `tedarik.md` — 15 tedarikçi sorusu, sahte toptancı işaretleri
- `magaza.md` — mağaza 6 adım, ürün sayfası, güven unsurları, yasal sayfalar (KVKK, mesafeli satış, ETBİS)
- `instagram.md` — bio formülü, 4 öne çıkan, %50 reels / %30 carousel / %20 görsel, 20–30 içerik şartı
- `reklam.md` — ABO + broad, set başı 100–150 TL, metrik eşikleri, 3 kapatma kuralı, %15–20 ölçekleme
- `akis.md` — eksik listesi ve uçtan uca akış planı
Yeni doküman gelirse: `kaynaklar/gelen/`e konur → metni çıkar → ilgili özet dosyasını güncelle → `00-indeks.md`ye satır ekle.

## Kesin kurallar
- Bot korumaları (AliExpress CAPTCHA, Trendyol Cloudflare) atlatılmaz; Trendyol vb. için Apify kullanılır.
- Apify aylık bütçe 5 $ (ücretsiz planda hesap limiti değiştirilemiyor; kodda `APIFY_AYLIK_BUTCE_USD` ile korunur).
- API anahtarları sadece `.env`'de; asla yazdırılmaz, sohbete yazılmaz.
- Satın alınmış takipçi/beğeni, sahte yorum, lisanssız (nulled) tema kullanılmaz.
- Sağlık vaadi, abartılı kazanç vaadi, ürünü yansıtmayan yanıltıcı görsel üretilmez.
- Para harcayan veya dışarı yayın yapan adımlar (numune, reklam, paylaşım, domain) insan onayında durur.

## Çalıştırma
`eticaret/urun-arastirma/`: `python -W ignore arastir.py kesfet "<ingilizce kelime>"` ve `arastir.py urun <link> --kelime "<türkçe>" --trendyol`.
`arastir.py skorla cikti/urun-....json` kayıtlı ürünü AliExpress'e gitmeden yeniden puanlar (istem/ayar değişikliği sonrası).
AliExpress araması İngilizce, Trends/Trendyol Türkçe kelimeyle daha iyi çalışır.
Gemini metin modeli: `gemini-3.5-flash` (`gemini-flash-latest` ve `gemini-3.8-flash` 60 sn+ takılıyordu, 2.5 kapalı).
Trendyol yorumlu çalıştırma pahalı: ürün başına 15 yorum ≈ 0,37 $ çıktı → 4'e indirildi.
