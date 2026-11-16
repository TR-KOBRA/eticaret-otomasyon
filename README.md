# E-ticaret hattı

AliExpress ürününden Türkiye'de satışa kadar 11 adım. Adım 1 `urun-arastirma/`, adım 2–11 `hat.py` + `hat/`.

```
1 araştırma ─ skor ≥ 15 (TESTE AL) ─▶ hat.py yeni
2 tedarik    satıcı mesajı (15 soru), numune kontrol listesi          ⏸ onay: numune iyi
3 marka      8 isim + .com kontrolü, kimlik, renk/font, logo brifi    ⏸ onay: --secim isim=...
4 icerik     ürün sayfası, SSS, SEO, paket metinleri, yasal şablonlar
5 gorsel     Gemini: beyaz zemin, 2 yaşam, detay, kapak + yazı logo   ⏸ onay: görseller gerçeğe uygun
6 magaza     Shopify CSV + index.html önizleme (+ --gonder ile Shopify'da TASLAK ürün)
7 instagram  profil/bio, 4 öne çıkan kapağı, 24 içerik (12 reels / 7 carousel / 5 görsel) CSV
8 kreatif    4 açı × 3 hook, başlık, CTA, 3 ton metin, 3 UGC senaryosu  ⏸ onay
9 reklam     ABO + broad TR test planı (günlük = 3 × hedef CPA), kapatma eşikleri (+ --gonder ile Meta'da DURAKLATILMIŞ kampanya)
10 analiz    Reklam Yöneticisi CSV'si → kapat / izle / ölçekle + huni teşhisi
11 operasyon müşteri mesajları, stok eşiği, haftalık net kâr tablosu
```

## Panel (önerilen)

Masaüstündeki **E-ticaret Paneli** kısayolu ya da `panel/panel_ac.cmd` → http://127.0.0.1:8765 (sadece bu bilgisayar).

| Sayfa | Ne yapar |
|---|---|
| Ana sayfa | yapılacaklar (onay bekleyen / çalıştırılabilir adımlar, TESTE AL adaylar), satış hattı, Apify bütçesi |
| Ürün keşfi | tüm araştırmalar: maliyet, %20 marj için fiyat, Trendyol medyanı, fiyat uyumu; ürün çekmecesi (skor, fiyat bandı, pazar, riskler), favori / reddet / projeye çevir / yeniden puanla |
| Günlük tarama | zamanlanmış görev durumu, kelime listesi düzenleme, günlük raporlar |
| Projeler | aşamaya göre pano; proje sayfasında 11 adım (çalıştır, onayla, rapor, görsel, mağaza önizleme), kâr, reklam performansı (CPA/ROAS/huni), içerik takvimi, haftalık finans |
| Kâr hesaplayıcı | fiyat / indirim / kanal / iade / reklam payı → net kâr, marj, başabaş ROAS, hedef CPA, test bütçesi, paket teklifi |
| Ayarlar | bağlantılar (sadece bağlı mı), Apify harcaması, hesaplama varsayımları |

Panel komutları mevcut CLI'lar üzerinden çalıştırır. Shopify/Meta gönderimi (`--gonder`) panelde yoktur.

## Günlük tarama

Windows Görev Zamanlayıcı her gün 09:00'da `urun-arastirma/gunluk_calistir.cmd` çalıştırır (bilgisayar kapalıysa açılınca):
`gunluk-kelimeler.txt`'den sıradaki kelime → AliExpress (alakasız sonuçlar elenir) → Trendyol (aylık 3 $ tavanı) → en iyi 3 ürün
20 puanla değerlendirilir → `cikti/gunluk/<tarih>.md` ve birikimli `adaylar.md`. CAPTCHA çıkarsa durur, atlatmaz.

## Kullanım (terminal)

```bash
cd eticaret
python urun-arastirma/arastir.py urun <aliexpress-link> --kelime "türkçe kelime" --trendyol
python hat.py yeni urun-arastirma/cikti/urun-<id>-<zaman>.json --ad urunadi
python hat.py calistir urunadi              # ön koşulu sağlanan tüm adımlar
python hat.py durum urunadi
python hat.py onayla urunadi marka --secim isim=Esenra
python hat.py sec urunadi fiyat=749 gunluk_butce=450   # isteğe bağlı: set_butce, set_sayisi
python hat.py calistir urunadi analiz --csv meta-rapor.csv
```

Çıktılar `projeler/<ad>/` altında: her adım `NN-adim.md` (okunur rapor) + `NN-adim.json`, ayrıca `gorseller/`, `magaza/`,
`instagram/`, `yasal/`, `operasyon/`. Bir adımı yeniden üretmek için `python hat.py calistir <ad> <adim>`.

## .env (eticaret/.env ya da urun-arastirma/.env)

| Anahtar | Gerekli olduğu yer |
|---|---|
| `APIFY_TOKEN` | Trendyol rakipleri (aylık 5 $ bütçe korumalı) |
| `GEMINI_API_KEY` | analiz, marka, içerik, Instagram, kreatif (metin) · görsel üretimi **faturalandırma açık** olmalı |
| `GEMINI_METIN_MODEL`, `GEMINI_GORSEL_MODEL` | isteğe bağlı model değişimi |
| `SHOPIFY_MAGAZA`, `SHOPIFY_ADMIN_TOKEN` | `magaza --gonder` (Shopify özel uygulama, `write_products` izni) |
| `META_ERISIM_TOKENI`, `META_REKLAM_HESABI`, `META_PIXEL_ID` | `reklam --gonder` (sistem kullanıcısı tokeni, `ads_management`) |

## Güvenlik ilkeleri

- Para harcatan ya da yayına çıkan hiçbir şey otomatik değil: numune, domain, paylaşım ve reklam yayını insan işidir.
  Shopify ürünü **taslak**, Meta kampanyası **duraklatılmış** oluşturulur.
- Metin istemlerinin hepsi ortak kurallarla gider (`hat/ortak.py` KURALLAR): sağlık vaadi yok, başka marka adı yok,
  satıcı verisinde olmayan teknik iddia yok, sahte yorum/sayaç yok.
- Görseller satıcı fotoğrafını referans alır; ürün farklı görünüyorsa onaylanmaz.
- Yasal sayfalar şablondur; hukukçu / mali müşavir kontrolü gerekir.
