"""Birim maliyet, fiyat seçenekleri, başa baş ROAS / CPA.

Varsayımların hepsi AYARLAR içinde; gümrük ve komisyon oranları değişebildiği için
kullanmadan önce güncel değerleri kontrol et ve gerekirse .env ya da CLI ile değiştir.
"""
from __future__ import annotations

import math

AYARLAR_SON_KONTROL = "2026-11-14"   # oranlar değişir; bu tarihten sonra güncelliğini kontrol et

AYARLAR = {
    "kdv": 0.20,                 # satış KDV'si
    "odeme_komisyonu": 0.035,    # sanal POS / iyzico (taksit farkı hariç, ortalama)
    "pazaryeri_komisyonu": 0.0,  # kanal = trendyol ise KANALLAR'dan gelir
    "reklam_payi": 0.20,         # satışın %'si (dokümanlardaki referans dağılım: %15–25)
    "hedef_marj": 0.20,          # net (reklam + iade sonrası) hedef marj, en az %20
    # İade: oran ≠ maliyet. Beklenen iade maliyeti = oran × (gidiş + dönüş kargo + paketleme + kayıp × ürün)
    "iade_orani": 0.15,          # e-ticarette %15–30; beden/renk/uyum ürünlerinde 0,25 kullan
    "iade_donus_kargo_tl": 90.0,
    "iade_kayip_orani": 0.25,    # iade gelen ürünün satılamayan/hasarlı kısmı (ürün maliyetinin %'si)
    "paketleme_tl": 25.0,
    "yurtici_kargo_tl": 90.0,    # anlaşmalı kargo, desi 1-2 ortalama
    # Türkiye'de stok tutma senaryosu: toplu ithalatta gümrük + KDV + aracı için kaba tahmin
    "stok_ithalat_orani": 0.45,  # ürün+kargo bedelinin %'si
    "stok_navlun_tl": 60.0,      # toplu gönderimde adet başı navlun tahmini
    # Doğrudan AliExpress gönderimi (müşteri adına posta/hızlı kargo): vergi oranı
    "dogrudan_vergi_orani": 0.30,
}


# Kanal farkları. Trendyol komisyonu kategoriye göre değişir (~%10–25); ürünün kategorisine göre güncelle.
KANALLAR = {
    "site": {"odeme_komisyonu": 0.035, "pazaryeri_komisyonu": 0.0, "reklam_payi": 0.20},
    "trendyol": {"odeme_komisyonu": 0.0, "pazaryeri_komisyonu": 0.20, "reklam_payi": 0.08},
}

YUKSEK_IADE_KELIMELERI = ["beden", "size", "numara", "ayakkabı", "shoe", "elbise", "dress", "pantolon", "gömlek",
                          "tişört", "t-shirt", "mont", "ceket", "giyim", "kot", "jeans", "sütyen", "bra", "yüzük", "ring"]


def ayarlar(kanal: str = "site", a: dict | None = None) -> dict:
    return {**AYARLAR, **KANALLAR.get(kanal, {}), **(a or {})}


def iade_orani_tahmini(u: dict) -> tuple[float, str]:
    """Beden/renk/uyum gerektiren ürünlerde %25, diğerlerinde %15."""
    metin = " ".join([u.get("baslik") or ""] + [str(v.get("ad") or "") for v in u.get("varyantlar") or []]).lower()
    bul = [k for k in YUKSEK_IADE_KELIMELERI if k in metin]
    if bul:
        return 0.25, f"beden/uyum gerektiren ürün ({', '.join(bul[:3])})"
    return AYARLAR["iade_orani"], "standart ürün"


def iade_maliyeti(maliyet: dict, a: dict) -> float:
    """Satılan her adet için beklenen iade maliyeti (TL)."""
    k = maliyet.get("kalemler", {})
    olay = (k.get("yurtici_kargo", 0) + a["iade_donus_kargo_tl"] + k.get("paketleme", 0)
            + a["iade_kayip_orani"] * maliyet["toplam"])
    return round(a["iade_orani"] * olay, 2)


def yuzdesel_kesinti(a: dict) -> float:
    return a["odeme_komisyonu"] + a["pazaryeri_komisyonu"] + a["reklam_payi"]


def minimum_fiyat(maliyet: dict, a: dict) -> float:
    """Net marj = hedef olacak en düşük KDV dahil satış fiyatı.
    Kâr = P/(1+KDV) − sabit − P × kesintiler = hedef × P  →  P = sabit / (1/(1+KDV) − kesintiler − hedef)."""
    sabit = maliyet["toplam"] + iade_maliyeti(maliyet, a)
    payda = 1 / (1 + a["kdv"]) - yuzdesel_kesinti(a) - a["hedef_marj"]
    return round(sabit / payda, 2) if payda > 0 else float("inf")


def psikolojik(fiyat: float) -> int:
    """1.000 altı: x49 / x99, üstü: x99'a yuvarla (yukarı)."""
    if fiyat < 1000:
        adim = 50
        return int(math.ceil((fiyat + 1) / adim) * adim - 1)
    return int(math.ceil((fiyat + 1) / 100) * 100 - 1)


def birim_maliyet(urun_tl: float, kargo_tl: float, senaryo: str = "stok", a: dict | None = None) -> dict:
    a = {**AYARLAR, **(a or {})}
    kalemler = {"urun": urun_tl}
    if senaryo == "stok":
        kalemler["navlun"] = a["stok_navlun_tl"]
        kalemler["ithalat_vergi_araci"] = round((urun_tl + a["stok_navlun_tl"]) * a["stok_ithalat_orani"], 2)
    else:  # dogrudan
        kalemler["uluslararasi_kargo"] = kargo_tl
        kalemler["vergi"] = round((urun_tl + kargo_tl) * a["dogrudan_vergi_orani"], 2)
    kalemler["paketleme"] = a["paketleme_tl"]
    kalemler["yurtici_kargo"] = a["yurtici_kargo_tl"] if senaryo == "stok" else 0.0
    return {"senaryo": senaryo, "kalemler": kalemler, "toplam": round(sum(kalemler.values()), 2)}


def fiyat_analizi(satis_fiyati: float, maliyet: dict | float, a: dict | None = None) -> dict:
    """maliyet: birim_maliyet() çıktısı (tercih edilen) ya da sadece toplam TL."""
    a = {**AYARLAR, **(a or {})}
    if not isinstance(maliyet, dict):
        maliyet = {"toplam": maliyet, "kalemler": {}}
    P = satis_fiyati
    kdv_haric = P / (1 + a["kdv"])
    komisyon = P * (a["odeme_komisyonu"] + a["pazaryeri_komisyonu"])
    iade = iade_maliyeti(maliyet, a)
    reklam = P * a["reklam_payi"]
    reklam_oncesi_kar = kdv_haric - maliyet["toplam"] - komisyon - iade
    net_kar = reklam_oncesi_kar - reklam
    ro_marj = reklam_oncesi_kar / P if P else 0
    net_marj = net_kar / P if P else 0
    return {
        "fiyat": P,
        "kdv_haric": round(kdv_haric, 2),
        "komisyon": round(komisyon, 2),
        "iade_maliyeti": iade,
        "reklam_payi": round(reklam, 2),
        "reklam_oncesi_kar": round(reklam_oncesi_kar, 2),
        "birim_kar": round(net_kar, 2),
        "marj_yuzde": round(net_marj * 100, 1),
        "reklam_oncesi_marj_yuzde": round(ro_marj * 100, 1),
        "hedefe_uygun": net_marj >= a["hedef_marj"] - 1e-9,
        # Başabaş: reklama harcanabilecek en fazla tutar = reklam öncesi kâr
        "basabas_roas": round(1 / ro_marj, 2) if ro_marj > 0 else None,
        "basabas_cpa": round(reklam_oncesi_kar, 2) if reklam_oncesi_kar > 0 else None,
        # Hedef CPA = sipariş başına planlanan reklam payı (bu CPA'da net marj hedefi tutar).
        # Başabaş CPA ise reklama harcanabilecek en fazla tutardır; hedef olarak kullanılmaz.
        "hedef_cpa": round(reklam, 2) if reklam > 0 else None,
        # Kapatma kuralları (Modül 6 + İleri Seviye Reklamcılık 13/16)
        "kapat_0_atc_harcama": round(net_kar, 2) if net_kar > 0 else None,
        "kapat_0_satis_harcama": round(2 * reklam, 2) if reklam > 0 and reklam_oncesi_kar > 0 else None,
        "kapat_yuksek_cpa": round(2 * reklam, 2) if reklam > 0 and reklam_oncesi_kar > 0 else None,
    }


def fiyat_secenekleri(maliyet: dict | float, rakip_ozet: dict | None = None, a: dict | None = None) -> list[dict]:
    """Hedef marjı tutturan minimum fiyat + rakip verisi varsa alt çeyrek / medyan / üst çeyrek
    (yoksa maliyetin 2,2x / 3x / 3,8x katı)."""
    a = {**AYARLAR, **(a or {})}
    if not isinstance(maliyet, dict):
        maliyet = {"toplam": maliyet, "kalemler": {}}
    m = maliyet["toplam"]
    if rakip_ozet and rakip_ozet.get("medyan"):
        hedefler = [("agresif", rakip_ozet["alt_ceyrek"]), ("dengeli", rakip_ozet["medyan"]),
                    ("premium", rakip_ozet["ust_ceyrek"])]
        kaynak = "Trendyol rakip fiyatları"
    else:
        hedefler = [("agresif", m * 2.2), ("dengeli", m * 3.0), ("premium", m * 3.8)]
        kaynak = "maliyet katsayısı (rakip verisi yok)"
    mf = minimum_fiyat(maliyet, a)
    if mf != float("inf"):
        hedefler.insert(0, (f"minimum (%{a['hedef_marj'] * 100:.0f} marj)", mf))
    out = []
    for ad, f in hedefler:
        f = psikolojik(f)
        r = fiyat_analizi(f, maliyet, a)
        r.update({"secenek": ad, "kaynak": kaynak})
        r["paket_2"] = psikolojik(f * 2 * 0.85)
        r["paket_3"] = psikolojik(f * 3 * 0.75)
        out.append(r)
    return out


def firsat_skoru(u: dict, rakip_medyan: float | None = None) -> float:
    """Arama sonuçlarını sıralamak için 0-100 arası kaba skor.
    Talep (satış), memnuniyet (puan) ve fiyat boşluğu (rakip medyanı / tahmini maliyet)."""
    satis = u.get("satis") or 0
    puan = u.get("puan") or 0
    talep = min(math.log10(satis + 1) / 4, 1) * 45           # 10.000 satış = tam puan
    memnuniyet = max(0.0, (puan - 4.0) / 1.0) * 25 if puan else 0
    bosluk = 0.0
    if rakip_medyan and u.get("fiyat"):
        maliyet = birim_maliyet(u["fiyat"], 0, "stok")["toplam"]
        kat = rakip_medyan / maliyet
        bosluk = min(max((kat - 1.5) / 2.0, 0), 1) * 30       # 3,5x ve üstü = tam puan
    else:
        bosluk = 15.0                                          # bilinmiyor: nötr
    return round(talep + memnuniyet + bosluk, 1)
