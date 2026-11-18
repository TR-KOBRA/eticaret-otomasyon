"""Ürün sinyali (Mert Kurtul yöntemi): Amazon'da YENİ ÇIKIP yükselen ürünler → Türkiye doğrulaması → ters hesap.

  python sinyal.py                         # sıradaki 2 kategori (sinyal-kategoriler.txt)
  python sinyal.py --kategori pet-supplies --kategori kitchen --dogrula 4

Akış:
 1. Amazon "New Releases" (Apify fanndev/amazon-bestsellers-movers-tracker, CAPTCHA çözmez; ~0,003 $/ürün)
 2. Mert filtreleri: puan ≥ 3,5 · fiyat 6–100 $ · yorum ≤ 1000
 3. Gemini (tek istek / kategori): Türkiye'ye lokalleşebilen, problem çözen, hafif, tüketim/takviye/marka bağımlı OLMAYAN ürünleri seçer,
    Türkçe arama kelimesi ve pazarlama açılarını yazar
 4. Trendyol (Apify, yorumsuz): aynı tür ürünler (Gemini eşleştirmesi) → piyasa medyanı ve doygunluk (güçlü rakip = 100+ yorum)
 5. Meta Reklam Kütüphanesi (TR): farklı reklamveren ≥ 20 → doymuş, 8–19 → kalabalık (reklam_kutuphanesi.py, ücretsiz)
 6. Ters hesap: Trendyol medyanında %20 net kâr için toptancıdan en fazla kaça (KDV dahil) alınmalı
Karar: Olur (uygun pazar + kârlı alış tavanı) · Belki (kalabalık / Türkiye'de yok / tavan çok düşük) · Olmaz (doymuş)
Bütçe: aylık Apify harcaması SINYAL_APIFY_TAVAN_USD'yi (4 $; toplam 5 $) geçerse çalışmaz.
Otomatik: sinyal_calistir.cmd (Görev Zamanlayıcı, Pzt ve Per 09:00) → 2 kategori × 30 ürün, 3 doğrulama ≈ 0,33 $/çalışma
≈ 3 $/ay; tavan dolunca kendiliğinden durur.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import statistics as st
import sys
from decimal import Decimal
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

KOK = Path(__file__).parent
load_dotenv(KOK / ".env")
load_dotenv(KOK.parent / ".env")

import gemini  # noqa: E402
import hesap  # noqa: E402
import rakipler  # noqa: E402

KLASOR = KOK / "cikti" / "sinyal"
KATEGORI_DOSYA = KOK / "sinyal-kategoriler.txt"
DURUM = KLASOR / "durum.json"
AKTOR = "fanndev/amazon-bestsellers-movers-tracker"
# İsteğe bağlı ikinci kaynak: TikTok Shop (ABD) son 7 günde geliri en hızlı artanlar (~0,003 $/ürün, kaynak başına en az 25 ürün).
# DİKKAT (2026-11-18 denendi): Apify ÜCRETSİZ planında bu aktör veri vermiyor (sadece "free-plan" uyarısı, 0,005 $ başlangıç ücreti);
# ücretli Apify planında çalışır. Ücretsiz alternatifler giriş çerezi (doliz) ya da residential proxy (datapeak, bovi) istiyor → kullanılmadı.
TT_AKTOR = "lergassy/tiktok-shop-top-products-scraper"
TT_KATEGORI = {"pet-supplies": "Pet Supplies", "kitchen": "Kitchenware", "home-garden": "Home Supplies", "baby-products": "Baby & Maternity",
               "office-products": "Office Supplies", "automotive": "Automotive & Motorcycle", "sporting-goods": "Sports & Outdoor",
               "hi": "Tools & Hardware", "toys-and-games": "Toys & Hobbies", "garden": "Home Supplies"}
APIFY_TAVAN = float(os.getenv("SINYAL_APIFY_TAVAN_USD", "4"))
USD_TL = float(os.getenv("USD_TL", "41"))     # yalnızca Amazon fiyatını fikir olsun diye TL'ye çevirmek için

SEC_SISTEM = (
    "Türkiye'de Shopify mağazası ve Meta reklamıyla satış yapan, yerli toptancıdan ya da Türkiye'de ürettirerek tedarik eden "
    "bir e-ticaretçiye ürün seçiyorsun (Mert Kurtul yöntemi). Kurallar: ürün Türkiye'deki insanın yaşamına LOKALLEŞEBİLMELİ; "
    "net bir problemi çözmeli ya da videoda dikkat çekici bir demo sunmalı; en az 3 farklı pazarlama açısı olmalı; hafif (≈1 kg altı) olmalı. "
    "SEÇME: gıda, mama, ödül maması, takviye, ilaç, kozmetik/cilt ürünü, tek kullanımlık sarf (poşet, kum, ped), büyük markaya bağlı ürün "
    "(Amazon Basics, Purina, Blink vb. markanın kendisi satılmaz), giyim, takı, ayakkabı, sertifika gerektiren tıbbi ürün, yetişkin ürünü. "
    "Sağlık/tedavi vaadi yazma. Türkçe yaz ve Türkçe karakterleri mutlaka kullan (ç, ğ, ı, ö, ş, ü): 'köpek', 'kedi taşıma çantası' gibi; "
    "'kopek', 'tasima' gibi ASCII yazma."
)
SEC_SEMA = {"type": "OBJECT", "properties": {"secilenler": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
    "no": {"type": "INTEGER"}, "tr_kelime": {"type": "STRING", "description": "Trendyol'da aranacak 2-4 kelimelik Türkçe ürün türü adı, Türkçe karakterlerle (ç ğ ı ö ş ü), küçük harf"},
    "urun_turu": {"type": "STRING"}, "problem": {"type": "STRING"}, "acilar": {"type": "ARRAY", "items": {"type": "STRING"}},
    "neden": {"type": "STRING", "description": "Türkiye'de neden satar, tek cümle"}},
    "required": ["no", "tr_kelime", "urun_turu", "problem", "acilar", "neden"]}}}, "required": ["secilenler"]}
ESLE_SEMA = {"type": "OBJECT", "properties": {"benzer": {"type": "ARRAY", "items": {"type": "INTEGER"}}}, "required": ["benzer"]}


def kategoriler() -> list[str]:
    if not KATEGORI_DOSYA.exists():
        return ["pet-supplies", "kitchen"]
    return [s.split("#")[0].strip() for s in KATEGORI_DOSYA.read_text(encoding="utf-8").splitlines() if s.split("#")[0].strip()]


def _durum() -> dict:
    try:
        return json.loads(DURUM.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"sira": 0, "gorulen": []}


def apify_harcama() -> float | None:
    try:
        from apify_client import ApifyClient
        return rakipler._aylik_harcama(ApifyClient(os.environ["APIFY_TOKEN"]))
    except Exception:  # noqa: BLE001
        return None


def amazon_yeni(kategori: str, adet: int) -> list[dict]:
    """Aynı gün aynı kategori tekrar istenirse önbellekten okur (Apify'a ikinci kez ödeme yapılmaz)."""
    onbellek = KLASOR / f"amazon-{kategori}-{dt.date.today():%Y%m%d}.json"
    if onbellek.exists():
        return json.loads(onbellek.read_text(encoding="utf-8"))
    liste = _amazon_cek(kategori, adet)
    onbellek.write_text(json.dumps(liste, ensure_ascii=False), encoding="utf-8")
    return liste


def _amazon_cek(kategori: str, adet: int) -> list[dict]:
    from apify_client import ApifyClient
    c = ApifyClient(os.environ["APIFY_TOKEN"])
    run = c.actor(AKTOR).call(run_input={"categories": [kategori], "listType": "new-releases", "marketplace": "com",
                                          "maxRank": adet, "trackMovement": False},
                              max_total_charge_usd=Decimal(str(round(adet * 0.004, 2))), run_timeout=timedelta(minutes=6), logger=None)
    ds = run["defaultDatasetId"] if isinstance(run, dict) else run.default_dataset_id
    return [x for x in c.dataset(ds).iterate_items() if not x.get("_error")]


def tiktok_yukselen(kategori: str, adet: int = 25) -> list[dict]:
    """TikTok Shop ABD: kategoride son 7 günde gelir artışı en yüksek ürünler (aynı gün önbellekten). Satır biçimi Amazon kaydına uydurulur."""
    ad = TT_KATEGORI.get(kategori)
    if not ad:
        return []
    onbellek = KLASOR / f"tiktok-{kategori}-{dt.date.today():%Y%m%d}.json"
    if onbellek.exists():
        return json.loads(onbellek.read_text(encoding="utf-8"))
    from apify_client import ApifyClient
    adet = max(25, adet)
    c = ApifyClient(os.environ["APIFY_TOKEN"])
    run = c.actor(TT_AKTOR).call(run_input={"categories": [ad], "country": "US", "period": "last7Day", "sortBy": "revenueGrowth",
                                             "maxResultsPerSource": adet, "minPrice": 6, "maxPrice": 100, "addAnalytics": False},
                                 max_total_charge_usd=Decimal(str(round(adet * 0.0035 + 0.02, 2))), run_timeout=timedelta(minutes=6), logger=None)
    ds = run["defaultDatasetId"] if isinstance(run, dict) else run.default_dataset_id
    out, uyari = [], None
    for x in c.dataset(ds).iterate_items():
        if x.get("type") == "notice" and x.get("kind") == "free-plan":
            uyari = "Apify ücretsiz planında TikTok Shop verisi gelmiyor (ücretli plan gerekir)"
        if x.get("type") != "product" or not x.get("productId"):
            continue
        out.append({"asin": f"TT{x['productId']}", "title": x.get("title"), "price": x.get("avgSellingPrice"), "rating": None,
                    "reviewCount": x.get("reviewCount"), "imageUrl": x.get("image") or x.get("imageUrl"), "productUrl": x.get("url"),
                    "_source": "tiktok", "tt_buyume": x.get("revenueGrowthPercent"), "tt_satis": x.get("unitsSold"),
                    "tt_gelir": x.get("revenue"), "tt_video_gelir": x.get("videoRevenue"), "rank": x.get("rank")})
    if not out and uyari:
        raise RuntimeError(uyari)
    onbellek.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out


def mert_filtre(u: dict) -> tuple[bool, str]:
    p, r, y = u.get("price"), u.get("rating"), u.get("reviewCount")
    if r is not None and r < 3.5:
        return False, f"puan {r} < 3,5"
    if p is not None and not (6 <= p <= 100):
        return False, f"fiyat {p} $ (6–100 dışı)"
    if y is not None and y > 1000:
        return False, f"{y} yorum > 1000 (eski/oturmuş ürün)"
    return True, ""


def sec(urunler: list[dict], kategori: str) -> list[dict]:
    def satir(i, u):
        if u.get("_source") == "tiktok":
            return (f"{i}. [TikTok Shop ABD] {(u.get('title') or '')[:160]} | {u.get('price')} $ | 7 günde gelir artışı %{u.get('tt_buyume')} | "
                    f"{u.get('tt_satis')} satış")
        return f"{i}. [Amazon yeni çıkan] {(u.get('title') or '')[:160]} | {u.get('price')} $ | {u.get('rating')}★ | {u.get('reviewCount')} yorum"
    istem = "\n".join([f"'{kategori}' kategorisinde YENİ ÇIKAN / satışı hızla yükselen ürünler (Amazon ve TikTok Shop):", ""]
                      + [satir(i, u) for i, u in enumerate(urunler, 1)]
                      + ["", "Kurallara uyan en fazla 6 ürünü seç (uymayanı seçme, hiçbiri uymuyorsa boş liste)."])
    g = gemini.json_sor(istem, SEC_SEMA, sistem=SEC_SISTEM, sicaklik=0.2, toplu=True)
    import riskler
    out = []
    for s in g.get("secilenler") or []:
        if not 1 <= int(s["no"]) <= len(urunler):
            continue
        u0 = urunler[int(s["no"]) - 1]
        metin = f"{u0.get('title') or ''} {s.get('tr_kelime') or ''} {s.get('urun_turu') or ''}".lower()
        if any(riskler._kelime(metin, k) for k in riskler.BASLANGICA_UYGUN_DEGIL.values()):
            continue                                    # model kurala uymasa da giyim/takı/ayakkabı elenir (Mert Kurtul)
        if 1 <= int(s["no"]) <= len(urunler):
            out.append({**urunler[int(s["no"]) - 1], **{k: s[k] for k in ("tr_kelime", "urun_turu", "problem", "acilar", "neden")}})
    return out


def benzerleri(aday: dict, rk: dict) -> list[dict]:
    liste = rakipler.numarali_liste(rk, 30)
    if not liste:
        return []
    istem = "\n".join([f"Bizim ürün: {(aday.get('title') or '')[:200]} (tür: {aday['urun_turu']}).", "Trendyol sonuçları:"]
                      + [f"{i}. {x.get('ad')} | {x.get('fiyat')} TL" for i, x in enumerate(liste, 1)]
                      + ["", "Hangileri bizim ürünle AYNI tür ve işlevde? (aksesuar, yedek parça, başka ürün değil) Numaraları ver."])
    try:
        g = gemini.json_sor(istem, ESLE_SEMA, sicaklik=0.0, toplu=True)
    except Exception:  # noqa: BLE001
        return []
    return [liste[i - 1] for i in sorted({int(i) for i in g.get("benzer") or []}) if 1 <= i <= len(liste)]


alis_tavani = hesap.alis_tavani


def karar(dg: dict | None, benzer: int, tavan: float | None, medyan: float | None) -> tuple[str, str]:
    if dg and dg["seviye"] == "doymus":
        return "ELE", f"Pazar doymuş: {dg['guclu_rakip']} güçlü rakip (100+ yorum)"
    if benzer < 1:
        return "İYİLEŞTİR", "Trendyol'da aynısı yok → pazar boşluğu olabilir; talebi reklam testiyle doğrula, ürettirme/ithal seçeneğine bak"
    if tavan is None or (medyan and tavan < medyan * 0.15):
        return "İYİLEŞTİR", f"Piyasa fiyatı ({medyan:.0f} TL) düşük: kargo + koli + reklam sonrası alış payı çok dar"
    if dg and dg["seviye"] == "kalabalik":
        return "İYİLEŞTİR", f"Kalabalık: {dg['guclu_rakip']} güçlü rakip, en çok {dg['en_cok_yorum']} yorum → net farklılaşma gerekli"
    return "TESTE AL", f"Az rakip ({dg['guclu_rakip'] if dg else 0} güçlü) · toptancıdan en fazla {tavan:.0f} TL'ye (KDV dahil) bulursan kârlı"


def calistir(args) -> int:
    KLASOR.mkdir(parents=True, exist_ok=True)
    if not os.getenv("APIFY_TOKEN"):
        print("APIFY_TOKEN yok"); return 1
    harcama = apify_harcama()
    if harcama is not None and harcama >= APIFY_TAVAN:
        print(f"Apify bu ay {harcama:.2f} $ ≥ sinyal tavanı {APIFY_TAVAN} $ → çalıştırılmadı"); return 0
    d = _durum()
    tum = kategoriler()
    secili = args.kategori or [tum[(d["sira"] + i) % len(tum)] for i in range(min(args.kac, len(tum)))]
    a = hesap.ayarlar("site")
    sonuc, notlar = [], []
    for kat in secili:
        print(f"› Amazon yeni çıkanlar: {kat}")
        try:
            ham = amazon_yeni(kat, args.adet)
        except Exception as e:  # noqa: BLE001
            notlar.append(f"{kat}: Amazon listesi alınamadı ({type(e).__name__}: {str(e)[:120]})"); continue
        if args.tiktok:
            try:
                tt = tiktok_yukselen(kat, args.tiktok_adet)
                print(f"  TikTok Shop: {len(tt)} ürün")
                ham = ham + tt
            except Exception as e:  # noqa: BLE001
                notlar.append(f"{kat}: TikTok listesi alınamadı ({type(e).__name__}: {str(e)[:120]})")
        uygun = [u for u in ham if mert_filtre(u)[0] and u.get("asin") not in d["gorulen"]]
        print(f"  {len(ham)} ürün, Mert filtresinden {len(uygun)} geçti")
        if not uygun:
            continue
        try:
            secilen = sec(uygun, kat)
        except Exception as e:  # noqa: BLE001
            notlar.append(f"{kat}: yapay zekâ seçimi yapılamadı ({str(e)[:120]})"); continue
        print(f"  yapay zekâ {len(secilen)} ürünü Türkiye'ye uygun buldu")
        for u in secilen:
            u["kategori"] = kat
            sonuc.append(u)
            d["gorulen"].append(u.get("asin"))
    # Trendyol doğrulaması: en yeni / en az yorumlu adaylardan başlayarak
    sonuc.sort(key=lambda u: (u.get("reviewCount") or 0))
    for u in sonuc[: args.dogrula]:
        print(f"› Trendyol: {u['tr_kelime']}")
        rk = rakipler.trendyol(u["tr_kelime"], adet=args.trendyol_adet)
        if rk.get("hata"):
            notlar.append(f"{u['tr_kelime']}: {rk['hata']}"); continue
        b = benzerleri(u, rk)
        dg = rakipler.doygunluk(b) if b else None
        medyan = st.median([x["fiyat"] for x in b if x.get("fiyat")]) if b else None
        tavan = alis_tavani(medyan, a) if medyan else None
        k, neden = karar(dg, len(b), tavan, medyan)
        u.update({"trendyol": {"aranan": u["tr_kelime"], "sonuc": len(rk.get("urunler") or []), "benzer": len(b), "medyan": medyan,
                               "doygunluk": dg, "ornekler": [{k2: x.get(k2) for k2 in ("ad", "fiyat", "degerlendirme", "favori", "link")} for x in b[:5]]},
                  "alis_tavani": tavan, "karar": k, "neden": neden})
    # Meta Reklam Kütüphanesi (Türkiye): kaç reklamveren? (normal tarayıcı, gizlenme yok; ücretsiz)
    dogrulanan = [u for u in sonuc[: args.dogrula] if u.get("karar")]
    if dogrulanan and not args.reklam_yok:
        print("› Meta Reklam Kütüphanesi…")
        try:
            import reklam_kutuphanesi
            # Mert: farklı kelimelerle ara → tam ifade + son 2 kelime (ör. "otomatik akıllı kedi topu" + "kedi topu"); çok reklamı olan sayılır
            kisa = {u["tr_kelime"]: " ".join(u["tr_kelime"].split()[-2:]) for u in dogrulanan}
            aranan = list(dict.fromkeys([k for k in kisa] + [v for k, v in kisa.items() if v != k]))
            ham_rk = reklam_kutuphanesi.ara(aranan)
            rk_sonuc = {}
            for k, v in kisa.items():
                adaylar = [x for x in (ham_rk.get(k), ham_rk.get(v)) if x and not x.get("hata")]
                en = max(adaylar, key=lambda x: (x.get("reklamveren") or 0, x.get("toplam_reklam") or 0), default=ham_rk.get(k) or {})
                rk_sonuc[k] = {**en, "aranan_kelime": v if en is ham_rk.get(v) else k}
        except Exception as e:  # noqa: BLE001
            rk_sonuc = {}
            notlar.append(f"Reklam kütüphanesi okunamadı ({type(e).__name__}: {str(e)[:100]})")
        for u in dogrulanan:
            r = rk_sonuc.get(u["tr_kelime"]) or {}
            u["reklam"] = r
            if r.get("hata"):
                continue
            if r.get("seviye") == "doymus":
                u["karar"], u["neden"] = "ELE", f"Reklamda doymuş: {r['reklamveren']} farklı reklamveren (Mert: ~20 kişi pazarlıyorsa açılar tükenmiş)"
            elif r.get("seviye") == "kalabalik" and u["karar"] == "TESTE AL":
                u["karar"], u["neden"] = "İYİLEŞTİR", f"{r['reklamveren']} reklamveren var → farklı pazarlama açısı/teklif şart · {u['neden']}"
            elif r.get("seviye") == "reklam_yok" and u.get("trendyol", {}).get("benzer", 0) == 0:
                u["neden"] += " · Meta'da da reklamı yok (talep reklam testiyle doğrulanmalı)"
    for u in sonuc[args.dogrula:]:
        u.update({"karar": "EKSİK VERİ", "neden": "Trendyol doğrulaması bu çalıştırmada yapılmadı (bütçe/limit)"})
    if not args.kategori:
        d["sira"] = (d["sira"] + len(secili)) % max(1, len(tum))
    d["gorulen"] = d["gorulen"][-2000:]
    d["son"] = dt.datetime.now().isoformat(timespec="minutes")
    DURUM.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    zaman = dt.datetime.now().strftime("%Y%m%d-%H%M")
    kayit = {"zaman": d["son"], "kategoriler": secili, "usd_tl": USD_TL, "urunler": sonuc, "notlar": notlar}
    (KLASOR / f"sinyal-{zaman}.json").write_text(json.dumps(kayit, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    sira = {"TESTE AL": 0, "İYİLEŞTİR": 1, "EKSİK VERİ": 2, "ELE": 3}
    print(f"✓ {len(sonuc)} sinyal → cikti/sinyal/sinyal-{zaman}.json")
    for u in sorted(sonuc, key=lambda x: sira.get(x["karar"], 9)):
        print(f"  [{u['karar']}] {u['tr_kelime']} — {u['neden']}")
    for n in notlar:
        print("  not:", n)
    return 0


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Amazon yeni çıkanlar → Türkiye doğrulaması (Mert Kurtul yöntemi)")
    p.add_argument("--kategori", action="append", help="Amazon kategori slug'ı (ör. pet-supplies); verilmezse listeden sıradaki")
    p.add_argument("--kac", type=int, default=2, help="kategori sayısı (listeden)")
    p.add_argument("--adet", type=int, default=40, help="kategori başına Amazon ürünü (≈0,003 $/ürün)")
    p.add_argument("--dogrula", type=int, default=4, help="Trendyol'da doğrulanacak aday sayısı (≈0,05 $/aday)")
    p.add_argument("--reklam-yok", action="store_true", help="Meta Reklam Kütüphanesi kontrolünü atla")
    p.add_argument("--trendyol-adet", type=int, default=24, help="aday başına okunacak Trendyol sonucu (≈0,002 $/sonuç)")
    p.add_argument("--tiktok", action="store_true", help="TikTok Shop (ABD) yükselenlerini de ekle (~0,08 $/kategori; ücretli Apify planı gerekir)")
    p.add_argument("--tiktok-adet", type=int, default=25, help="kategori başına TikTok ürünü (en az 25)")
    sys.exit(calistir(p.parse_args()))


if __name__ == "__main__":
    main()
