"""Shopify Admin GraphQL — panel için SADECE OKUMA (mağaza, siparişler, ürünler).

.env: SHOPIFY_MAGAZA (xxx.myshopify.com) + SHOPIFY_ADMIN_TOKEN (özel uygulama, kapsamlar: read_orders, read_products, write_products).
Ürün oluşturma (taslak) hat/magaza.py içinde ve panelde ayrıca onay ister. Anahtar hiçbir yanıtta / hata mesajında yer almaz.
"""
from __future__ import annotations

import datetime as dt
import os
import time

import requests

SURUM = os.getenv("SHOPIFY_API_SURUM", "2025-10")
_ONBELLEK: dict[str, tuple[float, object]] = {}


class ShopifyHata(RuntimeError):
    pass


def yapilandirildi() -> bool:
    return bool(os.getenv("SHOPIFY_MAGAZA") and os.getenv("SHOPIFY_ADMIN_TOKEN"))


def gql(sorgu: str, degisken: dict | None = None) -> dict:
    magaza, token = os.getenv("SHOPIFY_MAGAZA"), os.getenv("SHOPIFY_ADMIN_TOKEN")
    if not (magaza and token):
        raise ShopifyHata("Shopify bağlı değil")
    try:
        r = requests.post(f"https://{magaza}/admin/api/{SURUM}/graphql.json", json={"query": sorgu, "variables": degisken or {}},
                          headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"}, timeout=40)
    except requests.RequestException as e:
        raise ShopifyHata(f"Shopify'a ulaşılamadı ({type(e).__name__})") from None
    if r.status_code == 401:
        raise ShopifyHata("Anahtar geçersiz (401): Admin API erişim anahtarını kontrol et")
    if r.status_code == 403:
        raise ShopifyHata("Yetki yok (403): özel uygulamada read_orders / read_products kapsamlarını aç")
    if r.status_code == 404:
        raise ShopifyHata("Mağaza bulunamadı (404): adres xxx.myshopify.com biçiminde olmalı")
    if r.status_code != 200:
        raise ShopifyHata(f"Shopify HTTP {r.status_code}")
    d = r.json()
    if d.get("errors"):
        raise ShopifyHata("Shopify: " + "; ".join(str(e.get("message", e)) for e in d["errors"])[:300])
    return d["data"]


def _onbellek(anahtar: str, sure: float, f):
    t, v = _ONBELLEK.get(anahtar, (0, None))
    if time.time() - t > sure:
        v = f()
        _ONBELLEK[anahtar] = (time.time(), v)
    return v


def magaza() -> dict:
    return _onbellek("magaza", 600, lambda: gql("{ shop { name myshopifyDomain currencyCode plan { displayName } } }")["shop"])


SIPARIS_Q = """query($q: String!, $son: String) {
  orders(first: 100, after: $son, query: $q, sortKey: CREATED_AT) {
    pageInfo { hasNextPage endCursor }
    nodes { createdAt cancelledAt displayFinancialStatus currentSubtotalLineItemsQuantity
      totalPriceSet { shopMoney { amount } } totalRefundedSet { shopMoney { amount } } }
  }
}"""


def ozetle(siparisler: list[dict], gun: int, bugun: dt.date | None = None) -> dict:
    """Ham siparişlerden günlük ciro / sipariş / adet / iade ve toplamlar."""
    bugun = bugun or dt.date.today()
    gunluk = {(bugun - dt.timedelta(days=i)).isoformat(): {"ciro": 0.0, "siparis": 0, "adet": 0, "iade": 0.0} for i in range(gun)}
    for s in siparisler:
        if s.get("cancelledAt"):
            continue
        g = s["createdAt"][:10]
        if g not in gunluk:
            continue
        gunluk[g]["ciro"] += float(s["totalPriceSet"]["shopMoney"]["amount"])
        gunluk[g]["iade"] += float((s.get("totalRefundedSet") or {}).get("shopMoney", {}).get("amount") or 0)
        gunluk[g]["siparis"] += 1
        gunluk[g]["adet"] += int(s.get("currentSubtotalLineItemsQuantity") or 0)
    seri = [{"gun": k, **v} for k, v in sorted(gunluk.items())]
    ciro = sum(x["ciro"] for x in seri)
    sip = sum(x["siparis"] for x in seri)
    iade = sum(x["iade"] for x in seri)
    return {"gun": gun, "ciro": round(ciro, 2), "siparis": sip, "adet": sum(x["adet"] for x in seri),
            "ortalama_sepet": round(ciro / sip, 2) if sip else None, "iade": round(iade, 2),
            "iade_orani": round(iade / ciro * 100, 1) if ciro else None, "seri": seri}


def satis(gun: int = 30) -> dict:
    def oku():
        bas = (dt.date.today() - dt.timedelta(days=gun - 1)).isoformat()
        hepsi, son = [], None
        for _ in range(20):                                   # en fazla 2.000 sipariş
            d = gql(SIPARIS_Q, {"q": f"created_at:>={bas}", "son": son})["orders"]
            hepsi += d["nodes"]
            if not d["pageInfo"]["hasNextPage"]:
                break
            son = d["pageInfo"]["endCursor"]
        return ozetle(hepsi, gun)
    return _onbellek(f"satis{gun}", 300, oku)


def urunler() -> list[dict]:
    q = "{ products(first: 25, sortKey: UPDATED_AT, reverse: true) { nodes { title status totalInventory handle featuredMedia { preview { image { url } } } } } }"
    return _onbellek("urunler", 300, lambda: [
        {"baslik": n["title"], "durum": n["status"], "stok": n.get("totalInventory"), "handle": n["handle"],
         "gorsel": ((((n.get("featuredMedia") or {}).get("preview") or {}).get("image") or {}).get("url"))}
        for n in gql(q)["products"]["nodes"]])


def temizle():
    _ONBELLEK.clear()
