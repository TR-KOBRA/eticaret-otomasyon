"""AliExpress veri toplama: anahtar kelimeyle ürün arama ve tek ürün detayı.

Normal bir Chromium ile sayfayı açar ve sayfanın kendi yüklediği JSON verisini okur.
Bot korumasını atlatmaya çalışmaz: doğrulama (CAPTCHA) sayfası çıkarsa DogrulamaGerekli
hatası verir ve durur. İstekler arasında bekleme vardır.
"""
from __future__ import annotations

import json
import random
import re
import time
from contextlib import contextmanager
from urllib.parse import quote

from playwright.sync_api import sync_playwright, Page, BrowserContext

TABAN = "https://tr.aliexpress.com"


class DogrulamaGerekli(RuntimeError):
    """AliExpress doğrulama/CAPTCHA istedi. Bir süre bekleyip tekrar dene ya da elle aç."""


def _bekle(min_sn=1.5, max_sn=3.5):
    time.sleep(random.uniform(min_sn, max_sn))


def sayi_cek(metin) -> int | None:
    """'1.000+ satıldı', '29 satıldı', '5000+ sold' -> int"""
    if metin is None:
        return None
    if isinstance(metin, (int, float)):
        return int(metin)
    m = re.search(r"(\d[\d.,]*)\s*(bin|b|k)?", str(metin), re.I)
    if not m:
        return None
    n = float(m.group(1).replace(".", "").replace(",", "."))
    if m.group(2):
        n *= 1000
    return int(n)


def urun_id(link_ya_da_id: str) -> str:
    m = re.search(r"(\d{10,})", str(link_ya_da_id))
    if not m:
        raise ValueError(f"Ürün kimliği bulunamadı: {link_ya_da_id}")
    return m.group(1)


@contextmanager
def tarayici(gorunur: bool = False):
    with sync_playwright() as p:
        b = p.chromium.launch(headless=not gorunur)
        ctx = b.new_context(locale="tr-TR", timezone_id="Europe/Istanbul",
                            viewport={"width": 1366, "height": 900})
        try:
            yield ctx
        finally:
            b.close()


def _dogrulama_kontrol(page: Page):
    if "punish" in page.url or "_____tmd_____" in page.url or \
            page.locator("#nc_1_n1z, .baxia-dialog, iframe[src*='punish']").count() > 0:
        raise DogrulamaGerekli(f"Doğrulama sayfası: {page.url}")


# ---------------------------------------------------------------- arama
SIRALAMA = {
    "populer": "default",
    "satis": "total_tranpro_desc",
    "fiyat_artan": "price_asc",
    "fiyat_azalan": "price_desc",
}


def ara(ctx: BrowserContext, kelime: str, sayfa_sayisi: int = 1, sirala: str = "populer") -> list[dict]:
    """Anahtar kelimeyle arama. Her ürün: id, baslik, fiyat, eski_fiyat, indirim, satis, puan, gorsel, link."""
    sonuc, gorulen = [], set()
    page = ctx.new_page()
    try:
        for s in range(1, sayfa_sayisi + 1):
            url = (f"{TABAN}/w/wholesale-{quote(kelime.replace(' ', '-'))}.html"
                   f"?SearchText={quote(kelime)}&page={s}")
            if sirala != "populer":  # satışa göre sıralama alaka düzeyini bozuyor, varsayılan alakaya göre
                url += f"&sortType={SIRALAMA.get(sirala, sirala)}"
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2500)
            ham = page.evaluate("window._dida_config_ && JSON.stringify(window._dida_config_._init_data_)")
            if not ham:
                _dogrulama_kontrol(page)
                break
            try:
                ogeler = json.loads(ham)["data"]["data"]["root"]["fields"]["mods"]["itemList"]["content"]
            except (KeyError, TypeError):
                break
            for it in ogeler:
                pid = it.get("productId")
                if not pid or pid in gorulen:
                    continue
                gorulen.add(pid)
                fiyat = (it.get("prices") or {}).get("salePrice") or {}
                eski = (it.get("prices") or {}).get("originalPrice") or {}
                img = ((it.get("image") or {}).get("imgUrl") or "")
                sonuc.append({
                    "id": pid,
                    "baslik": (it.get("title") or {}).get("displayTitle"),
                    "fiyat": fiyat.get("minPrice"),
                    "eski_fiyat": eski.get("minPrice"),
                    "para": fiyat.get("currencyCode"),
                    "indirim": fiyat.get("discount"),
                    "satis": sayi_cek((it.get("trade") or {}).get("tradeDesc")),
                    "puan": (it.get("evaluation") or {}).get("starRating"),
                    "gorsel": ("https:" + img) if img.startswith("//") else img,
                    "link": f"{TABAN}/item/{pid}.html",
                })
            _bekle()
    finally:
        page.close()
    return sonuc


# ---------------------------------------------------------------- ürün detayı
def _pdp_yakala(ctx: BrowserContext, pid: str) -> dict:
    page = ctx.new_page()
    yakalanan: dict = {}

    def on_resp(r):
        if "mtop.aliexpress.pdp.pc.query" not in r.url:
            return
        try:
            t = r.text()
        except Exception:
            return
        m = re.match(r"^\s*\w+\((.*)\)\s*;?\s*$", t, re.S)
        try:
            d = json.loads(m.group(1) if m else t)
        except json.JSONDecodeError:
            return
        res = (d.get("data") or {}).get("result")
        if res:
            yakalanan["pdp"] = res

    page.on("response", on_resp)
    try:
        page.goto(f"{TABAN}/item/{pid}.html", wait_until="domcontentloaded", timeout=60000)
        for _ in range(40):
            if "pdp" in yakalanan:
                break
            page.wait_for_timeout(500)
        if "pdp" not in yakalanan:  # veri geldiyse yan bileşenlerin doğrulaması önemsiz
            _dogrulama_kontrol(page)
    finally:
        page.close()
    if "pdp" not in yakalanan:
        raise RuntimeError("Ürün verisi yüklenmedi (sayfa değişmiş ya da ürün kaldırılmış olabilir).")
    return yakalanan["pdp"]


def _kargo(r: dict) -> list[dict]:
    out = []
    for o in (r.get("SHIPPING") or {}).get("originalLayoutResultList") or []:
        b = o.get("bizData") or {}
        out.append({
            "firma": b.get("deliveryProviderName") or b.get("company"),
            "ucret_tl": 0.0 if b.get("shippingFee") == "free" else b.get("displayAmount"),
            "ucretsiz": b.get("shippingFee") == "free",
            "gun_min": b.get("deliveryDayMin"),
            "gun_max": b.get("deliveryDayMax"),
            "nereden": b.get("shipFrom"),
            "takip": b.get("tracking") != "invisible",
        })
    return out


def _varyantlar(r: dict) -> list[dict]:
    fiyatlar = (r.get("PRICE") or {}).get("skuIdStrPriceInfoMap") or {}
    yollar = (r.get("SKU") or {}).get("skuPaths") or []
    adlar = {}
    for prop in (r.get("SKU") or {}).get("skuProperties") or []:
        for v in prop.get("skuPropertyValues") or []:
            adlar[str(v.get("propertyValueIdLong"))] = v.get("propertyValueDisplayName")
    out = []
    for y in yollar:
        sku = str(y.get("skuIdStr") or y.get("skuId"))
        attr = y.get("skuAttr") or ""
        ad = " / ".join(adlar.get(re.split(r"[:#]", p)[1], "") for p in attr.split(";") if ":" in p)
        f = fiyatlar.get(sku) or {}
        sale = f.get("salePriceLocal", "")
        m = re.match(r".*?\|(\d+)\|(\d+)", sale or "")
        out.append({
            "sku": sku,
            "ad": ad.strip(" /") or (attr.split("#", 1)[1] if "#" in attr else ""),
            "fiyat": float(f"{m.group(1)}.{m.group(2)}") if m else (f.get("originalPrice") or {}).get("value"),
            "stok": y.get("skuStock"),
            "satilabilir": y.get("salable"),
        })
    # Aynı adlı varyantları birleştir (satıcılar aynı rengi farklı kimlikle tekrar listeleyebiliyor)
    birlesik: dict[str, dict] = {}
    for v in out:
        k = v["ad"] or v["sku"]
        if k not in birlesik or (v["fiyat"] or 9e9) < (birlesik[k]["fiyat"] or 9e9):
            birlesik[k] = v
    return list(birlesik.values())


def _aciklama(ctx: BrowserContext, r: dict) -> dict:
    url = (r.get("DESC") or {}).get("nativeDescUrl")
    if not url:
        return {"metin": [], "gorseller": []}
    try:
        d = ctx.request.get(url, timeout=30000).json()
    except Exception:
        return {"metin": [], "gorseller": []}
    metin, gorsel = [], []

    def gez(mods):
        for m in mods or []:
            if m.get("type") == "text":
                c = (m.get("data") or {}).get("content")
                if c:
                    metin.append(c.strip())
            elif m.get("type") == "image":
                u = (m.get("data") or {}).get("url")
                if u:
                    gorsel.append(u)
            gez(m.get("children") or m.get("moduleList"))

    gez(d.get("moduleList"))
    return {"metin": metin, "gorseller": gorsel}


def _etiket(l: dict) -> dict:
    """Yorum etiketi: konu, oy sayısı ve seçeneklerin yüzdeleri (ör. Kalite: Kötü %20 / Oldu %57 / ...)."""
    kat = (l.get("categoryReviewLabelDTOList") or [{}])[0]
    return {
        "konu": kat.get("labelName"),
        "oy": l.get("count"),
        "dagilim": {o.get("labelValueName"): o.get("countPercentage")
                    for o in kat.get("labelValueOptions") or []},
    }


def yorumlar(ctx: BrowserContext, pid: str, adet: int = 40) -> dict:
    """Yorum özeti + yorumlar. Önce düşük puanlıları da almak için 'all' filtresiyle sayfalar."""
    toplam, ozet, liste, sayfa = 0, {}, [], 1
    while len(liste) < adet:
        u = (f"https://feedback.aliexpress.com/pc/searchEvaluation.do?productId={pid}&lang=tr_TR"
             f"&country=TR&page={sayfa}&pageSize=20&filter=all&sort=complex_default")
        try:
            d = (ctx.request.get(u, timeout=30000).json() or {}).get("data") or {}
        except Exception:
            break
        if sayfa == 1:
            st = d.get("productEvaluationStatistic") or {}
            toplam = d.get("totalNum") or 0
            ozet = {
                "toplam": toplam,
                "ortalama": st.get("evarageStar"),
                "yildiz": {i: st.get(k) for i, k in
                           [(5, "fiveStarNum"), (4, "fourStarNum"), (3, "threeStarNum"),
                            (2, "twoStarNum"), (1, "oneStarNum")]},
                "etiketler": [_etiket(l) for l in d.get("reviewStructuredLabelDTOList") or []],
            }
        ogeler = d.get("evaViewList") or []
        if not ogeler:
            break
        for e in ogeler:
            liste.append({
                "yildiz": (e.get("buyerEval") or 0) // 20 if (e.get("buyerEval") or 0) > 5 else e.get("buyerEval"),
                "metin": e.get("buyerTranslationFeedback") or e.get("buyerFeedback"),
                "ulke": e.get("buyerCountry"),
                "tarih": e.get("evalDate"),
                "varyant": e.get("skuInfo"),
                "fotograf": len(e.get("images") or []),
            })
        if sayfa >= (d.get("totalPage") or 1):
            break
        sayfa += 1
        _bekle(1, 2)
    return {"ozet": ozet, "liste": liste[:adet]}


def urun(ctx: BrowserContext, link_ya_da_id: str, yorum_adedi: int = 40) -> dict:
    pid = urun_id(link_ya_da_id)
    r = _pdp_yakala(ctx, pid)
    g = (r.get("GLOBAL_DATA") or {}).get("globalData") or {}
    if g.get("bigBossBan"):
        raise RuntimeError(f"Bu ürün Türkiye'ye satılmıyor: {g.get('bigBossBanTip') or g.get('errorCode')}")
    fiyat = (r.get("PRICE") or {}).get("targetSkuPriceInfo") or {}
    sale = re.match(r".*?\|(\d+)\|(\d+)", fiyat.get("salePriceLocal") or "")
    rating = r.get("PC_RATING") or {}
    shop = r.get("SHOP_CARD_PC") or {}
    imgs = (r.get("HEADER_IMAGE_PC") or {}).get("imagePathList") or []
    _bekle(1, 2)
    acik = _aciklama(ctx, r)
    _bekle(1, 2)
    yor = yorumlar(ctx, pid, yorum_adedi) if yorum_adedi else {"ozet": {}, "liste": []}
    return {
        "id": pid,
        "link": f"{TABAN}/item/{pid}.html",
        "baslik": (r.get("PRODUCT_TITLE") or {}).get("text"),
        "kategori_id": g.get("categoryId"),
        "fiyat": float(f"{sale.group(1)}.{sale.group(2)}") if sale else None,
        "eski_fiyat": (fiyat.get("originalPrice") or {}).get("value"),
        "para": (fiyat.get("originalPrice") or {}).get("currency"),
        "puan": float(rating["rating"]) if rating.get("rating") else None,
        "puan_sayisi": rating.get("totalValidNum"),
        "satis": sayi_cek(rating.get("otherText")),
        "stok": (r.get("QUANTITY_PC") or {}).get("totalAvailableInventory"),
        "ozellikler": {p.get("attrName"): p.get("attrValue")
                       for p in (r.get("PRODUCT_PROP_PC") or {}).get("showedProps") or []},
        "varyantlar": _varyantlar(r),
        "kargo": _kargo(r),
        "magaza": {
            "ad": shop.get("storeName"),
            "olumlu_oran": shop.get("sellerPositiveRate"),
            "puan": shop.get("sellerScore"),
            "toplam": shop.get("sellerTotalNum"),
            "seviye": shop.get("sellerLevel"),
        },
        "gorseller": imgs,
        "video": ((r.get("HEADER_IMAGE_PC") or {}).get("productVideo") or {}).get("videoUrl"),
        "aciklama": acik,
        "yorumlar": yor,
    }
