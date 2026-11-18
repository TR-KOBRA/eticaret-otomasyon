# E-ticaret otomasyonu

Türkiye pazarı için AliExpress'ten ürün bulup marka, mağaza, içerik ve reklama giden modüler hat.
Adım 1 `urun-arastirma/` (kendi CLI'ı), adım 2–11 `hat.py` + `hat/<adim>.py`: her ürün `projeler/<ad>/` klasörü,
adımlar `durum.json`daki onay kapılarıyla sırayla çalışır (bkz. `README.md`). Yeni adım eklerken `hat/ortak.py` ADIMLAR'a
kaydet, `calistir(p: Proje, args)` yaz, `p.yaz(adim, veri, md)` ile çıktı ver, metin üretiminde `metin_json` (ortak KURALLAR) kullan.

## Bilgi bankası (her işten önce ilgili özeti oku)
`kaynaklar/ozetler/` — kullanıcının e-ticaret eğitim dokümanlarından çıkarılmış kurallar:
- `arastirma.md` — 8 kriter, 20 puanlık skor kartı (15+ teste al), viral 5 soru, rekabet analizi
- `fiyat-kar.md` — kâr formülü, hedef net marj ≥ %20, iade %15–30, başabaş ROAS/CPA, sermaye/nakit
- `tedarik.md` — 15 tedarikçi sorusu, sahte toptancı işaretleri
- `magaza.md` — mağaza 6 adım, ürün sayfası, güven unsurları, yasal sayfalar (KVKK, mesafeli satış, ETBİS); Shopify yayın öncesi kontrol, upsell/bundle, indirim-katkı, ücretsiz kargo eşiği, dönüşüm hunisi
- `instagram.md` — bio formülü, 4 öne çıkan, %50 reels / %30 carousel / %20 görsel, 20–30 içerik şartı
- `reklam.md` — ABO + broad, günlük ≈ 3 × hedef CPA (kodda `reklam.butce_hesapla`), metrik eşikleri, 4 kapatma kuralı (hedef CPA'ya göre), %10–20 ölçekleme; Pixel/CAPI/Purchase testi, bütçe = hedef CPA × 3, retargeting, Lookalike, CBO/ABO
- `akis.md` — eksik listesi ve uçtan uca akış planı
Yeni doküman gelirse: `kaynaklar/gelen/`e konur → metni çıkar → ilgili özet dosyasını güncelle → `00-indeks.md`ye satır ekle.

## Kesin kurallar
- Bot korumaları (AliExpress CAPTCHA, Trendyol Cloudflare) atlatılmaz; Trendyol vb. için Apify kullanılır.
- Apify aylık bütçe 5 $ (ücretsiz planda hesap limiti değiştirilemiyor; kodda `APIFY_AYLIK_BUTCE_USD` ile korunur).
- API anahtarları sadece `.env`'de; asla yazdırılmaz, sohbete yazılmaz.
- Satın alınmış takipçi/beğeni, sahte yorum, lisanssız (nulled) tema kullanılmaz.
- Sağlık vaadi, abartılı kazanç vaadi, ürünü yansıtmayan yanıltıcı görsel üretilmez.
- Para harcayan veya dışarı yayın yapan adımlar (numune, reklam, paylaşım, domain) insan onayında durur.

## Bilinen durumlar
- Gemini görsel modelleri ücretsiz katmanda kota 0 → faturalandırma açılana kadar görsel adımı satıcı fotoğraflarını GEÇİCİ kullanır.
- Shopify/Meta gönderimi kodlu ama gerçek hesapla test edilmedi (API sürümü `SHOPIFY_API_SURUM`, `META_API_SURUM`).
- `projeler/deneme` elenmiş bir ürünle (`--zorla`) uçtan uca test projesidir.

## Çalıştırma
`eticaret/urun-arastirma/`: `python -W ignore arastir.py kesfet "<ingilizce kelime>"` ve `arastir.py urun <link> --kelime "<türkçe>" --trendyol`.
`arastir.py skorla cikti/urun-....json` kayıtlı ürünü AliExpress'e gitmeden yeniden puanlar (istem/ayar değişikliği sonrası).
AliExpress araması İngilizce, Trends/Trendyol Türkçe kelimeyle daha iyi çalışır.
Gemini metin modeli: `gemini-3.5-flash` (`gemini-flash-latest` ve `gemini-3.8-flash` 60 sn+ takılıyordu, 2.5 kapalı).
Trendyol yorumlu çalıştırma pahalı: ürün başına 15 yorum ≈ 0,37 $ çıktı → 4'e indirildi.
Panel: `panel/sunucu.py` (FastAPI, 127.0.0.1:8765) + `panel/index.html`, `app.js`, `app.css` (derlemesiz). Komutları CLI'lar üzerinden çalıştırır;
Panel tasarımı: açık tema varsayılan (koyu seçilebilir), karar dili "Olur / Belki / Olmaz" (TESTE AL / İYİLEŞTİR / ELE), önce hüküm + tek cümle neden, ayrıntı açılır bölümlerde; grafikler dataviz kuralları (ince işaret, 2px boşluk, ipucu).
`--gonder` panelde yok. Favori/red işaretleri `panel/veri.json`, iş logları `panel/isler/` (git dışı).
Günlük tarama: `urun-arastirma/gunluk.py` (Görev Zamanlayıcı "Eticaret Gunluk Urun Taramasi", 09:00), kelimeler `gunluk-kelimeler.txt`.
Rakip kıyası: rakip_analiz `benzer_rakipler` → `rakipler.benzer_rakip` (aynı tür ürünler; <3 ise benzer_yok). Günlük taramada alaka (baş kelime + Gemini) ve ön eleme (`--on-eleme-kat`).
Skor: piyasa (benzer rakip medyanı) fiyatında kâr yoksa (kar_marji=0) toplam ≥15 olsa da karar İYİLEŞTİR.
Gemini: ücretsiz katmanda model başına ~20 istek/gün; `gemini.py` kota dolunca GEMINI_YEDEK_MODELLER'e (flash-lite) geçer, hepsi doluysa GeminiKota.
Toptan fiyat: `hat.py sec <proje> tedarik_fiyati=<TL> tedarik_kargo=<TL>` → `Proje.maliyet()` / `fiyat()` yeniden hesaplar. Mağaza bilgisi: `kargo_esigi`, `hazirlik_gun`.
Uçtan uca test sonuçları ve açık konular: `TEST-RAPORU.md` (test projesi `projeler/tuy-araci`).
