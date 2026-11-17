"""7 · Instagram: profil (isim alanı, 3 satır bio), 4 öne çıkan + kapakları, 24 içeriklik plan (%50 reels / %30 carousel / %20 görsel).

Paylaşım yapılmaz; içerik paketi üretilir. Satın alınmış takipçi/beğeni önerilmez (kaynaklar/ozetler/instagram.md).
"""
from __future__ import annotations

import csv

from PIL import Image, ImageDraw

from gorsel import _font
from ortak import Proje, metin_json, ozet

ICERIK = {"type": "OBJECT", "properties": {
    "tur": {"type": "STRING", "enum": ["reels", "carousel", "gorsel"]},
    "baslik": {"type": "STRING"},
    "kanca": {"type": "STRING", "description": "ilk 3 saniye / kapak cümlesi"},
    "akis": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "reels: sahne sahne; carousel: slayt slayt; görsel: tek açıklama"},
    "cta": {"type": "STRING"},
    "caption": {"type": "STRING"},
    "hashtagler": {"type": "ARRAY", "items": {"type": "STRING"}},
    "gorsel_kaynagi": {"type": "STRING", "description": "hangi çekim/görsel gerekiyor: numune çekimi, AI görsel, müşteri UGC"},
}, "required": ["tur", "baslik", "kanca", "akis", "cta", "caption", "hashtagler", "gorsel_kaynagi"]}

SEMA = {"type": "OBJECT", "properties": {
    "kullanici_adi_onerileri": {"type": "ARRAY", "items": {"type": "STRING"}},
    "isim_alani": {"type": "STRING"},
    "bio": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "tam 3 satır"},
    "one_cikanlar": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
        "ad": {"type": "STRING"}, "icerikler": {"type": "ARRAY", "items": {"type": "STRING"}}}, "required": ["ad", "icerikler"]}},
    "icerikler": {"type": "ARRAY", "items": ICERIK},
}, "required": ["kullanici_adi_onerileri", "isim_alani", "bio", "one_cikanlar", "icerikler"]}


def kapak(metin: str, renk: str, zemin: str, hedef):
    img = Image.new("RGB", (1080, 1920), zemin or "#FFFFFF")
    d = ImageDraw.Draw(img)
    d.ellipse((240, 660, 840, 1260), fill=renk or "#222222")
    # Tam başlık (ör. "Sizden Gelenler"): daire içine sığana kadar küçült, gerekirse iki satıra böl
    satirlar = [metin]
    for boyut in (84, 76, 68, 60, 54):
        f = _font(boyut)
        genis = lambda t: d.textbbox((0, 0), t, font=f)[2] - d.textbbox((0, 0), t, font=f)[0]
        if genis(metin) <= 500:
            satirlar = [metin]
            break
        k = metin.split()
        if len(k) > 1:
            orta = max(range(1, len(k)), key=lambda i: -abs(len(" ".join(k[:i])) - len(" ".join(k[i:]))))
            iki = [" ".join(k[:orta]), " ".join(k[orta:])]
            if max(genis(t) for t in iki) <= 470:
                satirlar = iki
                break
    yuk = boyut * 1.15
    for i, t in enumerate(satirlar):
        x0, y0, x1, y1 = d.textbbox((0, 0), t, font=f)
        y = 960 - yuk * len(satirlar) / 2 + i * yuk + (yuk - (y1 - y0)) / 2 - y0
        d.text((540 - (x1 - x0) / 2 - x0, y), t, font=f, fill=zemin or "#FFFFFF")
    img.save(hedef)


def calistir(p: Proje, args=None):
    m = p.marka()
    ic = p.oku("icerik") or {}
    istem = "\n".join([
        p.urun_ozeti(),
        f"Marka: {m['isim']} · ton: {m.get('ton')} · hedef kitle: {m.get('hedef_kitle')} · sloganlar: {m.get('sloganlar')}",
        f"Ürün adı (mağaza): {ic.get('urun_adi', '')}",
        "", "Bilgi bankası:", ozet("instagram")[:3000], "",
        "Görev: 3 kullanıcı adı önerisi (nokta/alt çizgi karmaşası yok), isim alanı ('Marka | Resmi Mağaza' formatı), "
        "3 satır bio (fayda · güven · CTA; güven satırında doğrulanamayan '%100 memnuniyet' gibi iddia kullanma, "
        "kargo/iade/destek gibi gerçek taahhütleri yaz), 4 öne çıkan (Sizden Gelenler, Kargo & Teslimat, SSS, Nasıl Kullanılır) "
        "ve her biri için 3 hikâye fikri, ve reklamdan önce paylaşılacak TAM 24 içerik: 12 reels, 7 carousel, 5 tekil görsel. "
        "'Sizden Gelenler' ve yorum içerikleri için yalnızca gerçek müşteri geri bildirimi toplanınca paylaşılacağını belirt. "
        "Her içerik için Türkçe caption ve 5 niş hashtag.",
    ])
    g = metin_json(istem, SEMA, sicaklik=0.8)
    kl = p.yol / "instagram"
    kl.mkdir(exist_ok=True)
    for i, o in enumerate(g["one_cikanlar"][:4], 1):
        kapak(o["ad"][:24], m.get("ana_renk"), m.get("notr_renk"), kl / f"one-cikan-{i}.png")
    with open(kl / "icerik-takvimi.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["sira", "tur", "baslik", "kanca", "akis", "cta", "caption", "hashtagler", "gorsel_kaynagi", "durum"])
        for i, x in enumerate(g["icerikler"], 1):
            w.writerow([i, x["tur"], x["baslik"], x["kanca"], " | ".join(x["akis"]), x["cta"], x["caption"],
                        " ".join(x["hashtagler"]), x["gorsel_kaynagi"], "taslak"])
    say = {t: sum(1 for x in g["icerikler"] if x["tur"] == t) for t in ("reels", "carousel", "gorsel")}
    md = [f"# Instagram — {m['isim']}", "", "## Profil", "",
          "- **Kullanıcı adı önerileri:** " + ", ".join(g["kullanici_adi_onerileri"]),
          f"- **İsim alanı:** {g['isim_alani']}", "- **Bio:**", "", "```"] + g["bio"] + ["```", "",
          "- **Profil fotoğrafı:** `gorseller/00-logo-yazi.png` (beyaz/nötr zemin, yüksek kontrast)",
          "- **Link:** mağaza domaini · **İletişim:** WhatsApp destek hattı", "",
          "## Öne çıkanlar (kapaklar `instagram/`)", ""]
    md += [f"{i}. **{o['ad']}** — " + "; ".join(o["icerikler"]) for i, o in enumerate(g["one_cikanlar"], 1)]
    md += ["", f"## İçerik planı ({len(g['icerikler'])} içerik · reels {say['reels']} · carousel {say['carousel']} · görsel {say['gorsel']})", "",
           "Tam liste ve captionlar: `instagram/icerik-takvimi.csv` (Excel'de açılır). Reklama çıkmadan önce en az 20 içerik paylaşılmış olmalı.", ""]
    for i, x in enumerate(g["icerikler"], 1):
        md += [f"### {i}. [{x['tur']}] {x['baslik']}", f"**Kanca:** {x['kanca']}  ", "**Akış:** " + " → ".join(x["akis"]) + "  ",
               f"**CTA:** {x['cta']}  ", f"**Gerekli çekim:** {x['gorsel_kaynagi']}", "", f"> {x['caption']}", "",
               " ".join(x["hashtagler"]), ""]
    md += ["## Uygulanmayacak", "", "Satın alınmış takipçi/beğeni (Modül 3 önerisi): hesap ve reklam hesabı riski. "
           "Yerine gerçek müşteri UGC'si, paketleme videoları ve teslimat sonrası yorum isteme mesajı (operasyon adımı)."]
    p.yaz("instagram", g, md)
