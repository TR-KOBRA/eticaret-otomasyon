"""2 · Tedarik: satıcı değerlendirmesi, 15 soruluk mesaj taslağı, numune kontrol listesi (kaynaklar/ozetler/tedarik.md).

Mesaj gönderilmez; sadece taslak üretilir. Numune siparişi insan onayıdır.
"""
from __future__ import annotations

import re
import urllib.parse

from ortak import Proje, tl

SORULAR_EN = [
    "Are you the manufacturer of this product or a reseller?",
    "What is your minimum order quantity (MOQ) and your price for 10 / 50 / 100 units?",
    "Can you ship to Turkey with a tracked method? Which carrier, how many days, and what is the cost?",
    "Can I order 1–2 samples first? What is the sample price and shipping time?",
    "What are the exact product dimensions, net weight and packed weight (with box)?",
    "What is the material / ingredient list? Can you share certificates (CE, MSDS, test reports) for this exact item?",
    "How is the product packed? Is it protected against breakage or leakage during shipping?",
    "What happens if items arrive damaged or defective? Do you replace or refund?",
    "How many units do you usually have in stock, and how fast can you restock?",
    "Will you notify me before stock runs out or before a price change? How far in advance?",
    "Can you ship without invoices/flyers showing prices or your store name (neutral packaging)?",
    "Can you add my logo/label or custom packaging? From what quantity and at what cost?",
    "May I use your product photos and videos on my own store and ads?",
    "Is this design exclusive to you? Are there any brand or patent restrictions?",
    "Which payment methods do you accept for larger orders, and can we agree terms in writing?",
]
SORULAR_TR = [
    "Ticari unvanınız ve vergi numaranız nedir?", "Ürünü kendiniz mi üretiyorsunuz?", "Minimum sipariş adedi (MOQ) nedir?",
    "Fiyatlar KDV dahil mi?", "Kargo ücreti ve teslim süresi nedir?", "Hangi ödeme yöntemlerini kabul ediyorsunuz?",
    "Vadeli çalışma imkânı var mı?", "Numune gönderiyor musunuz, ücreti nedir?",
    "Hasarlı/hatalı ürünlerde iade ve değişim nasıl işliyor?", "Stok durumunu nasıl bildiriyorsunuz?",
    "Fiyat değişikliklerini ne kadar önce bildiriyorsunuz?", "Yeni ürün eklediğinizde nasıl haber veriyorsunuz?",
    "Ürün görsellerini ve açıklamalarını kullanmamıza izin var mı?", "Münhasırlık veya bölge kısıtı var mı?",
    "Yazılı sözleşme ile çalışıyor musunuz?",
]
KIRMIZI_BAYRAK = [
    "Sadece ön ödemeli havale veya kripto istiyor", "Fiyat piyasanın çok altında", "Yeni domain, kurumsal bilgi yok",
    "Fotoğraflar başka sitelerde de aynı", "Yeni/az takipçili sosyal hesap", "Tek iletişim kanalı",
    "Sicil veya vergi numarası vermekten kaçınıyor",
]


def calistir(p: Proje, args=None):
    u = p.urun
    m = u.get("magaza") or {}
    kargo = sorted(u.get("kargo") or [], key=lambda k: (k.get("gun_max") or 999))
    an = p.veri.get("rakip_analizi") or {}
    kr = p.veri.get("kargo_riski") or {}

    kontrol = [
        "Ürün, ilandaki fotoğraflarla aynı mı (renk, boyut, malzeme)?",
        "Paket ölçüsü ve ağırlığı (desi) — gerçek kargo ücretini buna göre güncelle (hesap.py yurtici_kargo_tl).",
        "Kutudan çıkış videosu çek (Instagram 'Nasıl Kullanılır' öne çıkanı ve reklam UGC'si için kullanılacak).",
        "Kullanım süresi/dayanıklılık: 3–7 gün gerçek kullanım.",
    ]
    kontrol += [f"Rakip şikâyeti kontrolü: {x['konu']} — numunede de var mı?" for x in an.get("sikayetler") or []]
    kontrol += [f"Kargo riski: {n} — paketleme yeterli mi?" for n in kr.get("nedenler") or []]
    kontrol += [f"Satıcı verisini doğrula: {r['konu']}" for r in p.veri.get("riskler") or [] if r["seviye"] != "bilgi"]

    # Diğer satıcıları bulmak için: araştırmadaki Türkçe pazar kelimesi, yoksa başlığın ilk anlamlı kelimeleri
    kelime = next(iter(((p.veri.get("trendler") or {}).get("kelimeler") or {}).keys()), None)
    arama = kelime or " ".join(re.sub(r"[^\w\s-]", " ", u.get("baslik", "").split(":")[0]).split()[:5])
    alternatif = f"https://tr.aliexpress.com/w/wholesale-{urllib.parse.quote(arama)}.html?sortType=total_tranpro_desc"
    mesaj_en = ("Hello, I am planning to sell this product in Turkey and may place regular orders if the sample quality is good.\n"
                f"Product: {u.get('link')}\n\nCould you please answer:\n"
                + "\n".join(f"{i}. {q}" for i, q in enumerate(SORULAR_EN, 1)) + "\n\nThank you!")

    veri = {"satici": m, "kargo": kargo, "sorular_en": SORULAR_EN, "sorular_tr": SORULAR_TR, "mesaj_en": mesaj_en,
            "numune_kontrol": kontrol, "alternatif_arama": alternatif, "kirmizi_bayraklar": KIRMIZI_BAYRAK}
    md = [f"# Tedarik — {u.get('baslik', '')[:80]}", "",
          f"**Mevcut satıcı:** {m.get('ad')} · olumlu %{m.get('olumlu_oran')} · {m.get('toplam')} değerlendirme", "",
          "| Kargo | Ücret | Gün | Takip |", "|---|---|---|---|"]
    md += [f"| {k.get('firma')} | {'ücretsiz' if k.get('ucretsiz') else tl(k.get('ucret_tl'))} | {k.get('gun_min')}–{k.get('gun_max')} | "
           f"{'var' if k.get('takip') else 'yok'} |" for k in kargo[:6]]
    md += ["", "## Yapılacaklar", "",
           "1. Aynı ürünü satan **en az 2 satıcı daha** bul ve karşılaştır (fiyat, teslim, mağaza puanı, yorum):",
           f"   - AliExpress araması: {alternatif}",
           f"   - ya da: `python arastir.py kesfet \"<ingilizce kelime>\" --icermeli \"...\"` ve adayları `urun` ile incele",
           "2. Her satıcıya aşağıdaki mesajı gönder (AliExpress mesajlaşma). **Gönderimi sen yaparsın.**",
           "3. En iyi 1–2 satıcıdan **numune** sipariş et ve kontrol listesini doldur.",
           "4. Satıcı **toptan fiyat** verince sisteme gir (adet başı ürün TL; varsa adet başı uluslararası kargo):",
           f"   `python hat.py sec {p.ad} tedarik_fiyati=<KDV dahil TL>` (yerli toptancı; ithalatta ayrıca tedarik_kargo=<TL>) ya da panelde Proje → Ayarlar. "
           "Fiyat, kâr ve reklam eşikleri bu maliyetle yeniden hesaplanır.",
           f"   Şu an hesapta: tek adet AliExpress fiyatı **{tl((p.veri.get('maliyet') or {}).get('stok', {}).get('kalemler', {}).get('urun'))}** "
           f"→ birim maliyet **{tl(p.maliyet()['toplam'])}**" + (" (toptan fiyat girildi)" if p.secim('tedarik_fiyati') else " (toptan fiyat henüz yok)") + ".",
           "5. Numune uygunsa onayla (panel ya da `python hat.py onayla <proje> tedarik`) — reklam adımı bu onay olmadan açılmaz.", "",
           "## Satıcıya mesaj (İngilizce)", "", "```", mesaj_en, "```", "",
           "## Yerli toptancı için 15 soru", ""] + [f"{i}. {q}" for i, q in enumerate(SORULAR_TR, 1)]
    md += ["", "## Numune kontrol listesi", ""] + [f"- [ ] {k}" for k in kontrol]
    md += ["", "## Sahte toptancı kırmızı bayrakları", ""] + [f"- {k}" for k in KIRMIZI_BAYRAK]
    md += ["", "Yerli toptancıda ticaret sicil (ticaret odası) ve vergi numarasını resmi kaynaktan doğrula."]
    p.yaz("tedarik", veri, md)
