"""Trendyol rakip taraması (Apify aktörü: memo23/trendyol-scraper).

Trendyol doğrudan erişimde Cloudflare doğrulaması gösteriyor; onu atlatmaya çalışmıyoruz.
Bunun yerine Apify'daki hazır aktörü kullanıyoruz. .env içinde APIFY_TOKEN gerekir.
Ücret: sonuç başına (yaklaşık 0,50 $ / 1.000 ürün, detay ve yorumlar ayrıca).
"""
from __future__ import annotations

import os
import statistics as st
from datetime import timedelta
from decimal import Decimal

AKTOR = "memo23/trendyol-scraper"
# Ücretsiz planda Apify aylık limiti değiştirtmiyor (sabit ~6 $), bu yüzden bütçeyi burada tutuyoruz.
AYLIK_BUTCE_USD = float(os.getenv("APIFY_AYLIK_BUTCE_USD", "5"))
CALISMA_BASI_MAX_USD = float(os.getenv("APIFY_CALISMA_MAX_USD", "0.50"))


def _aylik_harcama(client) -> float | None:
    try:
        d = client.user().limits()
        cur = d.get("current", {}) if isinstance(d, dict) else getattr(d, "current", None)
        if isinstance(cur, dict):
            return float(cur.get("monthlyUsageUsd") or 0)
        return float(getattr(cur, "monthly_usage_usd", 0) or 0)
    except Exception:
        return None


def _sayi(x):
    try:
        return float(str(x).replace(".", "").replace(",", ".")) if isinstance(x, str) else float(x)
    except (TypeError, ValueError):
        return None


def ozet_hesapla(urunler: list[dict]) -> dict:
    """Fiyat dağılımı (min, çeyrekler, medyan, max) ve toplam değerlendirme."""
    fiyatlar = sorted(u["fiyat"] for u in urunler if u.get("fiyat"))
    if not fiyatlar:
        return {}
    return {
        "urun_sayisi": len(urunler),
        "min": fiyatlar[0],
        "medyan": st.median(fiyatlar),
        "max": fiyatlar[-1],
        "alt_ceyrek": fiyatlar[len(fiyatlar) // 4],
        "ust_ceyrek": fiyatlar[(len(fiyatlar) * 3) // 4],
        "toplam_degerlendirme": sum(int(u.get("degerlendirme") or 0) for u in urunler),
    }


def benzer_rakip(rk: dict | None, numaralar: list[int] | None, en_az: int = 3) -> dict | None:
    """Rakip analizinin seçtiği aynı tür/işlevdeki ürünlerle yeni bir rakip verisi döndürür.
    Eşleşme `en_az`dan azsa: fiyat kıyası güvenilmez → ozet boş, `benzer_yok` işaretli (kelime ortalamasına güvenilmez)."""
    if not rk or rk.get("hata") or numaralar is None:
        return rk
    liste = numarali_liste(rk)
    secilen = [liste[i - 1] for i in sorted(set(numaralar)) if 1 <= i <= len(liste)]
    yeni = {**rk, "tum_ozet": rk.get("tum_ozet") or rk.get("ozet"), "benzer_sayisi": len(secilen), "benzerler": secilen}
    yeni.pop("benzer_yok", None)
    if len(secilen) >= en_az:
        yeni["ozet"] = {**ozet_hesapla(secilen), **{k: v for k, v in (rk.get("ozet") or {}).items() if k.startswith("apify")},
                        "kapsam": f"{len(secilen)} benzer ürün (toplam {len(liste)} sonuçtan)"}
    else:
        yeni["ozet"] = {}
        yeni["benzer_yok"] = True
    return yeni


def numarali_liste(rk: dict, adet: int = 40) -> list[dict]:
    """Rakip analizi istemindeki numaralı liste ile aynı sıra (değerlendirme sayısına göre)."""
    ur = sorted(rk.get("urunler") or [], key=lambda x: -int(x.get("degerlendirme") or 0))
    return [u for u in ur if u.get("fiyat")][:adet]


def trendyol(kelime: str, adet: int = 30, yorumlar: bool = False, yorum_adedi: int = 20) -> dict:
    token = os.getenv("APIFY_TOKEN")
    if not token:
        return {"hata": "APIFY_TOKEN tanımlı değil (.env dosyasına ekle). Rakip taraması atlandı."}
    from apify_client import ApifyClient

    girdi = {
        "countries": ["TR"],
        "keywords": [kelime],
        "maxItems": adet,
        "scrapeProductDetails": True,
        "scrapeReviews": yorumlar,
        "maxReviewsPerProduct": yorum_adedi,
        "includeOtherSellers": False,
        "enrichEmails": False,
        "splitByPrice": False,
    }
    client = ApifyClient(token)
    harcanan = _aylik_harcama(client)
    if harcanan is not None and harcanan + CALISMA_BASI_MAX_USD > AYLIK_BUTCE_USD:
        return {"hata": f"Aylık Apify bütçesi doluyor ({harcanan:.2f} $ / {AYLIK_BUTCE_USD:.2f} $). Rakip taraması atlandı."}
    try:
        run = client.actor(AKTOR).call(
            run_input=girdi,
            max_total_charge_usd=Decimal(str(CALISMA_BASI_MAX_USD)),
            run_timeout=timedelta(minutes=10),
        )
        ds = run["defaultDatasetId"] if isinstance(run, dict) else run.default_dataset_id
        ogeler = list(client.dataset(ds).iterate_items())
        ucret = run.get("usageTotalUsd") if isinstance(run, dict) else run.usage_total_usd
    except Exception as e:
        return {"hata": f"Apify çalıştırması başarısız: {type(e).__name__}: {e}"}

    urunler, yorum_listesi = [], []
    for o in ogeler:
        tip = o.get("type", "product")
        if tip == "review":
            yorum_listesi.append({
                "urun_id": o.get("productId"),
                "puan": o.get("rate"),
                "metin": o.get("comment"),
                "tarih": o.get("date"),
            })
            continue
        if tip not in ("product", "listing"):
            continue
        urunler.append({
            "id": o.get("productId"),
            "ad": o.get("name"),
            "marka": o.get("brand"),
            "kategori": o.get("categoryName"),
            "fiyat": _sayi(o.get("discountedPrice") or o.get("price")),
            "eski_fiyat": _sayi(o.get("originalPrice")),
            "puan": _sayi(o.get("ratingAverage")),
            "degerlendirme": o.get("ratingCount") or o.get("commentCount"),
            "favori": o.get("favoriteCount"),
            "satici": o.get("sellerName"),
            "satici_puan": o.get("sellerScore"),
            "ucretsiz_kargo": o.get("freeCargo"),
            "link": o.get("url"),
        })

    ozet = ozet_hesapla(urunler)
    ozet["apify_ucret_usd"] = round(float(ucret or 0), 4)
    ozet["apify_aylik_harcanan_usd"] = _aylik_harcama(client)
    return {"kelime": kelime, "ozet": ozet, "urunler": urunler, "yorumlar": yorum_listesi}
