# Uçtan uca test — 16.11.2026

Gerçek bir ürünle (AliExpress → 11 adım) sistemin tamamı çalıştırıldı. Test projesi: `projeler/tuy-araci` (marka **PatiPratik**, "deneme" işaretli).

## 1. Geniş tarama (6 kategori, 18 ürün + önceki 7)

| Kategori | Sonuç |
|---|---|
| Sensörlü LED lamba | 3 ürün, en iyi 16/20 (İYİLEŞTİR — piyasa fiyatında kâr yok) |
| Silikon streç kapak | alaka filtresi drone kılıflarını kaçırdı (bkz. açık konular) |
| Çekmece düzenleyici, poşet kapatma, telefon tutucu, kablo kutusu | 9–14/20, hepsi kârsız |

**Ana bulgu:** hiçbir ürün TESTE AL almadı. Neden: maliyet AliExpress **tek adet perakende** fiyatından hesaplanıyor; Trendyol rakipleri toptan
getiriyor (örn. maliyet 409 ₺, %20 marj için 1.199 ₺ gerekiyor, Trendyol medyanı 350 ₺). Gerçek kârlılık tedarikçiden toptan fiyat gelince belli olur
→ toptan fiyat girişi eklendi (aşağıda).

## 2. Adım adım sonuçlar

| Adım | Durum | Testte bulunan ve düzeltilen |
|---|---|---|
| 1 Araştırma | ✓ | Gemini günlük kotası (20/gün) doldu → ürünler yanlışlıkla **ELE** oluyordu; artık **EKSİK VERİ** + yedek model (flash-lite) + puanlanamayan ürün "görüldü" sayılmıyor + kota doluysa Apify harcanmıyor |
| Kapı: TESTE AL değilse proje açılmaz | ✓ | `--zorla` olmadan reddetti |
| 2 Tedarik | ✓ | Arama linki yarım başlıkla arıyordu → Türkçe pazar kelimesi; kargo ücreti TL biçimi; **toptan fiyat girişi** (`tedarik_fiyati`, `tedarik_kargo`) maliyet/fiyat/reklam eşiklerini yeniden hesaplıyor; girilen kargo navlun varsayımını eziyordu → düzeltildi |
| 3 Marka | ✓ (24 sn) | Kapı: isim seçilmeden onay reddedildi |
| 4 İçerik | ✓ | Sağlık/abartı yok, teknik iddialar satıcı açıklamasında doğrulandı. `[X]` yer tutucuları → `kargo_esigi`, `hazirlik_gun` ile dolduruluyor, iade 14 gün (yasal), kalan boşluk sayısı uyarısı; "3ü" → "3'ü" |
| 5 Görsel | ✓ (geçici) | Gemini görsel kotası 0 → satıcı fotoğrafı GEÇİCİ. Logo "PATIPRATIK" (noktasız I) → Türkçe büyük harf **PATİPRATİK** |
| 6 Mağaza | ✓ | Shopify handle "3-u-1…baki" → `patipratik-3u-1-arada-…`; fiyatlar "1,199 TL" → "1.199 TL"; sayfa tarayıcıda kontrol edildi |
| 7 Instagram | ✓ | 24 içerik (12/7/5), yasaklı ifade yok. Öne çıkan kapakları sadece ilk kelimeyi yazıyordu ("Sizden") → tam başlık, iki satır |
| 8 Kreatif | ✓ | "Tek hareketle **tüm** tüylerden kurtulun" gibi kesin vaat → ortak kurallara eklendi + her yapay zekâ raporunda otomatik **abartı taraması** |
| 9 Reklam | ✓ | 4 set × 180 ₺ = 3 × hedef CPA; kapatma eşiği 5 günde ulaşılabilir; Meta istekleri PAUSED. Bütçe 5 ₺'ye yuvarlanıyor, numune onayı listede işaretli |
| 10 Analiz (test CSV) | ✓ | 4 kararın 4'ü beklenen (KAPAT/ÖLÇEKLE/KAPAT/İZLE). Set adındaki "\|" tabloyu bozuyordu; çelişkili "48 saati bekle" mesajı; eksi süre → düzeltildi |
| 11 Operasyon | ✓ | "Kargo süresi" sorusuna kargoya verme süresi yazılıyordu → yalnızca "kargoya verilir" cümlelerine |
| Panel | ✓ | Proje panoda, 11/11, reklam grafikleri test verisiyle; konsol hatası yok |

## 3. Açık konular (senin kararın / sonraki iş)

- **Gemini faturalandırma:** ücretsiz katman günde ~20 istek (model başına) ve görsel üretimi kapalı. Gerçek kullanımda AI Studio'da faturalandırmayı aç.
- **Maliyet varsayımları** (Ayarlar): adet başı navlun 60 ₺ + yurt içi kargo 90 ₺ + paket 25 ₺ küçük ürünlerde yüksek; numune ve kargo anlaşmasından sonra güncelle.
- **Alaka filtresi** iki kelime eşleşmesiyle çalışıyor; "silikon … kapak" drone kılıfını geçirdi. Daha sıkı kural ya da Gemini ile alaka kontrolü düşünülebilir.
- **Rakip karşılaştırması** kelime düzeyinde (aynı ürün değil): LED projektör, "sensörlü led lamba" medyanıyla kıyaslandı.
- Yasal sayfalar ve SSS'de işletme bilgileri (adres, kargo firması, iletişim) `[X]` olarak kalıyor — gerçek bilgilerle doldur.
- Shopify/Meta gönderimi gerçek hesapla hâlâ test edilmedi.

## 4. Test sonrası geliştirmeler (17.11.2026)

- **Benzer rakip eşleştirmesi:** rakip analizi (aynı Gemini isteği, ek kota yok) Trendyol listesinden ürünümüzle aynı tür/işlevdekileri seçer;
  fiyat seçenekleri ve kâr kriteri bu alt kümenin medyanıyla hesaplanır. 3'ten az eşleşmede fiyat kıyası yapılmaz, rapor ve panel
  "Piyasada aynısı yok" der, kâr kriteri otomatik tam puan almaz (1/2). Test: tüy aleti için 60 sonucun 0'ı aynı ürün (hepsi yapışkan rulo) — doğru.
- **Alaka filtresi:** başlıkta ürün türünü söyleyen baş kelime şart (tavan spotu artık "sensörlü led lamba" sayılmıyor); ardından tek Gemini
  isteğiyle aksesuar/yedek/başka ürünler elenir (`--alaka-yok` ile kapatılabilir).
- **Ön eleme:** derin incelemeden önce AliExpress fiyatından %20 marj için gereken fiyat, Trendyol'da kelimenin üst çeyrek fiyatının 2,5 katını
  aşıyorsa ürün elenir (`--on-eleme-kat`, `GUNLUK_ON_ELEME_KAT`). Test: "silikon streç kapak" taramasında 8 ürün Gemini'ye hiç gitmeden elendi.
  Kalanlar piyasaya yakınlığa göre sıralanır.
- **Kelime listesi:** fiyatı daha yüksek 5 niş eklendi (kedi su pınarı, kedi cam yatağı, köpek araç koltuk örtüsü, otomatik mama kabı, çanta içi düzenleyici).
