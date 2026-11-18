"""2 · Tedarik (yerli öncelikli): Trendyol satıcısı / İstoç / Türkiye'de ürettirme yolları, toptancıya telefon-WhatsApp metni,
15 soru, toptancı kartı, numune kontrol listesi (kaynaklar/ozetler/tedarik.md, mert-kurtul.md).

Hiçbir mesaj gönderilmez, arama yapılmaz; sadece metin ve yol haritası üretilir. Numune / toptan alım insan onayıdır.
AliExpress satıcısına İngilizce mesaj yalnızca ek olarak (ürün AliExpress araştırmasından geldiyse) verilir.
"""
from __future__ import annotations

import re
import urllib.parse

from ortak import Proje, tl

SORULAR_TR = [
    "Ticari unvanınız ve vergi numaranız nedir?", "Ürünü kendiniz mi üretiyorsunuz, yoksa ithalatçı / toptancı mısınız?",
    "Minimum sipariş adedi (MOQ) nedir? 10 / 50 / 100 adette birim fiyat nedir?", "Fiyatlar KDV dahil mi, faturalı mı?",
    "Siparişleri benim müşterime tek tek, faturanız/fiyat etiketi olmadan gönderebilir misiniz (dropship)? Adet başı kargo + paketleme ücreti?",
    "Kargoya veriş süresi kaç gün, hangi kargo firması?", "Hangi ödeme yöntemlerini kabul ediyorsunuz, vadeli çalışma imkânı var mı?",
    "Numune gönderiyor musunuz, ücreti nedir?", "Hasarlı/hatalı ürünlerde iade ve değişim nasıl işliyor?",
    "Stok durumunu ve stok bitişini nasıl bildiriyorsunuz?", "Fiyat değişikliklerini ne kadar önce bildiriyorsunuz?",
    "Ürün görsellerini ve videolarını kendi sitemde ve reklamlarımda kullanabilir miyim?",
    "Kendi markamla / etiketimle paketleme mümkün mü, hangi adetten itibaren?", "Münhasırlık veya bölge kısıtı var mı?",
    "Yazılı sözleşme ile çalışıyor musunuz?",
]
KIRMIZI_BAYRAK = [
    "Sadece ön ödemeli havale veya kripto istiyor", "Fiyat piyasanın çok altında", "Yeni domain, kurumsal bilgi yok",
    "Fotoğraflar başka sitelerde de aynı", "Yeni/az takipçili sosyal hesap", "Tek iletişim kanalı",
    "Sicil veya vergi numarası vermekten kaçınıyor", "Fatura kesmek istemiyor",
]
SORULAR_EN = [
    "Are you the manufacturer of this product or a reseller?",
    "What is your minimum order quantity (MOQ) and your price for 10 / 50 / 100 units?",
    "Can you ship to Turkey with a tracked method? Which carrier, how many days, and what is the cost?",
    "Can I order 1–2 samples first? What is the sample price and shipping time?",
    "What are the exact product dimensions, net weight and packed weight (with box)?",
    "May I use your product photos and videos on my own store and ads?",
]
# Toptancı kartı: panelde/`hat.py sec` ile girilen alanlar
KART = [("toptanci_ad", "Toptancı / üretici"), ("toptanci_tel", "Telefon / WhatsApp"), ("tedarik_tipi", "Tür (yerli / uretim / ithal)"),
        ("tedarik_fiyati", "Birim alış (KDV dahil TL)"), ("moq", "Minimum adet"), ("fatura", "Fatura"), ("dropship", "Tek tek gönderim"),
        ("teslim_gun", "Kargoya veriş (gün)"), ("toptanci_not", "Not")]


def _kelime(p: Proje) -> str:
    ty = p.veri.get("trendyol") or {}
    if ty.get("kelime"):
        return ty["kelime"]
    k = next(iter(((p.veri.get("trendler") or {}).get("kelimeler") or {}).keys()), None)
    return k or " ".join(re.sub(r"[^\w\s-]", " ", p.urun.get("baslik", "").split(":")[0]).split()[:4])


def _saticilar(p: Proje) -> list[dict]:
    """Aynı ürünü Trendyol'da satanlar (en çok yorumdan aza): telefonları mesafeli satış sözleşmesinde."""
    ty = p.veri.get("trendyol") or {}
    liste = ty.get("benzerler") or ty.get("urunler") or (p.veri.get("rakip_analizi") or {}).get("rakip_tablosu") or []
    goruldu, out = set(), []
    for x in sorted(liste, key=lambda x: -(x.get("degerlendirme") or 0)):
        link = x.get("link") or ""
        pid = re.search(r"-p-(\d+)", link)
        anahtar = pid.group(1) if pid else link
        if not link or anahtar in goruldu:
            continue
        goruldu.add(anahtar)
        s = {k: x.get(k) for k in ("ad", "marka", "satici", "fiyat", "degerlendirme")}
        s["link"] = link.split("?")[0]
        if not s.get("marka"):
            m = re.search(r"trendyol\.com/([^/]+)/", link)
            s["marka"] = m.group(1) if m else None
        out.append(s)
    return out[:8]


def telefon_metni(p: Proje, fiyat_tavani: float | None) -> str:
    urun = p.urun.get("baslik", "")[:80]
    s = [f"Merhaba, iyi günler. Ben [ADINIZ], [ŞEHİR]'de online satış yapıyorum. Trendyol'da sattığınız \"{urun}\" ürünüyle ilgili arıyorum.",
         "Bu ürünü kendi sitemde ve sosyal medya reklamlarıyla satmayı planlıyorum; düzenli çalışabileceğim bir tedarikçi arıyorum.",
         "Birkaç sorum olacak:",
         "1. Toptan fiyatınız nedir (10 / 50 / 100 adet), KDV dahil ve faturalı mı?",
         "2. Siparişleri benim müşterime tek tek, fiyat etiketi/faturanız olmadan gönderebilir misiniz? Adet başı kargo + paket ne tutar?",
         "3. Kaç günde kargoya verirsiniz, iade ve hasarlı üründe nasıl çalışırız?",
         "4. Ürün fotoğraf ve videolarını kullanabilir miyim?",
         "Önce 1-2 adet numune alıp kaliteyi görmek istiyorum. Uygun olursa toplu alımda indirimle devam ederiz."]
    if fiyat_tavani:
        s.append(f"(Kendine not: KDV dahil {tl(fiyat_tavani)} üstü kârsız — pazarlıkta bu sınırın altında kal.)")
    return "\n".join(s)


def calistir(p: Proje, args=None):
    import hesap
    u = p.urun
    kelime = _kelime(p)
    ty_ozet = (p.veri.get("trendyol") or {}).get("ozet") or {}
    a = {**hesap.AYARLAR, **{k: v for k, v in (p.veri.get("ayarlar") or {}).items() if k in hesap.AYARLAR}}
    # Tavan projenin gerçekten kullandığı satış fiyatından; piyasa (Trendyol medyanı) ayrıca gösterilir
    hedef_fiyat = float(p.secim("fiyat") or 0) or (p.fiyat() or {}).get("fiyat") or ty_ozet.get("medyan")
    piyasa = ty_ozet.get("medyan")
    tavan = hesap.alis_tavani(hedef_fiyat, a) if hedef_fiyat else None
    tavan_piyasa = hesap.alis_tavani(piyasa, a) if piyasa else None
    saticilar = _saticilar(p)
    an = p.veri.get("rakip_analizi") or {}
    kr = p.veri.get("kargo_riski") or {}
    ae = "aliexpress" in str(u.get("link") or "")

    kontrol = [
        "Ürün, ilandaki fotoğraflarla aynı mı (renk, boyut, malzeme)?",
        "Paket ölçüsü ve ağırlığı (desi) — gerçek kargo ücretini buna göre güncelle (hesap.py yurtici_kargo_tl).",
        "Faturası geldi mi, KDV doğru mu (KDV mahsubu için şart)?",
        "Kutudan çıkış videosu çek (Instagram 'Nasıl Kullanılır' öne çıkanı ve reklam UGC'si için kullanılacak).",
        "Kullanım süresi/dayanıklılık: 3–7 gün gerçek kullanım.",
    ]
    kontrol += [f"Rakip şikâyeti kontrolü: {x['konu']} — numunede de var mı?" for x in an.get("sikayetler") or []]
    kontrol += [f"Kargo riski: {n} — paketleme yeterli mi?" for n in kr.get("nedenler") or []]
    kontrol += [f"Kontrol et: {r['konu']}" for r in p.veri.get("riskler") or [] if r["seviye"] != "bilgi"]

    q = urllib.parse.quote(kelime)
    yollar = [
        {"ad": "Trendyol satıcısı", "nasil": "Ürünü sepete ekle → ödeme sayfasında 'Mesafeli Satış Sözleşmesi'ni aç → satıcının unvanı ve telefonu "
                                            "orada yazar. Ara; tek tek gönderim + toplu alım indirimi iste.",
         "link": f"https://www.trendyol.com/sr?q={q}", "risk": "Ürün tutunca satıcı vermek istemeyebilir → stoğu toptan al ya da ürettir."},
        {"ad": "İstoç / toptancı çarşıları", "nasil": "İstoç (İstanbul) ve şehrindeki toptancılar: faturalı, çoğu Çin'den konteynerle getiren ithalatçı. "
                                                      "Google'da '<ürün> toptan' ara, bul ve ara.",
         "link": f"https://www.google.com/search?q={urllib.parse.quote(kelime + ' toptan')}", "risk": "MOQ yüksek olabilir; aracı olabilir."},
        {"ad": "Türkiye'de ürettirme", "nasil": "Malzemesine göre üretici bul (plastik → enjeksiyon atölyesi, tahta → marangoz, kumaş → tekstilci). "
                                                "Önce reklam testi, sipariş gelirse üretime geç (Mert: rakibe '10-0 öne geçmek').",
         "link": f"https://www.google.com/search?q={urllib.parse.quote(kelime + ' imalatçı')}", "risk": "Kalıp/ilk üretim maliyeti; numune süresi uzun."},
        {"ad": "Pazaryeri toptancıları", "nasil": "Trendyol / Hepsiburada'da toptan satan ve dropship yapan satıcılara komisyonla getirmeyi öner.",
         "link": f"https://www.trendyol.com/sr?q={urllib.parse.quote(kelime + ' toptan')}", "risk": "Kalite değişken; numunesiz başlama."},
    ]
    kart = {k: p.secim(k) for k, _ in KART if p.secim(k) not in (None, "")}
    mesaj = telefon_metni(p, tavan)
    mesaj_en = None
    if ae:
        mesaj_en = ("Hello, I am planning to sell this product in Turkey and may place regular orders if the sample quality is good.\n"
                    f"Product: {u.get('link')}\n\nCould you please answer:\n"
                    + "\n".join(f"{i}. {q}" for i, q in enumerate(SORULAR_EN, 1)) + "\n\nThank you!")

    veri = {"kelime": kelime, "alis_tavani": tavan, "hedef_fiyat": hedef_fiyat, "piyasa_medyan": piyasa, "alis_tavani_piyasa": tavan_piyasa, "saticilar": saticilar, "yollar": yollar,
            "telefon_metni": mesaj, "sorular_tr": SORULAR_TR, "toptanci_karti": kart, "numune_kontrol": kontrol,
            "kirmizi_bayraklar": KIRMIZI_BAYRAK, "mesaj_en": mesaj_en}
    m = p.maliyet()
    md = [f"# Tedarik — {u.get('baslik', '')[:80]}", ""]
    if tavan and tavan >= hedef_fiyat * 0.1:
        md += [f"**Toptan alış tavanı: KDV dahil {tl(tavan)}** — {tl(hedef_fiyat)} satış fiyatında %{a['hedef_marj'] * 100:.0f} net kâr için "
               "bundan pahalıya alma.", ""]
    else:
        md += [f"**Dikkat:** {tl(hedef_fiyat) if hedef_fiyat else 'piyasa'} fiyatında alış en fazla {tl(tavan or 0)} olabilir, %{a['hedef_marj'] * 100:.0f} net çok zor "
               "(kargo + koli + reklam payı). Daha yüksek fiyat (paket/set) ya da daha ucuz kargo gerekir.", ""]
    if piyasa and hedef_fiyat and hedef_fiyat > piyasa * 1.15:
        md += [f"> ⚠ Planlanan fiyat ({tl(hedef_fiyat)}) Trendyol medyanının ({tl(piyasa)}) %{(hedef_fiyat / piyasa - 1) * 100:.0f} üstünde. "
               + (f"Piyasa fiyatından satacaksan alış en fazla {tl(tavan_piyasa)} olmalı." if tavan_piyasa
                  else "Piyasa fiyatında kargo + reklam sonrası kâr kalmıyor; fark yaratan paket/set ya da marka gerekir."), ""]
    md += ["## Toptancı kartı", ""]
    if kart:
        md += ["| Alan | Değer |", "|---|---|"] + [f"| {ad} | {kart[k]} |" for k, ad in KART if k in kart]
    else:
        md += ["Henüz toptancı girilmedi. Görüşünce panelde **Toptancı kartı**nı doldur ya da: "
               f"`python hat.py sec {p.ad} toptanci_ad=\"...\" toptanci_tel=\"...\" tedarik_fiyati=<KDV dahil TL> moq=<adet> fatura=var dropship=evet`"]
    md += ["", f"Şu an hesapta birim maliyet **{tl(m['toplam'])}** ({m.get('kaynak') or 'araştırmadaki fiyat'}).", "",
           "## Tedarikçiyi nerede bulursun", ""]
    for i, y in enumerate(yollar, 1):
        md += [f"{i}. **{y['ad']}** — {y['nasil']}", f"   - Ara: {y['link']}", f"   - Risk: {y['risk']}"]
    if saticilar:
        md += ["", "## Bu ürünü Trendyol'da satanlar (telefon: mesafeli satış sözleşmesi)", "", "| Ürün | Satıcı | Fiyat | Yorum |", "|---|---|---|---|"]
        md += [f"| [{(s['ad'] or '')[:50]}]({s['link']}) | {s.get('satici') or s.get('marka') or '–'} | {tl(s.get('fiyat'))} | {s.get('degerlendirme') or 0} |"
               for s in saticilar]
    md += ["", "## Telefon / WhatsApp metni (aramayı sen yaparsın)", "", "```", mesaj, "```", "",
           "## Toptancıya 15 soru", ""] + [f"{i}. {q}" for i, q in enumerate(SORULAR_TR, 1)]
    md += ["", "## Numune kontrol listesi", ""] + [f"- [ ] {k}" for k in kontrol]
    md += ["", "## Sahte toptancı kırmızı bayrakları", ""] + [f"- {k}" for k in KIRMIZI_BAYRAK]
    md += ["", "Ticaret sicil (ticaret odası) ve vergi numarasını resmi kaynaktan doğrula. Numune uygunsa adımı onayla; reklam adımı bu onay olmadan açılmaz."]
    if mesaj_en:
        md += ["", "## Ek: AliExpress satıcısına mesaj (İngilizce, ithalat düşünürsen)", "", "```", mesaj_en, "```"]
    p.yaz("tedarik", veri, md)
