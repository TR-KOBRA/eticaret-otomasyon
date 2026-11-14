"""Ürün risk taraması: marka/kopya, sağlık iddiası, satıcının vermediği bilgiler, kargo ve yorum zayıflığı.

Kesin hüküm değildir; elle kontrol edilecek noktaları işaretler.
"""
from __future__ import annotations

import re

MARKALAR = [
    "tom ford", "hermes", "hermès", "chanel", "dior", "gucci", "nina ricci", "burberry", "burberr", "armani",
    "giorgio", "versace", "jo malone", "bvlgari", "bulgari", "ysl", "yves saint", "lancome", "paco rabanne",
    "creed", "byredo", "le labo", "zara", "apple", "airpods", "iphone", "samsung", "dyson", "nike", "adidas",
    "disney", "marvel", "pokemon", "lego", "tesla", "louis vuitton", "lv ", "prada", "rolex", "cartier",
    "jean paul", "hugo boss", "calvin klein", "victoria", "crowne plaza", "intercontinental", "hilton", "ritz",
]
KOPYA = ["replica", "replika", "dupe", "inspired by", "esintili", "muadil", "1:1", "aaa kalite", "birebir"]
SAGLIK = [
    "stres", "kaygı", "anksiyete", "uyku", "bağışıklık", "tedavi", "iyileştir", "ağrı", "migren", "depresyon",
    "beyin aktivite", "zayıfla", "kilo ver", "selülit", "virüs", "bakteri", "mikrop", "%99", "antibakteriyel",
    "detoks", "kan şekeri", "tansiyon", "sağlıklı",
]
YASAKLI_KATEGORI = ["takviye", "supplement", "ilaç", "lens", "bebek maması", "lityum pil", "lazer pointer",
                    "elektronik sigara", "vape", "bıçak", "silah"]


KIRILGAN = ["cam", "glass", "seramik", "ceramic", "porselen", "porcelain", "kristal", "crystal", "ayna", "mirror"]
SIVI = ["sıvı", "liquid", "yağ", " oil", "esans", "essential", "parfüm", "perfume", "ml", "jel", "gel", "losyon", "sprey", "spray"]
PIL = ["lityum", "lithium", "li-ion", "battery", "pil ", "batarya", "şarj edilebilir", "rechargeable"]


def desi_tahmini(u: dict) -> dict:
    """Özelliklerden ağırlık (kg) ve paket ölçüsü (cm) bulmaya çalışır. Desi = en×boy×yük / 3000."""
    ag, olcu = None, None
    for k, v in (u.get("ozellikler") or {}).items():
        kv = f"{k} {v}".lower().replace(",", ".")
        if ag is None and any(t in kv for t in ("ağırlık", "weight", "kg")):
            m = re.search(r"(\d+(?:\.\d+)?)\s*(kg|gr|g)\b", kv)
            if m:
                ag = float(m.group(1)) / (1000 if m.group(2) in ("g", "gr") else 1)
        if olcu is None:
            m = re.search(r"(\d+(?:\.\d+)?)\s*[x×*]\s*(\d+(?:\.\d+)?)\s*[x×*]\s*(\d+(?:\.\d+)?)\s*(cm|mm)?", kv)
            if m:
                bol = 10 if m.group(4) == "mm" else 1
                olcu = [float(m.group(i)) / bol for i in (1, 2, 3)]
    desi = round(olcu[0] * olcu[1] * olcu[2] / 3000, 1) if olcu else None
    return {"agirlik_kg": ag, "olcu_cm": olcu, "desi": desi,
            "faturalanan": max(x for x in (ag, desi) if x is not None) if (ag or desi) else None}


def _kelime(metin: str, liste: list[str]) -> list[str]:
    """Kelime başı eşleşmesi ('ayna' 'kaynağı' içinde yakalanmasın)."""
    return sorted({k.strip() for k in liste if re.search(r"(?<![a-zçğıöşü])" + re.escape(k.strip()), metin)})


def kargo_riski(u: dict) -> dict:
    """{seviye: dusuk|orta|yuksek, nedenler: [...], desi: {...}}"""
    metin = " ".join([u.get("baslik") or ""] + [f"{k} {v}" for k, v in (u.get("ozellikler") or {}).items()]).lower()
    nedenler = []
    kr = _kelime(metin, KIRILGAN)
    sv = _kelime(metin, SIVI)
    pl = _kelime(metin, PIL)
    if kr:
        nedenler.append(f"kırılgan malzeme ({', '.join(kr)})")
    if sv:
        nedenler.append(f"sıvı/sızma riski ({', '.join(sv[:4])})")
    if pl:
        nedenler.append(f"pil/batarya: hava kargoda kısıt ({', '.join(pl)})")
    d = desi_tahmini(u)
    if d["faturalanan"] and d["faturalanan"] > 5:
        nedenler.append(f"yüksek desi/ağırlık (~{d['faturalanan']})")
    seviye = "dusuk" if not nedenler else ("yuksek" if len(nedenler) >= 2 or (d["faturalanan"] or 0) > 10 else "orta")
    return {"seviye": seviye, "nedenler": nedenler, "desi": d}


def _bul(metin: str, liste: list[str]) -> list[str]:
    m = metin.lower()
    return sorted({k.strip() for k in liste if k in m})


def tara(u: dict) -> list[dict]:
    """[{seviye: yuksek|orta|bilgi, konu, detay}]"""
    metin = " ".join([
        u.get("baslik") or "",
        " ".join(u.get("aciklama", {}).get("metin") or []),
        " ".join(f"{k} {v}" for k, v in (u.get("ozellikler") or {}).items()),
        " ".join(v.get("ad") or "" for v in u.get("varyantlar") or []),
    ])
    r = []
    mk = _bul(metin, MARKALAR)
    if mk:
        r.append({"seviye": "yuksek", "konu": "Başka markaların adı geçiyor",
                  "detay": f"{', '.join(mk)}. Kopya/taklit ürün ya da marka ihlali riski; bu varyantları satma, adlarını hiçbir yerde kullanma."})
    kp = _bul(metin, KOPYA)
    if kp:
        r.append({"seviye": "yuksek", "konu": "Kopya ürün ifadesi", "detay": ", ".join(kp)})
    sg = _bul(metin, SAGLIK)
    if sg:
        r.append({"seviye": "orta", "konu": "Satıcı sağlık/etki iddiası kullanıyor",
                  "detay": f"{', '.join(sg)}. Bu iddiaları sitede ve reklamda kullanma (Ticari Reklam Yönetmeliği, Meta politikaları)."})
    yk = _bul(metin, YASAKLI_KATEGORI)
    if yk:
        r.append({"seviye": "orta", "konu": "Düzenlemeye tabi olabilecek kategori", "detay": ", ".join(yk)})
    oz = {k.lower(): str(v).lower() for k, v in (u.get("ozellikler") or {}).items()}
    if any("110v" in v for v in oz.values()):
        r.append({"seviye": "orta", "konu": "Gerilim 110V yazıyor",
                  "detay": "Türkiye 220V. Elektrikli ürünse uyumluluğu ve CE belgesini satıcıdan teyit et."})
    kr = kargo_riski(u)
    if kr["nedenler"]:
        r.append({"seviye": "orta" if kr["seviye"] != "dusuk" else "bilgi", "konu": "Kargolama riski",
                  "detay": "; ".join(kr["nedenler"]) + ". Paketleme ve kırılma/sızma iadesini maliyete kat."})
    kargo = u.get("kargo") or []
    if kargo:
        en_hizli = min((k.get("gun_max") or 999) for k in kargo)
        if en_hizli > 30:
            r.append({"seviye": "orta", "konu": f"Türkiye'ye en hızlı teslim {en_hizli} gün",
                      "detay": "Doğrudan gönderimle satış yapılamaz; Türkiye'de stok tutmak gerekir."})
        if not any(k.get("takip") for k in kargo):
            r.append({"seviye": "bilgi", "konu": "Takipli kargo seçeneği yok", "detay": "Numune siparişinde kaybolma riski."})
    else:
        r.append({"seviye": "yuksek", "konu": "Türkiye'ye kargo seçeneği yok", "detay": ""})
    oz_y = (u.get("yorumlar") or {}).get("ozet") or {}
    toplam = oz_y.get("toplam") or 0
    if toplam < 20:
        r.append({"seviye": "bilgi", "konu": f"Az yorum ({toplam})",
                  "detay": "Ürün kalitesi kanıtlanmamış; numune sipariş et, zayıf noktaları kategori bilgisinden çıkar."})
    yz = oz_y.get("yildiz") or {}
    dusuk = sum((yz.get(i) or 0) for i in (1, 2, 3))
    if toplam and dusuk / toplam > 0.15:
        r.append({"seviye": "orta", "konu": f"Düşük puan oranı %{dusuk / toplam * 100:.0f}",
                  "detay": "Düşük puanlı yorumları oku; tekrar eden şikâyet varsa üründen vazgeç."})
    try:
        oran = float((u.get("magaza") or {}).get("olumlu_oran") or 100)
        if oran < 92:
            r.append({"seviye": "orta", "konu": f"Mağaza olumlu oranı %{oran}", "detay": "Alternatif tedarikçi ara."})
    except ValueError:
        pass
    return r
