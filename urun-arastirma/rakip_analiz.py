"""Rakip ve yorum analizi (kaynaklar/ozetler/arastirma.md → Rekabet analizi).

Yorumlardan tekrar eden şikâyet/beğenileri çıkarır, farklılaşma önerisi ve "neden benden alınır" cümlesi üretir.
Şikâyetler SADECE verilen yorumlardan çıkarılır; yorum yoksa liste boş kalır (uydurma yok).
"""
from __future__ import annotations

import gemini
import rakipler

SISTEM = (
    "Türkiye pazarında e-ticaret yapan birine ürün araştırmasında yardım eden analistsin. "
    "Sadece verilen yorumlara ve verilere dayan; yorumda olmayan şikâyet ya da beğeni uydurma. "
    "Sağlık/tedavi vaadi ve abartılı iddia önerme. Kısa, somut, Türkçe yaz. "
    "'Daha ucuza satmak' tek başına farklılaşma değildir. "
    "Başka markanın 'muadili/benzeri' olarak konumlandırma önerme (marka ihlali). "
    "SSS cevaplarında satıcı verisinde olmayan bir bilgiyi (ambalaj, malzeme, sertifika, cilt güvenliği vb.) "
    "kesinmiş gibi yazma; bilinmeyen kısmı [satıcıdan doğrula] diye işaretle. "
    "Şikâyet listesine öncelikle en az 2 yorumda geçenleri al."
)

SEMA = {
    "type": "OBJECT",
    "properties": {
        "sikayetler": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "konu": {"type": "STRING"}, "yorum_sayisi": {"type": "INTEGER"},
            "ornek": {"type": "STRING"}, "firsat": {"type": "STRING"}},
            "required": ["konu", "yorum_sayisi", "ornek", "firsat"]}},
        "begeniler": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "konu": {"type": "STRING"}, "yorum_sayisi": {"type": "INTEGER"}, "ornek": {"type": "STRING"}},
            "required": ["konu", "yorum_sayisi", "ornek"]}},
        "farklilasma": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "boyut": {"type": "STRING", "enum": ["urun", "teklif", "icerik", "deneyim", "problem_cozumu"]},
            "oneri": {"type": "STRING"}}, "required": ["boyut", "oneri"]}},
        "neden_benden": {"type": "STRING"},
        "sss": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "soru": {"type": "STRING"}, "cevap_taslagi": {"type": "STRING"}}, "required": ["soru", "cevap_taslagi"]}},
        "ayrisma_puani": {"type": "INTEGER", "description": "0: ayrışmak zor, 1: kısmen, 2: net ayrışma fırsatı var"},
        "ayrisma_gerekce": {"type": "STRING"},
        "benzer_rakipler": {"type": "ARRAY", "items": {"type": "INTEGER"},
                            "description": "Numaralı Trendyol listesinden bizim ürünle AYNI tür ve işlevdeki ürünlerin numaraları"},
    },
    "required": ["sikayetler", "begeniler", "farklilasma", "neden_benden", "sss", "ayrisma_puani", "ayrisma_gerekce",
                 "benzer_rakipler"],
}


def rakip_tablosu(rk: dict | None, adet: int = 10) -> list[dict]:
    if not rk or rk.get("hata"):
        return []
    ur = sorted(rk.get("urunler") or [], key=lambda x: -int(x.get("degerlendirme") or 0))
    return [{k: u.get(k) for k in ("ad", "marka", "fiyat", "eski_fiyat", "puan", "degerlendirme", "favori",
                                   "satici", "ucretsiz_kargo", "link")} for u in ur[:adet]]


def _yorumlar(u: dict, rk: dict | None) -> list[str]:
    out = []
    for r in (u.get("yorumlar") or {}).get("liste") or []:
        if r.get("metin"):
            out.append(f"[AliExpress {r.get('yildiz')}★] {r['metin'].strip()[:300]}")
    for r in (rk or {}).get("yorumlar") or []:
        if r.get("metin"):
            out.append(f"[Trendyol rakip {r.get('puan')}★] {r['metin'].strip()[:300]}")
    return out


def analiz(u: dict, rk: dict | None) -> dict:
    tablo = rakip_tablosu(rk)
    yorumlar = _yorumlar(u, rk)
    sonuc = {"rakip_tablosu": tablo, "yorum_sayisi": len(yorumlar)}
    if not gemini.var_mi():
        return {**sonuc, "hata": "GEMINI_API_KEY yok; yorum analizi yapılmadı"}
    oz = u.get("ozellikler") or {}
    satirlar = [
        f"Ürün: {u.get('baslik')}",
        "Satıcı özellikleri: " + "; ".join(f"{k}: {v}" for k, v in list(oz.items())[:25]),
        "Açıklama: " + " ".join((u.get("aciklama") or {}).get("metin") or [])[:1500],
        "",
        "Türkiye'deki rakipler (Trendyol, en çok değerlendirilen):",
    ]
    satirlar += [f"- {t['ad']} | {t['fiyat']} TL | {t['puan']}★ | {t['degerlendirme']} değerlendirme | "
                 f"ücretsiz kargo: {t['ucretsiz_kargo']}" for t in tablo] or ["- (rakip verisi yok)"]
    liste = rakipler.numarali_liste(rk) if rk and not rk.get("hata") else []
    if liste:
        satirlar += ["", "Numaralı Trendyol arama sonuçları (benzer rakip seçimi için):"]
        satirlar += [f"{i}. {x.get('ad')} | {x.get('fiyat')} TL" for i, x in enumerate(liste, 1)]
    satirlar += ["", f"Yorumlar ({len(yorumlar)} adet):"] + (yorumlar[:120] or ["(yorum yok)"])
    satirlar += ["", "Görev: tekrar eden en fazla 3 şikâyet (her biri için ürünü satarken nasıl fırsata çevrileceği), "
                 "en fazla 3 beğeni, 5 boyutta farklılaşma önerisi (ürün, teklif, içerik, deneyim, problem çözümü; "
                 "her boyuttan en fazla 1), tek cümlelik 'neden benden alınır', yorumlardaki itirazlardan 4–6 SSS, "
                 "ve rakiplerden ayrışabilme puanı (0/1/2) gerekçesiyle. Yorum yoksa şikâyet/beğeni listesi boş olsun. "
                 "benzer_rakipler: numaralı Trendyol listesinden bizim ürünle AYNI ürün türü ve işlevde olanların numaraları "
                 "(ör. çok işlevli bakım fırçası ile yapışkan tüy rulosu yedeği aynı ürün DEĞİLDİR; set/paket olsa da ana ürün aynıysa dahil). "
                 "Aynısı yoksa boş liste."]
    try:
        g = gemini.json_sor("\n".join(satirlar), SEMA, sistem=SISTEM)
    except Exception as e:
        return {**sonuc, "hata": f"Gemini: {e}"}
    g["ayrisma_puani"] = max(0, min(2, int(g.get("ayrisma_puani") or 0)))
    g["benzer_rakipler"] = [int(i) for i in g.get("benzer_rakipler") or [] if 1 <= int(i) <= len(liste)]
    return {**sonuc, **g, "model": gemini.son_model() or gemini.model()}
