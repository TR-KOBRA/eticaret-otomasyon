# Ürün araştırma hattı

E-ticaret otomasyonunun ilk modülü. AliExpress'te aday ürün bulur, tek ürünü derinlemesine inceler,
Türkiye talebini (Google Trends) ve Trendyol rakiplerini (Apify) çıkarır, maliyet / fiyat / başa baş ROAS hesaplar
ve risk taraması yapar. Çıktılar `cikti/` klasörüne `.md` rapor ve `.json` ham veri olarak yazılır.

## Kurulum

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

`.env` dosyasına `APIFY_TOKEN` (Trendyol taraması) ve `GEMINI_API_KEY` (yorum analizi + skor kartının yorum gerektiren 5 kriteri) ekle; yoksa o bölümler atlanır.
Model `GEMINI_METIN_MODEL` ile değiştirilebilir (varsayılan `gemini-3.5-flash`).

## 1) Keşif: anahtar kelimeyle aday bul

```bash
python arastir.py kesfet "aroma diffuser" --icermeli "difüzör,aroma,koku" --trend "oda kokusu,koku makinesi"
```

- AliExpress araması **İngilizce** kelimeyle daha iyi sonuç verir; `--icermeli` başlıkta geçmesi gereken (Türkçe) kelimelerle alakasızları eler.
- `--trend` Türkiye'de insanların gerçekten aradığı Türkçe kelimeler olmalı (ör. "aroma difüzörü" neredeyse hiç aranmıyor, "oda kokusu" çok aranıyor).
- Diğer seçenekler: `--sayfa 3`, `--max-fiyat 2000`, `--min-satis 0`, `--sirala populer|satis|fiyat_artan`, `--trendyol` (rakip medyanıyla skorlar).
- Skor = talep (satış, 45) + memnuniyet (puan, 25) + fiyat boşluğu (Trendyol medyanı / tahmini maliyet, 30).

## 2) Ürün raporu: tek ürünü incele

```bash
python arastir.py urun <aliexpress-linki> --kelime "oda kokusu,koku makinesi" --trendyol
```

Rapor en üstte **karar** verir: 20 puanlık skor kartı (10 kriter × 0/1/2; 15+ TESTE AL, 10–14 İYİLEŞTİR, 0–9 ELE,
yüksek risk varsa ELE), kırmızı bayraklar, reklam kancası denemeleri ve paket önerisi. Ardından: özet, **riskler**, varyantlar, satıcının verdiği özellikler ve açıklama metni (kanıtlanabilir iddiaların kaynağı),
Türkiye'ye kargo, yorum dağılımı + düşük puanlı yorumlar, stok / doğrudan gönderim maliyeti, fiyat seçenekleri
(%20 net marjı tutturan **minimum fiyat** + rakip çeyrekleri; reklam payı ve beklenen iade maliyeti düşülmüş net kâr,
başabaş ROAS, reklam kapatma eşikleri, 2'li/3'lü paket), **rakip ve yorum analizi** (tekrar eden şikâyet → fırsat,
beğeniler, 5 boyutta farklılaşma, "neden benden alınır", SSS taslağı), Google Trends, Trendyol rakipleri.

`--kanal trendyol` pazaryeri komisyonuyla hesaplar (varsayılan `site`).

## 3) Yeniden değerlendirme (AliExpress'e gitmeden)

```bash
python arastir.py skorla cikti/urun-<id>-<zaman>.json [--trendyol --kelime "oda kokusu esansı"] [--kanal trendyol]
```

Ayarları (`hesap.py`) ya da istemleri değiştirdikten sonra kayıtlı ürünü yeniden puanlar. `--trendyol` rakipleri yeniden çeker
(Apify; ürün başına 4 yorumla bir çalıştırma ~0,1–0,4 $).

## Dosyalar

| Dosya | Görev |
|---|---|
| `aliexpress.py` | Arama + ürün detayı + açıklama + yorumlar (sayfanın kendi JSON verisi, normal Chromium) |
| `trendler.py` | Google Trends TR: ilgi, değişim, zirve/dip ayı, yükselen aramalar |
| `rakipler.py` | Trendyol (Apify `memo23/trendyol-scraper`): fiyat dağılımı, puan, favori, yorumlar |
| `hesap.py` | Maliyet, reklam payı, iade modeli, %20 marjlı minimum fiyat, ROAS/CPA, kapatma eşikleri, kanal (site/trendyol). **Varsayımlar `AYARLAR` / `KANALLAR` içinde** |
| `riskler.py` | Marka/kopya, sağlık iddiası, 110V, teslim süresi, yorum ve mağaza zayıflığı, kırılgan/sıvı/pil + desi |
| `rakip_analiz.py` | Rakip tablosu + yorumlardan şikâyet/beğeni/farklılaşma/SSS (Gemini; şikâyet uydurmaz) |
| `skor.py` | 20 puanlık skor kartı: 4 kriter veriden, 5 kriter Gemini'den, ayrışma rakip analizinden |
| `gemini.py` | Gemini REST yardımcısı (JSON şemalı yanıt) |
| `arastir.py` | Komut satırı ve rapor üretimi |

## Sınırlar ve kurallar

- Bot korumaları atlatılmaz. AliExpress doğrulama isterse script durur (çıkış kodu 2); bir süre bekleyip tekrar dene.
  Trendyol doğrudan erişimde Cloudflare doğrulaması gösterdiği için Apify kullanılır (sonuç başına ücretli).
- `tr.aliexpress.com` satış sayıları Türkiye görünümüne göredir ve genelde düşüktür.
- `hesap.py` içindeki gümrük, ithalat ve komisyon oranları kaba tahmindir; karar vermeden önce güncel mevzuat ve
  kendi kargo/POS anlaşmalarınla güncelle.
- Risk taraması kesin hüküm değildir, elle kontrol edilecek noktaları işaretler.
