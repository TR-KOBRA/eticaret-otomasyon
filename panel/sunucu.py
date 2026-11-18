"""E-ticaret paneli: hattın tüm adımlarını tarayıcıdan izleme ve yönetme.

  python panel/sunucu.py            → http://127.0.0.1:8765

Sadece bu bilgisayardan erişilir (127.0.0.1). Komutları mevcut CLI'lar üzerinden çalıştırır (hat.py, arastir.py, gunluk.py),
yani panelde yapılan her şey terminalden yapılanla aynıdır. Para harcayan / dışarı gönderen işler (Shopify/Meta --gonder)
panelde yoktur; API anahtarları hiçbir yanıtta yer almaz (sadece "bağlı mı" bilgisi).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys
import threading
import uuid
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

PANEL = Path(__file__).resolve().parent
KOK = PANEL.parent                                   # eticaret/
ARASTIRMA = KOK / "urun-arastirma"
CIKTI = ARASTIRMA / "cikti"
GUNLUK = CIKTI / "gunluk"
PROJELER = KOK / "projeler"
ISLER = PANEL / "isler"
PY = sys.executable

sys.path.insert(0, str(KOK / "hat"))
import ortak  # noqa: E402
from ortak import ADIMLAR, Proje  # noqa: E402

ADIM_ADI = {
    "arastirma": "Ürün araştırması", "tedarik": "Tedarik", "marka": "Marka", "icerik": "İçerik", "gorsel": "Görseller",
    "magaza": "Mağaza", "instagram": "Instagram", "kreatif": "Reklam kreatifi", "reklam": "Reklam planı",
    "analiz": "Reklam analizi", "operasyon": "Operasyon",
}
ADIM_ACIKLAMA = {
    "arastirma": "AliExpress verisi, rakipler, trend ve 20 puanlık skor kartı",
    "tedarik": "Satıcıya 15 soru, numune kontrol listesi, kırmızı bayraklar",
    "marka": "8 isim önerisi, .com kontrolü, renk/font ve logo brifi",
    "icerik": "Ürün sayfası metni, SSS, SEO, paket metinleri, yasal şablonlar",
    "gorsel": "Beyaz zemin, yaşam ve detay görselleri, yazı logo",
    "magaza": "Shopify CSV ve ürün sayfası önizlemesi",
    "instagram": "Bio, 4 öne çıkan kapağı, 24 içerik takvimi",
    "kreatif": "4 açı × 3 hook, başlıklar, CTA, UGC senaryoları",
    "reklam": "ABO test planı, bütçe (3 × hedef CPA), kapatma kuralları",
    "analiz": "Reklam Yöneticisi CSV'si → kapat / izle / ölçekle",
    "operasyon": "Müşteri mesajları, stok eşiği, haftalık kâr tablosu",
}
ANAHTARLAR = ["GEMINI_API_KEY", "APIFY_TOKEN", "SHOPIFY_MAGAZA", "SHOPIFY_ADMIN_TOKEN", "META_ERISIM_TOKENI",
              "META_REKLAM_HESABI", "META_PIXEL_ID"]

app = FastAPI(title="E-ticaret paneli", docs_url=None, redoc_url=None)


# ---------------------------------------------------------------- yardımcılar
def _json(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _guvenli(taban: Path, goreli: str) -> Path:
    yol = (taban / goreli).resolve()
    if taban.resolve() not in yol.parents and yol != taban.resolve():
        raise HTTPException(400, "Geçersiz yol")
    if not yol.exists():
        raise HTTPException(404, "Dosya yok")
    return yol


def _proje(ad: str) -> Proje:
    if not re.fullmatch(r"[a-z0-9-]+", ad or "") or not (PROJELER / ad / "urun.json").exists():
        raise HTTPException(404, "Proje bulunamadı")
    return Proje(PROJELER / ad)


def eksikler(p: Proje, adim: str) -> list[str]:
    a = ADIMLAR[adim]
    e = [f"{ADIM_ADI[o]} onayı" for o in a["once"] if not p.onayli(o)]
    e += [f"{ADIM_ADI[g]} çıktısı" for g in a.get("gerekli", []) if not p.oku(g)]
    return e


def adim_durumu(p: Proje, adim: str) -> dict:
    d = p.durum["adimlar"].get(adim) or {}
    e = eksikler(p, adim)
    if d.get("durum") == "onaylandi":
        s = "onaylandi"
    elif d.get("durum") == "tamam":
        s = "tamam"
    elif d.get("durum") == "onay_bekliyor":
        s = "onay_bekliyor"
    elif e:
        s = "kilitli"
    else:
        s = "hazir"
    return {"anahtar": adim, "no": ADIMLAR[adim]["no"], "ad": ADIM_ADI[adim], "aciklama": ADIM_ACIKLAMA[adim], "durum": s,
            "zaman": d.get("zaman"), "onay_zamani": d.get("onay_zamani"), "onay_metni": ADIMLAR[adim]["onay"],
            "eksikler": e, "rapor": p.dosya(adim, "md").exists()}


def proje_ozeti(p: Proje) -> dict:
    sk = p.veri.get("skor") or {}
    adimlar = [adim_durumu(p, a) for a in ADIMLAR]
    biten = sum(a["durum"] in ("tamam", "onaylandi") for a in adimlar) + 1   # araştırma her zaman bitmiş
    bekleyen = [a["ad"] for a in adimlar if a["durum"] == "onay_bekliyor"]
    son = max([a["zaman"] or "" for a in adimlar] + [""])
    gorsel = None
    if (p.yol / "gorseller").exists():
        gorsel = next((f"/dosya/{p.ad}/gorseller/{x.name}" for x in sorted((p.yol / "gorseller").glob("*.*"))
                       if x.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") and "logo" not in x.name), None)
    gorsel = gorsel or (p.urun.get("gorseller") or [None])[0]
    return {"ad": p.ad, "baslik": p.urun.get("baslik"), "marka": p.secim("isim"), "karar": sk.get("karar"),
            "puan": sk.get("toplam"), "ilerleme": biten, "toplam_adim": len(ADIMLAR) + 1, "onay_bekleyen": bekleyen,
            "son_islem": son or None, "zorla": p.durum.get("zorla", False), "gorsel": gorsel,
            "asama": asama(p), "hazir": [a["ad"] for a in adimlar if a["durum"] == "hazir"],
            "adimlar": [{"anahtar": "arastirma", "durum": "tamam"}] + [{"anahtar": a["anahtar"], "durum": a["durum"]} for a in adimlar]}


VERI = PANEL / "veri.json"          # panelin kendi kayıtları (favori / reddedildi işaretleri)


def veri_oku() -> dict:
    return _json(VERI) or {"isaretler": {}}


def veri_yaz(v: dict):
    VERI.write_text(json.dumps(v, ensure_ascii=False, indent=1), encoding="utf-8")


def _aday_ozeti(j: Path, v: dict) -> dict:
    u, sk = v["urun"], v.get("skor") or {}
    fs = v.get("fiyat_secenekleri") or []
    piyasa = next((s for s in fs if s.get("secenek") == "dengeli"), None)
    mn = next((s for s in fs if str(s.get("secenek", "")).startswith("minimum")), None)
    rk = (v.get("trendyol") or {}).get("ozet") or {}
    m = re.search(r"-(\d{8}-\d{4})$", j.stem)
    riskler = v.get("riskler") or []
    an = v.get("rakip_analizi") or {}
    return {
        "id": str(u.get("id")), "baslik": u.get("baslik"), "link": u.get("link"), "gorsel": (u.get("gorseller") or [None])[0],
        "karar": sk.get("karar"), "puan": sk.get("toplam"),
        "maliyet": ((v.get("maliyet") or {}).get("stok") or {}).get("toplam"), "ae_fiyat": u.get("fiyat"),
        "min_fiyat": (mn or {}).get("fiyat"), "piyasa_fiyat": (piyasa or {}).get("fiyat") if rk.get("medyan") else None,
        "piyasa_marj": (piyasa or {}).get("marj_yuzde") if rk.get("medyan") else None, "rakip_medyan": rk.get("medyan"),
        "rakip_sayisi": rk.get("urun_sayisi"), "satis": u.get("satis"), "puan_ae": u.get("puan"),
        "benzer_yok": bool((v.get("trendyol") or {}).get("benzer_yok")), "benzer_sayisi": (v.get("trendyol") or {}).get("benzer_sayisi"),
        "yuksek_risk": sum(1 for r in riskler if r.get("seviye") == "yuksek"),
        "kargo_riski": (v.get("kargo_riski") or {}).get("seviye"), "iade_orani": (v.get("iade") or {}).get("oran"),
        "ayrisma": an.get("ayrisma_puani"),
        "tarih": dt.datetime.strptime(m.group(1), "%Y%m%d-%H%M").isoformat(timespec="minutes") if m else None,
        "json": j.name, "rapor": j.with_suffix(".md").name if j.with_suffix(".md").exists() else None,
    }


def arastirmalar() -> list[dict]:
    son: dict[str, dict] = {}
    for j in sorted(CIKTI.glob("urun-*.json")):           # zaman damgası sırası: aynı ürünün en yeni değerlendirmesi kalır
        v = _json(j)
        if v and "urun" in v:
            son[str(v["urun"].get("id"))] = _aday_ozeti(j, v)
    projeler = {}
    for d in PROJELER.glob("*/urun.json"):
        pid = str(((_json(d) or {}).get("urun") or {}).get("id"))
        projeler[pid] = d.parent.name
    isaret = veri_oku()["isaretler"]
    out = sorted(son.values(), key=lambda x: x["tarih"] or "", reverse=True)
    for x in out:
        x["proje"] = projeler.get(x["id"])
        x["isaret"] = isaret.get(x["id"])
    return out


ASAMALAR = [("tedarik", "Tedarik & numune"), ("marka", "Marka & içerik"), ("magaza", "Mağaza & sosyal"),
            ("reklam", "Reklam hazırlığı"), ("test", "Reklam testi"), ("olcek", "Analiz & ölçek")]


def asama(p: Proje) -> str:
    ok = p.onayli
    if not ok("tedarik"):
        return "tedarik"
    if not (ok("marka") and ok("icerik") and ok("gorsel")):
        return "marka"
    if not (ok("magaza") and ok("instagram")):
        return "magaza"
    if not (ok("kreatif") and ok("reklam")):
        return "reklam"
    if not p.oku("analiz"):
        return "test"
    return "olcek"


# ---------------------------------------------------------------- arka plan işleri
IS: dict[str, dict] = {}
KILIT = threading.Lock()


def is_baslat(baslik: str, komut: list[str], cwd: Path, anahtar: str) -> dict:
    with KILIT:
        for i in IS.values():
            if i["anahtar"] == anahtar and i["durum"] == "calisiyor":
                raise HTTPException(409, f"Bu iş zaten çalışıyor: {i['baslik']}")
        ISLER.mkdir(exist_ok=True)
        iid = uuid.uuid4().hex[:10]
        log = ISLER / f"{iid}.log"
        kayit = {"id": iid, "baslik": baslik, "anahtar": anahtar, "durum": "calisiyor", "kod": None,
                 "baslangic": dt.datetime.now().isoformat(timespec="seconds"), "bitis": None, "log": str(log)}
        IS[iid] = kayit

    def calis():
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1", "NO_COLOR": "1"}
        with log.open("w", encoding="utf-8") as fh:
            try:
                r = subprocess.run(komut, cwd=cwd, stdout=fh, stderr=subprocess.STDOUT, env=env,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                kayit["kod"] = r.returncode
            except Exception as e:  # noqa: BLE001
                fh.write(f"\n{type(e).__name__}: {e}\n")
                kayit["kod"] = -1
        kayit["durum"] = "bitti" if kayit["kod"] == 0 else "hata"
        kayit["bitis"] = dt.datetime.now().isoformat(timespec="seconds")

    threading.Thread(target=calis, daemon=True).start()
    return kayit


ANSI = re.compile(r"\x1b\[[0-9;]*m")


def is_gorunum(i: dict, satir: int = 200) -> dict:
    try:
        metin = Path(i["log"]).read_text(encoding="utf-8", errors="replace")
    except OSError:
        metin = ""
    satirlar = [s for s in ANSI.sub("", metin).splitlines() if "[apify." not in s]
    return {k: v for k, v in i.items() if k != "log"} | {"cikti": "\n".join(satirlar[-satir:])}


# ---------------------------------------------------------------- API
@app.get("/", response_class=HTMLResponse)
def index():
    return (PANEL / "index.html").read_text(encoding="utf-8")


@app.get("/api/genel")
def genel():
    projeler = []
    for d in sorted(PROJELER.glob("*/urun.json")):
        try:
            projeler.append(proje_ozeti(Proje(d.parent)))
        except Exception:  # noqa: BLE001
            continue
    projeler.sort(key=lambda x: x["son_islem"] or "", reverse=True)
    ar = arastirmalar()
    gd = _json(GUNLUK / "durum.json") or {}
    try:
        kelimeler = [s.split("|")[0].strip() for s in (ARASTIRMA / "gunluk-kelimeler.txt").read_text(encoding="utf-8").splitlines()
                     if s.strip() and not s.startswith("#")]
    except OSError:
        kelimeler = []
    gunler = sorted(GUNLUK.glob("????-??-??.md"), reverse=True)
    return {
        "projeler": projeler,
        "arastirma_sayisi": len(ar),
        "karar_dagilimi": {k: sum(1 for x in ar if x["karar"] == k) for k in ("TESTE AL", "İYİLEŞTİR", "EKSİK VERİ", "ELE")},
        "son_arastirmalar": ar[:6],
        "gunluk": {"son": gd.get("son"), "sonraki_kelime": kelimeler[gd.get("sira", 0) % len(kelimeler)] if kelimeler else None,
                   "kelime_sayisi": len(kelimeler), "gunler": [g.stem for g in gunler[:30]]},
        "anahtarlar": {k: bool(os.getenv(k)) for k in ANAHTARLAR},
        "isler": [is_gorunum(i, 3) for i in sorted(IS.values(), key=lambda x: x["baslangic"], reverse=True)[:8]],
    }


@app.get("/api/arastirmalar")
def api_arastirmalar():
    return arastirmalar()


@app.get("/api/arastirma-rapor/{ad}")
def arastirma_rapor(ad: str):
    yol = _guvenli(CIKTI, ad)
    if yol.suffix != ".md":
        raise HTTPException(400, "Sadece rapor")
    return {"md": yol.read_text(encoding="utf-8")}


@app.get("/api/gunluk/{gun}")
def gunluk_gun(gun: str):
    if gun == "adaylar":
        yol = GUNLUK / "adaylar.md"
    elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", gun):
        yol = GUNLUK / f"{gun}.md"
    else:
        raise HTTPException(400, "Geçersiz gün")
    if not yol.exists():
        return {"md": "Henüz kayıt yok."}
    return {"md": yol.read_text(encoding="utf-8")}


@app.get("/api/proje/{ad}")
def proje(ad: str):
    p = _proje(ad)
    sk = p.veri.get("skor") or {}
    marka = p.oku("marka") or {}
    try:
        f = p.fiyat()
    except Exception:  # noqa: BLE001
        f = {}
    dosyalar = []
    for alt in ("gorseller", "magaza", "instagram", "yasal", "operasyon"):
        for x in sorted((p.yol / alt).rglob("*")) if (p.yol / alt).exists() else []:
            if x.is_file() and "kaynak" not in x.parts:
                dosyalar.append({"yol": x.relative_to(p.yol).as_posix(), "tur": x.suffix.lower().lstrip("."), "klasor": alt})
    kaynak = p.durum.get("kaynak")
    return {
        **proje_ozeti(p),
        "urun": {k: p.urun.get(k) for k in ("baslik", "link", "fiyat", "puan", "satis", "magaza")},
        "skor": {"karar": sk.get("karar"), "toplam": sk.get("toplam"), "kriterler": sk.get("kriterler"),
                 "kirmizi_bayraklar": sk.get("kirmizi_bayraklar"), "eksik_kriter": sk.get("eksik_kriter")},
        "fiyat": {**{k: f.get(k) for k in ("fiyat", "secenek", "birim_kar", "marj_yuzde", "basabas_roas", "basabas_cpa")},
                  "hedef_cpa": f.get("hedef_cpa") or f.get("reklam_payi")},
        "secimler": p.durum.get("secimler", {}),
        "marka_isimleri": [{"isim": x.get("isim"), "com": x.get("com") or x.get("com_durumu"), "aciklama": x.get("anlam") or x.get("neden")}
                           for x in marka.get("isimler", [])],
        "adimlar_detay": [{"anahtar": "arastirma", "no": 1, "ad": ADIM_ADI["arastirma"], "aciklama": ADIM_ACIKLAMA["arastirma"],
                           "durum": "tamam", "zaman": None, "onay_metni": None, "eksikler": [],
                           "rapor": bool(kaynak and (KOK / kaynak).with_suffix(".md").exists())}]
                         + [adim_durumu(p, a) for a in ADIMLAR],
        "dosyalar": dosyalar,
        "kaynak_json": Path(kaynak).name if kaynak and (CIKTI / Path(kaynak).name).exists() else None,
    }


@app.get("/api/proje/{ad}/rapor/{adim}")
def proje_rapor(ad: str, adim: str):
    p = _proje(ad)
    if adim == "arastirma":
        k = p.durum.get("kaynak")
        yol = (KOK / k).with_suffix(".md") if k else None
    elif adim in ADIMLAR:
        yol = p.dosya(adim, "md")
    else:
        raise HTTPException(404, "Adım yok")
    if not yol or not yol.exists():
        raise HTTPException(404, "Rapor henüz yok")
    return {"md": yol.read_text(encoding="utf-8")}


@app.get("/dosya/{ad}/{yol:path}")
def dosya(ad: str, yol: str):
    p = _proje(ad)
    return FileResponse(_guvenli(p.yol, yol))


class CalistirIstek(BaseModel):
    adimlar: list[str] = []


@app.post("/api/proje/{ad}/calistir")
def calistir(ad: str, istek: CalistirIstek):
    p = _proje(ad)
    for a in istek.adimlar:
        if a not in ADIMLAR or a == "analiz":
            raise HTTPException(400, f"Bu adım buradan çalıştırılamaz: {a}")
    baslik = f"{p.ad}: " + (", ".join(ADIM_ADI[a] for a in istek.adimlar) if istek.adimlar else "hazır tüm adımlar")
    return is_baslat(baslik, [PY, "-W", "ignore", "hat.py", "calistir", p.ad, *istek.adimlar], KOK, f"proje:{p.ad}")


class OnayIstek(BaseModel):
    adim: str
    isim: str | None = None


@app.post("/api/proje/{ad}/onayla")
def onayla(ad: str, istek: OnayIstek):
    p = _proje(ad)
    if istek.adim not in ADIMLAR or not ADIMLAR[istek.adim]["onay"]:
        raise HTTPException(400, "Bu adım onay istemiyor")
    if not p.oku(istek.adim):
        raise HTTPException(400, "Adım henüz çalıştırılmadı")
    if istek.adim == "marka":
        isim = (istek.isim or p.secim("isim") or "").strip()
        if not isim:
            raise HTTPException(400, "Marka onayı için isim seç")
        p.durum["secimler"]["isim"] = isim
    a = p.durum["adimlar"].setdefault(istek.adim, {})
    a["durum"] = "onaylandi"
    a["onay_zamani"] = dt.datetime.now().isoformat(timespec="minutes")
    p.kaydet_durum()
    return {"tamam": True}


@app.post("/api/proje/{ad}/onay-geri")
def onay_geri(ad: str, istek: OnayIstek):
    p = _proje(ad)
    a = p.durum["adimlar"].get(istek.adim)
    if not a or a.get("durum") != "onaylandi":
        raise HTTPException(400, "Onaylı değil")
    a["durum"] = "onay_bekliyor"
    a.pop("onay_zamani", None)
    p.kaydet_durum()
    return {"tamam": True}


SECILEBILIR = {"fiyat", "gunluk_butce", "set_butce", "set_sayisi", "yas_min", "yas_max", "test_saat", "tedarik_fiyati", "tedarik_kargo", "kargo_esigi", "hazirlik_gun"}


@app.post("/api/proje/{ad}/sec")
def sec(ad: str, degerler: dict):
    p = _proje(ad)
    for k, v in degerler.items():
        if k not in SECILEBILIR:
            raise HTTPException(400, f"Bu ayar değiştirilemez: {k}")
        if v in (None, ""):
            p.durum["secimler"].pop(k, None)
        else:
            try:
                float(str(v).replace(",", "."))
            except ValueError:
                raise HTTPException(400, f"{k} sayı olmalı")
            p.durum["secimler"][k] = str(v).replace(",", ".")
    p.kaydet_durum()
    return p.durum["secimler"]


@app.post("/api/proje/{ad}/analiz")
async def analiz(ad: str, dosya: UploadFile = File(...)):
    p = _proje(ad)
    if not p.oku("reklam"):
        raise HTTPException(400, "Önce reklam planı oluşturulmalı")
    hedef = p.yol / "analiz-girdi"
    hedef.mkdir(exist_ok=True)
    yol = hedef / f"meta-{dt.datetime.now():%Y%m%d-%H%M%S}.csv"
    yol.write_bytes((await dosya.read())[:5_000_000])
    return is_baslat(f"{p.ad}: reklam analizi", [PY, "-W", "ignore", "hat.py", "calistir", p.ad, "analiz", "--csv", str(yol)],
                     KOK, f"proje:{p.ad}")


class ArastirIstek(BaseModel):
    link: str
    kelime: str = ""
    trendyol: bool = True


@app.post("/api/arastir")
def arastir(istek: ArastirIstek):
    link = istek.link.strip()
    if not re.search(r"aliexpress\.[a-z.]+/item/\d+|^\d{10,}$", link):
        raise HTTPException(400, "Geçerli bir AliExpress ürün linki gir (…aliexpress.com/item/123….html)")
    komut = [PY, "-W", "ignore", "arastir.py", "urun", link]
    if istek.kelime.strip():
        komut += ["--kelime", istek.kelime.strip()]
    if istek.trendyol:
        komut.append("--trendyol")
    return is_baslat(f"Araştırma: {istek.kelime or link[-30:]}", komut, ARASTIRMA, f"arastir:{link}")


class YeniIstek(BaseModel):
    json: str
    ad: str = ""
    zorla: bool = False


@app.post("/api/yeni")
def yeni(istek: YeniIstek):
    kaynak = _guvenli(CIKTI, istek.json)
    ad = ortak.slug(istek.ad) if istek.ad.strip() else ""
    komut = [PY, "-W", "ignore", "hat.py", "yeni", str(kaynak.relative_to(KOK))] + (["--ad", ad] if ad else [])
    if istek.zorla:
        komut.append("--zorla")
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run(komut, cwd=KOK, capture_output=True, text=True, encoding="utf-8", env=env,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if r.returncode != 0:
        raise HTTPException(400, (r.stderr or r.stdout).strip()[-400:])
    m = re.search(r"projeler[\\/]+([a-z0-9-]+)", r.stdout)
    return {"proje": m.group(1) if m else None, "cikti": r.stdout}


SINYAL = CIKTI / "sinyal"


@app.get("/api/sinyaller")
def sinyaller():
    """Son sinyal çalıştırmalarındaki ürünler (aynı ASIN'in en yenisi), karar sırasına göre."""
    son: dict[str, dict] = {}
    calismalar = []
    for f in sorted(SINYAL.glob("sinyal-*.json")):
        v = _json(f) or {}
        calismalar.append({"zaman": v.get("zaman"), "kategoriler": v.get("kategoriler"), "adet": len(v.get("urunler") or []),
                           "notlar": v.get("notlar") or []})
        for u in v.get("urunler") or []:
            u["zaman"] = v.get("zaman")
            u["usd_tl"] = v.get("usd_tl")
            son[u.get("asin") or u.get("title")] = u
    sira = {"TESTE AL": 0, "İYİLEŞTİR": 1, "EKSİK VERİ": 2, "ELE": 3}
    urunler = sorted(son.values(), key=lambda u: (sira.get(u.get("karar"), 9), -(len(u.get("acilar") or []))))
    d = _json(SINYAL / "durum.json") or {}
    return {"urunler": urunler, "calismalar": calismalar[-10:][::-1], "son": d.get("son")}


@app.post("/api/sinyal-calistir")
def sinyal_calistir():
    return is_baslat("Ürün sinyali (Amazon → Trendyol)", [PY, "-W", "ignore", "sinyal.py"], ARASTIRMA, "sinyal")


@app.post("/api/gunluk-calistir")
def gunluk_calistir():
    return is_baslat("Günlük ürün taraması", [PY, "-W", "ignore", "gunluk.py"], ARASTIRMA, "gunluk")


@app.get("/api/is/{iid}")
def is_durum(iid: str):
    if iid not in IS:
        raise HTTPException(404, "İş yok")
    return is_gorunum(IS[iid])

# ---------------------------------------------------------------- v2: keşif, hesap, veri, ayarlar
_ONBELLEK: dict[str, tuple[float, object]] = {}


def _onbellek(anahtar: str, sure: float, f):
    import time
    t, v = _ONBELLEK.get(anahtar, (0, None))
    if time.time() - t > sure:
        try:
            v = f()
        except Exception:  # noqa: BLE001
            v = None
        _ONBELLEK[anahtar] = (time.time(), v)
    return v


def apify_durum() -> dict:
    def oku():
        import rakipler
        from apify_client import ApifyClient
        if not os.getenv("APIFY_TOKEN"):
            return None
        return rakipler._aylik_harcama(ApifyClient(os.getenv("APIFY_TOKEN")))
    h = _onbellek("apify", 600, oku)
    return {"harcanan": h, "butce": float(os.getenv("APIFY_AYLIK_BUTCE_USD", "5")),
            "gunluk_tavan": float(os.getenv("GUNLUK_APIFY_TAVAN_USD", "3"))}


def gorev_durumu() -> dict | None:
    def oku():
        ps = ("$i = Get-ScheduledTask -TaskName 'Eticaret Gunluk Urun Taramasi' -ErrorAction Stop | Get-ScheduledTaskInfo; "
              "[pscustomobject]@{sonraki=$i.NextRunTime.ToString('s'); son=$i.LastRunTime.ToString('s'); sonuc=$i.LastTaskResult} | ConvertTo-Json")
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=20,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None
    return _onbellek("gorev", 300, oku)


@app.get("/api/ozet")
def ozet():
    g = genel()
    ar = arastirmalar()
    gorevler = []
    for p in g["projeler"]:
        for a in p["onay_bekleyen"]:
            gorevler.append({"tur": "onay", "metin": f"{a} onayını ver", "proje": p["ad"], "marka": p["marka"] or p["ad"]})
        for a in p["hazir"]:
            gorevler.append({"tur": "hazir", "metin": f"{a} adımını çalıştır", "proje": p["ad"], "marka": p["marka"] or p["ad"]})
    for x in ar:
        if x["karar"] == "TESTE AL" and not x["proje"] and x["isaret"] != "red":
            gorevler.append({"tur": "aday", "metin": "TESTE AL çıktı: projeye çevir ya da reddet", "json": x["json"],
                             "marka": (x["baslik"] or "")[:48]})
    return {**g, "gorevler": gorevler, "asamalar": ASAMALAR, "apify": apify_durum(), "gorev": gorev_durumu(),
            "adaylar": [x for x in ar if x["karar"] in ("TESTE AL", "İYİLEŞTİR") and x["isaret"] != "red" and not x["proje"]][:6]}


@app.get("/api/aday/{ad}")
def aday(ad: str):
    j = _guvenli(CIKTI, ad)
    v = _json(j)
    if not v or "urun" not in v:
        raise HTTPException(404, "Kayıt yok")
    oz = _aday_ozeti(j, v)
    u = v["urun"]
    an = v.get("rakip_analizi") or {}
    tr = (v.get("trendler") or {}).get("kelimeler") or {}
    projeler = {str(((_json(d) or {}).get("urun") or {}).get("id")): d.parent.name for d in PROJELER.glob("*/urun.json")}
    return {**oz, "isaret": veri_oku()["isaretler"].get(oz["id"]), "proje": projeler.get(oz["id"]),
            "skor": v.get("skor"), "fiyat_secenekleri": v.get("fiyat_secenekleri"), "maliyet": v.get("maliyet"),
            "riskler": v.get("riskler"), "iade": v.get("iade"), "kargo_riski": v.get("kargo_riski"),
            "rakip_ozet": (v.get("trendyol") or {}).get("ozet"), "trend": tr,
            "analiz": {k: an.get(k) for k in ("sikayetler", "begeniler", "farklilasma", "neden_benden", "ayrisma_puani", "ayrisma_gerekce")},
            "urun": {k: u.get(k) for k in ("magaza", "stok", "puan_sayisi", "kargo", "video")},
            "gorseller": (u.get("gorseller") or [])[:8]}


class IsaretIstek(BaseModel):
    isaret: str | None = None


@app.post("/api/aday-isaret/{pid}")
def aday_isaret(pid: str, istek: IsaretIstek):
    if not re.fullmatch(r"\d{5,}", pid) or istek.isaret not in (None, "favori", "red"):
        raise HTTPException(400, "Geçersiz")
    v = veri_oku()
    if istek.isaret:
        v["isaretler"][pid] = istek.isaret
    else:
        v["isaretler"].pop(pid, None)
    veri_yaz(v)
    return {"tamam": True}


@app.post("/api/yeniden-puanla/{ad}")
def yeniden_puanla(ad: str):
    j = _guvenli(CIKTI, ad)
    return is_baslat(f"Yeniden puanlama: {ad[:30]}", [PY, "-W", "ignore", "arastir.py", "skorla", str(j)], ARASTIRMA, f"skorla:{ad}")


class HesapIstek(BaseModel):
    fiyat: float
    maliyet: float | None = None
    json: str | None = None
    proje: str | None = None
    kanal: str = "site"
    iade_orani: float | None = None
    reklam_payi: float | None = None
    indirim: float = 0.0


@app.post("/api/hesapla")
def hesapla(h: HesapIstek):
    import hesap
    if h.kanal not in hesap.KANALLAR:
        raise HTTPException(400, "Kanal yok")
    if not (0 < h.fiyat < 1_000_000) or not (0 <= h.indirim < 0.9):
        raise HTTPException(400, "Fiyat/indirim geçersiz")
    maliyet = None
    if h.json:
        v = _json(_guvenli(CIKTI, h.json)) or {}
        maliyet = (v.get("maliyet") or {}).get("stok")
    if h.proje:
        maliyet = _proje(h.proje).maliyet()
    if h.maliyet is not None and h.maliyet >= 0:
        # Elle girilen değer: yerli toptancıdan KDV dahil alış fiyatı (+ kargo ve koli varsayımları eklenir)
        maliyet = hesap.birim_maliyet(h.maliyet, 0, "yerli")
    if not maliyet:
        raise HTTPException(400, "Maliyet gir ya da araştırılmış bir ürün seç")
    ek = {}
    if h.iade_orani is not None:
        ek["iade_orani"] = h.iade_orani
    if h.reklam_payi is not None:
        ek["reklam_payi"] = h.reklam_payi
    a = hesap.ayarlar(h.kanal, ek)
    satis = round(h.fiyat * (1 - h.indirim), 2)
    r = hesap.fiyat_analizi(satis, maliyet, a)
    mf = hesap.minimum_fiyat(maliyet, a)
    kdv = round(satis - r["kdv_haric"], 2)
    dagilim = [("Ürün, kargo, koli", r["net_maliyet"]), ("KDV (net)", round(kdv - r["mahsup_kdv"], 2)), ("Komisyon", r["komisyon"]),
               ("Beklenen iade", r["iade_maliyeti"]), ("Reklam", r["reklam_payi"]), ("Net kâr", r["birim_kar"])]

    def paket(n, oran):
        f = hesap.psikolojik(h.fiyat * n * oran * (1 - h.indirim))
        m = {"toplam": maliyet["toplam"] * n - maliyet["kalemler"].get("yurtici_kargo", 0) * (n - 1)
             - maliyet["kalemler"].get("paketleme", 0) * (n - 1), "kalemler": maliyet["kalemler"]}
        return {"fiyat": f, **{k: v for k, v in hesap.fiyat_analizi(f, m, a).items() if k in ("birim_kar", "marj_yuzde")}}
    return {**r, "satis": satis, "kdv": kdv, "maliyet": maliyet, "min_fiyat": None if mf == float("inf") else hesap.psikolojik(mf),
            "ayarlar": a, "dagilim": [{"ad": x, "tl": round(y, 2)} for x, y in dagilim],
            "paketler": {"2": paket(2, 0.85), "3": paket(3, 0.75)}}


def _csv(yol: Path) -> list[dict]:
    import csv
    if not yol.exists():
        return []
    ham = yol.read_text(encoding="utf-8-sig")
    if not ham.strip():
        return []
    ilk = ham.splitlines()[0]
    ayr = ";" if ilk.count(";") >= ilk.count(",") else ","
    return list(csv.DictReader(ham.splitlines(), delimiter=ayr))


@app.get("/api/proje/{ad}/veri")
def proje_veri(ad: str):
    p = _proje(ad)
    an = p.oku("analiz") or {}
    rk = (p.oku("reklam") or {}).get("plan") or {}
    return {"analiz": {"setler": an.get("setler") or [], "toplam": an.get("toplam"), "saat": an.get("saat"), "kurallar": an.get("kurallar")},
            "reklam": {"butce": rk.get("butce"), "kurallar": rk.get("kurallar"),
                       "setler": [{"ad": s["ad"], "butce": s["gunluk_butce_tl"]} for s in rk.get("setler", [])]},
            "instagram": _csv(p.yol / "instagram" / "icerik-takvimi.csv"),
            "haftalik": _csv(p.yol / "operasyon" / "haftalik.csv")}


KELIME_DOSYA = ARASTIRMA / "gunluk-kelimeler.txt"


@app.get("/api/kelimeler")
def kelimeler_oku():
    satirlar = KELIME_DOSYA.read_text(encoding="utf-8").splitlines() if KELIME_DOSYA.exists() else []
    out = []
    for s in satirlar:
        if s.strip() and not s.startswith("#"):
            en, _, tr = s.partition("|")
            out.append({"en": en.strip(), "tr": (tr or en).strip()})
    gd = _json(GUNLUK / "durum.json") or {}
    return {"liste": out, "sira": gd.get("sira", 0) % max(1, len(out)), "son": gd.get("son"), "gorev": gorev_durumu()}


class KelimeIstek(BaseModel):
    liste: list[dict]


@app.put("/api/kelimeler")
def kelimeler_yaz(istek: KelimeIstek):
    temiz = []
    for k in istek.liste[:200]:
        en = re.sub(r"[|#\r\n]", " ", str(k.get("en", ""))).strip()[:80]
        tr = re.sub(r"[|#\r\n]", " ", str(k.get("tr", ""))).strip()[:80]
        if en:
            temiz.append(f"{en} | {tr or en}")
    if not temiz:
        raise HTTPException(400, "Liste boş olamaz")
    eski = KELIME_DOSYA.read_text(encoding="utf-8").splitlines() if KELIME_DOSYA.exists() else []
    yorum = [s for s in eski if s.startswith("#")]
    KELIME_DOSYA.write_text("\n".join(yorum + temiz) + "\n", encoding="utf-8")
    return kelimeler_oku()


@app.get("/api/ayarlar")
def ayarlar_oku():
    import hesap
    return {"ayarlar": hesap.AYARLAR, "kanallar": hesap.KANALLAR, "son_kontrol": hesap.AYARLAR_SON_KONTROL,
            "apify": apify_durum(), "gorev": gorev_durumu(), "anahtarlar": {k: bool(os.getenv(k)) for k in ANAHTARLAR}}


@app.get("/app.js")
def app_js():
    return FileResponse(PANEL / "app.js", media_type="text/javascript")


@app.get("/app.css")
def app_css():
    return FileResponse(PANEL / "app.css", media_type="text/css")



# ---------------------------------------------------------------- Shopify (okuma) + anahtar formu + taslak ürün
import shopify_baglanti as _shopify  # noqa: E402

ENV_DOSYA = KOK / ".env"
ANAHTAR_KURAL = {
    "SHOPIFY_MAGAZA": (r"^[a-z0-9][a-z0-9-]*\.myshopify\.com$", "xxx.myshopify.com biçiminde olmalı"),
    "SHOPIFY_ADMIN_TOKEN": (r"^shpat_[A-Za-z0-9]{20,}$", "shpat_ ile başlayan Admin API erişim anahtarı olmalı"),
    "META_ERISIM_TOKENI": (r"^[A-Za-z0-9_\-]{30,}$", "Meta sistem kullanıcısı erişim anahtarı"),
    "META_REKLAM_HESABI": (r"^act_\d{5,}$", "act_ ile başlayan reklam hesabı numarası"),
    "META_PIXEL_ID": (r"^\d{5,}$", "sadece rakam"),
}


class AnahtarIstek(BaseModel):
    anahtar: str
    deger: str


@app.post("/api/anahtar")
def anahtar_kaydet(istek: AnahtarIstek):
    """Anahtarı eticaret/.env dosyasına yazar (yalnızca bu bilgisayar). Değer hiçbir yanıtta geri dönmez."""
    kural = ANAHTAR_KURAL.get(istek.anahtar)
    deger = (istek.deger or "").strip()
    if not kural:
        raise HTTPException(400, "Bu anahtar panelden eklenemez")
    if istek.anahtar == "SHOPIFY_MAGAZA":
        deger = re.sub(r"^https?://", "", deger).strip("/").lower()
    if not re.fullmatch(kural[0], deger):
        raise HTTPException(400, f"Geçersiz değer: {kural[1]}")
    satirlar = ENV_DOSYA.read_text(encoding="utf-8").splitlines() if ENV_DOSYA.exists() else []
    satirlar = [x for x in satirlar if not x.startswith(istek.anahtar + "=")] + [f"{istek.anahtar}={deger}"]
    ENV_DOSYA.write_text("\n".join(satirlar) + "\n", encoding="utf-8")
    os.environ[istek.anahtar] = deger
    _shopify.temizle()
    return {"tamam": True, "anahtar": istek.anahtar, "shopify_bagli": _shopify.yapilandirildi()}


@app.get("/api/shopify")
def shopify_durum():
    if not _shopify.yapilandirildi():
        return {"bagli": False, "eksik": [k for k in ("SHOPIFY_MAGAZA", "SHOPIFY_ADMIN_TOKEN") if not os.getenv(k)]}
    try:
        return {"bagli": True, "magaza": _shopify.magaza()}
    except _shopify.ShopifyHata as e:
        return {"bagli": True, "hata": str(e)}


@app.get("/api/shopify/satis")
def shopify_satis(gun: int = 30):
    if gun not in (7, 30, 90):
        raise HTTPException(400, "gun 7, 30 ya da 90 olmalı")
    try:
        return _shopify.satis(gun)
    except _shopify.ShopifyHata as e:
        raise HTTPException(400, str(e))


@app.get("/api/shopify/urunler")
def shopify_urunler():
    try:
        return _shopify.urunler()
    except _shopify.ShopifyHata as e:
        raise HTTPException(400, str(e))


class TaslakIstek(BaseModel):
    onay: bool = False


@app.post("/api/proje/{ad}/shopify-taslak")
def shopify_taslak(ad: str, istek: TaslakIstek):
    """Ürünü Shopify'a TASLAK olarak gönderir (yayına almaz). Panelde ayrı onay ister."""
    p = _proje(ad)
    if not istek.onay:
        raise HTTPException(400, "Onay gerekli")
    if not _shopify.yapilandirildi():
        raise HTTPException(400, "Shopify bağlı değil: Mağaza sayfasından bağla")
    if not p.oku("magaza"):
        raise HTTPException(400, "Önce mağaza adımını çalıştır")
    return is_baslat(f"{p.ad}: Shopify'a taslak ürün", [PY, "-W", "ignore", "hat.py", "calistir", p.ad, "magaza", "--gonder"], KOK, f"proje:{p.ad}")

if __name__ == "__main__":
    port = int(os.getenv("PANEL_PORT", "8765"))
    print(f"E-ticaret paneli: http://127.0.0.1:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
