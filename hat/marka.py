"""3 · Marka: isim önerileri, .com müsaitliği (RDAP), konumlandırma, ton, 2 ana renk, font, logo brifi.

İsim seçimi insan onayıdır: python hat.py onayla <proje> marka --secim isim=<Isim>
Marka tescili (TÜRKPATENT), .com.tr ve Instagram kullanıcı adı elle kontrol edilir.
"""
from __future__ import annotations

import requests

from ortak import Proje, metin_json, ozet, slug

SEMA = {
    "type": "OBJECT",
    "properties": {
        "isimler": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "isim": {"type": "STRING"}, "anlam": {"type": "STRING"}, "neden": {"type": "STRING"}},
            "required": ["isim", "anlam", "neden"]}},
        "kimlik": {"type": "OBJECT", "properties": {
            "konumlandirma": {"type": "STRING"},
            "hedef_kitle": {"type": "STRING"},
            "ton": {"type": "STRING"},
            "sloganlar": {"type": "ARRAY", "items": {"type": "STRING"}},
            "ana_renk": {"type": "STRING", "description": "#RRGGBB"},
            "ikinci_renk": {"type": "STRING", "description": "#RRGGBB"},
            "notr_renk": {"type": "STRING", "description": "#RRGGBB, açık zemin"},
            "baslik_fontu": {"type": "STRING", "description": "Google Fonts adı, Türkçe karakter destekli"},
            "metin_fontu": {"type": "STRING", "description": "Google Fonts adı, Türkçe karakter destekli"},
            "logo_brifi": {"type": "STRING"},
            "gorsel_dil": {"type": "STRING", "description": "fotoğraf stili, ışık, zemin, sahne önerisi"},
        }, "required": ["konumlandirma", "hedef_kitle", "ton", "sloganlar", "ana_renk", "ikinci_renk", "notr_renk",
                        "baslik_fontu", "metin_fontu", "logo_brifi", "gorsel_dil"]},
    },
    "required": ["isimler", "kimlik"],
}


def _rdap(alan: str) -> int | None:
    try:
        return requests.get(f"https://rdap.verisign.com/com/v1/domain/{alan}", timeout=15).status_code
    except requests.RequestException:
        return None


def com_durumu(isim: str) -> str:
    """Verisign RDAP: 404 → büyük olasılıkla boş, 200 → alınmış. Alınmışsa yaygın varyantları dener."""
    k = slug(isim).replace("-", "")
    for alan in (f"{k}.com", f"{k}tr.com", f"{k}home.com", f"get{k}.com", f"{k}store.com"):
        kod = _rdap(alan)
        if kod == 404:
            return f"{alan} boş görünüyor"
        if kod != 200:
            return f"{alan} kontrol edilemedi"
    return f"{k}.com ve 4 varyantı alınmış"


def calistir(p: Proje, args=None):
    istem = "\n".join([
        p.urun_ozeti(),
        "",
        "Bu ürünle Türkiye'de Instagram + kendi sitesi üzerinden satış yapacak tek ürünlü (ileride aynı kategoride genişleyebilecek) "
        "bir D2C marka kuruyoruz. Görev:",
        "1) 8 marka adı: kısa (≤ 10 harf), Türkçe telaffuzu kolay, akılda kalıcı, ürün kategorisini sınırlamayan, "
        "Türkçe olmayan harf (q, w, x) gerektirmeyen, bilinen bir marka adına benzemeyen. Her biri için anlamı ve neden uygun olduğu.",
        "2) Marka kimliği: konumlandırma cümlesi, hedef kitle (yaş, yaşam tarzı, problem), konuşma tonu, 3 kısa slogan, "
        "2 ana renk + 1 nötr zemin rengi (hex), Türkçe karakter destekli Google Fonts başlık ve metin fontu, "
        "logo brifi (sade wordmark, tek renkte de çalışmalı) ve ürün fotoğrafları için görsel dil.",
        "",
        "Bilgi bankası (Instagram profil kuralları):", ozet("instagram")[:1500],
    ])
    g = metin_json(istem, SEMA, sicaklik=0.9)
    for x in g["isimler"]:
        x["com"] = com_durumu(x["isim"])
        x["instagram"] = f"https://www.instagram.com/{slug(x['isim']).replace('-', '')}/"
    k = g["kimlik"]
    md = ["# Marka", "", "## İsim adayları", "",
          "| İsim | .com | Anlam | Neden |", "|---|---|---|---|"]
    md += [f"| **{x['isim']}** | {x['com']} | {x['anlam']} | {x['neden']} |" for x in g["isimler"]]
    md += ["", "Seçmeden önce **elle** kontrol et:",
           "- Marka tescili / benzer marka: https://www.turkpatent.gov.tr (Marka Araştırma) — sınıf 3, 21, 35 vb. ürününe göre",
           "- .com.tr: https://www.trabis.gov.tr · Instagram kullanıcı adı (tablodaki link 404 vermeli)",
           "- Trendyol/Google'da aynı isimle satış yapan var mı", "",
           "Seçim: `python hat.py onayla <proje> marka --secim isim=<Isim>`", "",
           "## Kimlik", "",
           f"- **Konumlandırma:** {k['konumlandirma']}", f"- **Hedef kitle:** {k['hedef_kitle']}", f"- **Ton:** {k['ton']}",
           "- **Sloganlar:** " + " · ".join(k["sloganlar"]),
           f"- **Renkler:** ana {k['ana_renk']} · ikinci {k['ikinci_renk']} · nötr {k['notr_renk']}",
           f"- **Fontlar:** başlık {k['baslik_fontu']} · metin {k['metin_fontu']}",
           f"- **Logo brifi:** {k['logo_brifi']}", f"- **Görsel dil:** {k['gorsel_dil']}"]
    p.yaz("marka", g, md)
