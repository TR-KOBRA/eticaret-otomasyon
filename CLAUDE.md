# E-ticaret otomasyonu

Türkiye pazarı için ürün bulup (ana yol: Amazon sinyali → Türkiye doğrulaması → yerli toptancı; eski yol: AliExpress) marka, mağaza, içerik ve reklama giden modüler hat.
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
- `mert-kurtul.md` — kullanıcının takip ettiği yöntem: Amazon/TikTok filtreleri, yorum hızı, TR doygunluk (yorum<100, 3–5 güçlü rakip, ~20 reklamveren), yerli tedarik, KDV mahsubu, Shopify %2
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
Otomatik tarama: Görev Zamanlayıcı "Eticaret Gunluk Urun Taramasi" Pzt+Per 09:00 → `urun-arastirma/sinyal_calistir.cmd` (2 kategori × 30, 3 doğrulama, Trendyol 20 sonuç).
Eski AliExpress günlük taraması `gunluk.py` (kelimeler `gunluk-kelimeler.txt`) zamanlanmıyor; panelde arşiv.
Rakip kıyası: rakip_analiz `benzer_rakipler` → `rakipler.benzer_rakip` (aynı tür ürünler; <3 ise benzer_yok). Günlük taramada alaka (baş kelime + Gemini) ve ön eleme (`--on-eleme-kat`).
Skor: piyasa (benzer rakip medyanı) fiyatında kâr yoksa (kar_marji=0) toplam ≥15 olsa da karar İYİLEŞTİR.
Gemini: ücretsiz katmanda model başına ~20 istek/gün; `gemini.py` kota dolunca GEMINI_YEDEK_MODELLER'e (flash-lite) geçer, hepsi doluysa GeminiKota.
Toptan fiyat: `hat.py sec <proje> tedarik_fiyati=<TL> tedarik_kargo=<TL>` → `Proje.maliyet()` / `fiyat()` yeniden hesaplar. Mağaza bilgisi: `kargo_esigi`, `hazirlik_gun`.
Uçtan uca test sonuçları ve açık konular: `TEST-RAPORU.md` (test projesi `projeler/tuy-araci`).
Ürün sinyali (Mert Kurtul yöntemi): `urun-arastirma/sinyal.py` — Amazon "New Releases" (Apify fanndev/amazon-bestsellers-movers-tracker,
CAPTCHA çözmez, ~0,003 $/ürün; Movers & Shakers listesi boş döndüğü için yeni çıkanlar kullanılıyor) → Mert filtresi → Gemini seçimi (TR'ye lokalleşen,
problem çözen, sarf/gıda/marka değil) → Trendyol benzer + `rakipler.doygunluk` → `alis_tavani` (TR medyanında %20 net için KDV dahil max toptan alış).
Kategoriler `sinyal-kategoriler.txt`, aynı gün Amazon listesi önbellekten, `SINYAL_APIFY_TAVAN_USD` (4 $). Panel: "Ürün sinyali" sayfası.
Maliyet modeli (2026-11-18): senaryo `yerli` (KDV dahil toptan alış + kargo + koli, gümrük yok) varsayılan; `kdv_mahsup` (yerli kalemlerin alış KDV'si düşülür),
`shopify_komisyonu` %2 (site); `brut_marj_yuzde` (reklam/iade öncesi, hedef %40–50). Skor kapıları: doygunluk "doymus" ve giyim/takı/ayakkabı → en fazla İYİLEŞTİR.
Meta Reklam Kütüphanesi: `urun-arastirma/reklam_kutuphanesi.py` — herkese açık sayfa, normal Playwright (gizlenme/undetected-chromedriver YOK,
`facebook-ad-library-scraper` paketi bu yüzden kullanılmadı), aramalar arası 6 sn; ilk sayfadaki farklı reklamveren ≥20 doymuş, 8–19 kalabalık.
Sinyal akışına bağlı (`--reklam-yok` ile kapatılır).
Shopify panel: `panel/shopify_baglanti.py` (Admin GraphQL, sadece okuma: mağaza, siparişler→ciro/sipariş/sepet/iade, ürünler; 5 dk önbellek),
panel "Mağaza (Shopify)" sayfası; anahtarlar panel formuyla `eticaret/.env`'e yazılır (`/api/anahtar`, değer asla geri dönmez, biçim doğrulanır);
projede "Shopify'a taslak gönder" onay kutusu ister → `hat.py calistir <p> magaza --gonder` (TASLAK). Gerçek mağazayla henüz test edilmedi.
Sinyal → proje (2026-11-18): `urun-arastirma/sinyal_proje.py` sinyal kaydını araştırma JSON'una çevirir (`cikti/urun-sinyal-<asin>-….json`,
`kaynak: "sinyal"`, maliyet = alış tavanı TAHMİNİ, yoksa Amazon fiyatı × kur × 0,35); panel `/api/sinyal-json/{asin}` + "Projeye çevir".
Tedarik adımı yerli öncelikli (`hat/tedarik.py`): alış tavanı projenin satış fiyatından, piyasa medyanı ayrı uyarı; Trendyol satıcıları (link
`-p-<id>` ile tekil), İstoç / üretim / pazaryeri toptancısı yolları, telefon metni, 15 soru; İngilizce AliExpress mesajı sadece AliExpress kaynaklıda ek.
Toptancı kartı secimler: `toptanci_ad`, `toptanci_tel`, `toptanci_not` (metin), `tedarik_tipi` (yerli/uretim/ithal), `fatura` (var/yok),
`dropship` (evet/hayir), `moq`, `teslim_gun` (sayı) — panel `/sec` bunları doğrular.
`hesap.alis_tavani(satis, a)` ortak fonksiyon (sinyal, tedarik, keşif kartları). Keşif kartı "Gereken" yerine "Alış tavanı", AliExpress kayıtları "eski yöntem".
Gemini: `json_sor(..., toplu=True)` önce flash-lite (sinyal seçimi/eşleştirme, günlük alaka; ~1 sn) → ana modelin kotası puanlama/metne kalır.
Trends: `trendler.py` trendspyg `compat.TrendReq` (engine="http": Google reddederse Chrome'a DÜŞMEZ); yoksa pytrends.
TikTok: `sinyal.py --tiktok` (lergassy/tiktok-shop-top-products-scraper) Apify ücretsiz planında veri vermiyor; doliz çerez, datapeak/bovi residential proxy istiyor → panelde düğme yok.
Testler: `python testler.py` (unittest, internetsiz). Panel statik dosyaları `Cache-Control: no-cache`.
