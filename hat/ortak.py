"""Hattın ortak altyapısı: proje klasörü, adım durumu, onay kapıları, Gemini (metin + görsel).

Her ürün bir proje: eticaret/projeler/<slug>/
  urun.json        araştırma modülünün çıktısı (skor, fiyat, rakip analizi dahil)
  durum.json       adımların durumu, onaylar ve seçimler
  NN-<adim>.json   adım çıktısı (makine için)
  NN-<adim>.md     adım raporu (insan için)
"""
from __future__ import annotations

import base64
import datetime as dt
import json
import mimetypes
import os
import re
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

KOK = Path(__file__).resolve().parent.parent          # eticaret/
PROJELER = KOK / "projeler"
OZETLER = KOK / "kaynaklar" / "ozetler"
sys.path.insert(0, str(KOK / "urun-arastirma"))
for e in (KOK / ".env", KOK / "urun-arastirma" / ".env"):
    if e.exists():
        load_dotenv(e)

import gemini as _gm  # noqa: E402  (urun-arastirma/gemini.py)

# Sıra, ön koşul (onaylanmış olması gereken adımlar) ve adımın kendisinin insan onayı isteyip istemediği
ADIMLAR = {
    "tedarik":   {"no": 2, "once": [], "onay": "Numune sipariş edildi, kalite ve teslim süresi kontrol edildi"},
    "marka":     {"no": 3, "once": [], "onay": "Marka adı seçildi (--secim isim=...) ve domain/IG elle kontrol edildi"},
    "icerik":    {"no": 4, "once": ["marka"], "onay": None},
    "gorsel":    {"no": 5, "once": ["marka"], "onay": "Görseller ürünü gerçeğe uygun gösteriyor"},
    "magaza":    {"no": 6, "once": ["marka", "gorsel"], "onay": None, "gerekli": ["icerik"]},
    "instagram": {"no": 7, "once": ["marka", "gorsel"], "onay": None},
    "kreatif":   {"no": 8, "once": ["marka"], "onay": "Kreatif metinler kontrol edildi", "gerekli": ["icerik"]},
    "reklam":    {"no": 9, "once": ["tedarik", "kreatif"], "onay": None, "gerekli": ["magaza"]},
    "analiz":    {"no": 10, "once": [], "onay": None, "gerekli": ["reklam"]},
    "operasyon": {"no": 11, "once": [], "onay": None, "gerekli": ["icerik"]},
}

KURALLAR = (
    "Türkiye pazarı için Türkçe yaz. Sağlık/tedavi vaadi, abartılı kazanç vaadi, 'en iyi/1 numara' gibi kanıtsız "
    "üstünlük iddiası kullanma. Başka marka, ünlü ürün, otel veya kişi adı ve 'muadil/benzeri' iması kullanma. "
    "Teknik iddiaları SADECE verilen satıcı özelliklerinden al; bilinmeyeni uydurma, [doğrula] diye işaretle. "
    "Sahte yorum, sahte sayaç, sahte stok aciliyeti üretme. "
    "'Farklılaşma' ve 'neden benden alınır' maddeleri henüz yapılmamış PLANLARDIR: bunları kutu içeriği, aksesuar, ambalaj "
    "ya da ürün özelliği olarak mevcutmuş gibi yazma. 'Güvenli', 'zararsız', 'doğal', 'saf' gibi güvenlik/sağlık çağrışımlı "
    "nitelemeleri sertifika belgesi görülmeden kullanma. "
    "Kesin sonuç vaat etme: 'tüm/bütün tüyler', 'tamamen', 'anında', 'tek hareketle', 'iz bırakmaz', 'sonsuza kadar' yerine "
    "ölçülü ifade kullan (ör. 'tüyleri kolayca toplar'). Türkçe ekleri kesme işaretiyle yaz (3'ü 1 arada)."
)


def slug(s: str) -> str:
    tr = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    return re.sub(r"[^a-z0-9]+", "-", s.translate(tr).lower()).strip("-")[:40]


def tr_upper(s: str) -> str:
    """Türkçe büyük harf: i → İ, ı → I (str.upper() 'i'yi noktasız 'I' yapar)."""
    return s.replace("i", "İ").replace("ı", "I").upper()


def tl(x) -> str:
    if x is None:
        return "-"
    return f"{x:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")


def ozet(ad: str) -> str:
    """Bilgi bankasından ilgili kural özetini istemlere eklemek için okur."""
    p = OZETLER / f"{ad}.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


class Proje:
    def __init__(self, yol: Path):
        self.yol = Path(yol)
        if not (self.yol / "urun.json").exists():
            raise SystemExit(f"Proje bulunamadı: {self.yol}")
        self.veri = json.loads((self.yol / "urun.json").read_text(encoding="utf-8"))
        dp = self.yol / "durum.json"
        self.durum = json.loads(dp.read_text(encoding="utf-8")) if dp.exists() else {"adimlar": {}, "secimler": {}}

    # ---- erişim
    @property
    def urun(self) -> dict:
        return self.veri["urun"]

    @property
    def ad(self) -> str:
        return self.yol.name

    def kaydet_durum(self):
        (self.yol / "durum.json").write_text(json.dumps(self.durum, ensure_ascii=False, indent=1), encoding="utf-8")

    def dosya(self, adim: str, uzanti: str = "json") -> Path:
        return self.yol / f"{ADIMLAR[adim]['no']:02d}-{adim}.{uzanti}"

    def oku(self, adim: str) -> dict | None:
        p = self.dosya(adim)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def yaz(self, adim: str, veri: dict, md: list[str] | str):
        if adim in ("icerik", "instagram", "kreatif", "marka"):      # yapay zekâ metni: kesin sonuç vaadi kaldıysa uyar
            bul = abarti_tara({k: v for k, v in veri.items() if k not in ("yasal", "yasal_kontrol", "fiyat")})
            veri["abarti_uyarilari"] = bul
            if bul:
                satir = (["> ⚠ **Abartı / kesin sonuç vaadi bulundu (reklam reddi ve tüketici şikâyeti riski) — yayından önce düzelt:**"]
                         + [f"> - {x}" for x in bul[:12]] + [""])
                md = (md.split("\n") if isinstance(md, str) else list(md))
                md[2:2] = satir
        self.dosya(adim).write_text(json.dumps(veri, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        self.dosya(adim, "md").write_text(md if isinstance(md, str) else "\n".join(md), encoding="utf-8")
        a = self.durum["adimlar"].setdefault(adim, {})
        a.update({"durum": "onay_bekliyor" if ADIMLAR[adim]["onay"] else "tamam",
                  "zaman": dt.datetime.now().isoformat(timespec="minutes")})
        a.pop("onay_zamani", None)
        self.kaydet_durum()

    def onayli(self, adim: str) -> bool:
        a = self.durum["adimlar"].get(adim) or {}
        return a.get("durum") in ("tamam", "onaylandi")

    def secim(self, anahtar: str, varsayilan=None):
        return self.durum["secimler"].get(anahtar, varsayilan)

    # ---- sık kullanılan türetilmiş bilgiler
    def marka(self) -> dict:
        m = self.oku("marka") or {}
        isim = self.secim("isim")
        sec = next((x for x in m.get("isimler", []) if x["isim"].lower() == (isim or "").lower()), None)
        return {**(m.get("kimlik") or {}), "isim": isim or (sec or {}).get("isim") or "[MARKA]", "secilen": sec}

    def maliyet(self) -> dict:
        """Birim maliyet (stoklu). Tedarikçiden toptan fiyat geldiyse (secim tedarik_fiyati = adet başı ürün TL,
        isteğe bağlı tedarik_kargo = adet başı uluslararası kargo TL) araştırmadaki tek adet AliExpress fiyatının yerine geçer."""
        import hesap
        m = self.veri["maliyet"]["stok"]
        tf = self.secim("tedarik_fiyati")
        if not tf:
            return m
        a = {k: v for k, v in (self.veri.get("ayarlar") or {}).items() if k in hesap.AYARLAR}
        if self.secim("tedarik_kargo") not in (None, ""):          # tedarikçinin adet başı kargosu navlun varsayımının yerine geçer
            a["stok_navlun_tl"] = float(self.secim("tedarik_kargo"))
        yeni = hesap.birim_maliyet(float(tf), 0, "stok", a)
        yeni["kaynak"] = "tedarikçi toptan fiyatı"
        return yeni

    def fiyat(self) -> dict:
        """Satış fiyatı: seçim > dengeli seçenek (hedef marjı tutuyorsa) > minimum fiyat.
        Toptan fiyat girildiyse seçenekler o maliyetle yeniden hesaplanır."""
        import hesap
        sec = self.veri.get("fiyat_secenekleri") or []
        a = {**hesap.AYARLAR, **{k: v for k, v in (self.veri.get("ayarlar") or {}).items() if k in hesap.AYARLAR}}
        m = self.maliyet()
        if self.secim("tedarik_fiyati"):
            sec = hesap.fiyat_secenekleri(m, (self.veri.get("trendyol") or {}).get("ozet"), a)
        if self.secim("fiyat"):
            return {**hesap.fiyat_analizi(float(self.secim("fiyat")), m, a), "secenek": "elle seçilen"}
        d = next((s for s in sec if s["secenek"] == "dengeli" and s.get("hedefe_uygun")), None)
        mn = next((s for s in sec if s["secenek"].startswith("minimum")), None)
        return d or mn or (sec[0] if sec else {})

    def urun_ozeti(self, uzun: bool = False) -> str:
        u = self.urun
        oz = u.get("ozellikler") or {}
        s = [f"Ürün (AliExpress başlığı): {u.get('baslik')}",
             "Satıcının verdiği özellikler: " + "; ".join(f"{k}: {v}" for k, v in oz.items()),
             f"Varyantlar: {', '.join(str(v.get('ad')) for v in (u.get('varyantlar') or [])[:15])}"]
        if uzun:
            s.append("Satıcı açıklaması: " + " ".join((u.get("aciklama") or {}).get("metin") or [])[:2500])
        an = self.veri.get("rakip_analizi") or {}
        if an.get("sikayetler") is not None:
            s.append("Rakip/yorum şikâyetleri: " + "; ".join(f"{x['konu']} → {x['firsat']}" for x in an.get("sikayetler") or []))
            s.append("Beğenilenler: " + "; ".join(x["konu"] for x in an.get("begeniler") or []))
            s.append("Farklılaşma PLANI (henüz ürüne eklenmedi): " + "; ".join(f"{x['boyut']}: {x['oneri']}" for x in an.get("farklilasma") or []))
            if an.get("neden_benden"):
                s.append(f"Hedeflenen 'neden benden alınır' (PLAN): {an['neden_benden']}")
        riskler = [r["konu"] + (": " + r["detay"] if r.get("detay") else "") for r in self.veri.get("riskler") or []
                   if r["seviye"] in ("yuksek", "orta")]
        if riskler:
            s.append("Dikkat (kullanma/kaçın): " + " | ".join(riskler))
        f = self.fiyat()
        if f:
            s.append(f"Satış fiyatı: {f.get('fiyat')} TL; 2'li paket {f.get('paket_2')} TL, 3'lü paket {f.get('paket_3')} TL")
        return "\n".join(s)


def projeyi_bul(ad_ya_da_yol: str) -> Proje:
    p = Path(ad_ya_da_yol)
    if not p.exists():
        p = PROJELER / ad_ya_da_yol
    return Proje(p)


# ---------------------------------------------------------------- Gemini
ABARTI = re.compile(r"\b(tüm|bütün)\s+(tüy|kir|leke|toz)\w*|\btamamen\b|\banında\b|\btek hareketle\b|\biz bırakmaz\b|"
                    r"\bsonsuza kadar\b|%100\b|\bmucize\w*", re.I)


def _duzelt(x):
    """Model çıktısında: sayı eklerindeki düşen kesme işaretini düzelt (3ü 1 → 3'ü 1)."""
    if isinstance(x, str):
        return re.sub(r"\b(\d)(ü|u|ı|i)\s?(\d)\s(Arada|arada)", r"\1'\2 \3 \4", x)
    if isinstance(x, list):
        return [_duzelt(v) for v in x]
    if isinstance(x, dict):
        return {k: _duzelt(v) for k, v in x.items()}
    return x


def abarti_tara(veri) -> list[str]:
    """Metinlerde kalan kesin sonuç / abartı ifadelerini bulur (kurallara rağmen model üretirse rapora uyarı düşmek için)."""
    bulunan = []
    def gez(x):
        if isinstance(x, str):
            bulunan.extend(f"“{m.group(0)}” → {x[:90]}" for m in ABARTI.finditer(x))
        elif isinstance(x, list):
            for v in x: gez(v)
        elif isinstance(x, dict):
            for v in x.values(): gez(v)
    gez(veri)
    return bulunan


def metin_json(istem: str, sema: dict, sistem: str = "", sicaklik: float = 0.5) -> dict:
    return _duzelt(_gm.json_sor(istem, sema, sistem=(KURALLAR + " " + sistem).strip(), sicaklik=sicaklik))


def gemini_var() -> bool:
    return _gm.var_mi()


def gorsel_modeli() -> str:
    return os.getenv("GEMINI_GORSEL_MODEL", "gemini-3.1-flash-image")


def gorsel_uret(istem: str, referanslar: list[Path], cikti: Path, oran: str = "1:1", deneme: int = 3) -> Path:
    """Referans ürün fotoğraflarıyla görsel üretir/düzenler; PNG/JPEG olarak kaydeder."""
    anahtar = os.getenv("GEMINI_API_KEY")
    if not anahtar:
        raise RuntimeError("GEMINI_API_KEY tanımlı değil")
    parcalar = []
    for r in referanslar:
        mime = mimetypes.guess_type(str(r))[0] or "image/jpeg"
        parcalar.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(r.read_bytes()).decode()}})
    parcalar.append({"text": istem})
    govde = {"contents": [{"role": "user", "parts": parcalar}],
             "generationConfig": {"responseModalities": ["IMAGE", "TEXT"], "imageConfig": {"aspectRatio": oran}}}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{gorsel_modeli()}:generateContent"
    son = None
    for i in range(deneme):
        r = requests.post(url, json=govde, timeout=180, headers={"x-goog-api-key": anahtar})
        if r.status_code in (429, 500, 502, 503, 504):
            son = f"HTTP {r.status_code}: {r.text[:200]}"
            time.sleep(8 * (i + 1))
            continue
        if r.status_code != 200:
            raise RuntimeError(f"Gemini görsel HTTP {r.status_code}: {r.text[:300]}")
        for c in r.json().get("candidates", []):
            for p in c.get("content", {}).get("parts", []):
                d = p.get("inlineData") or p.get("inline_data")
                if d and d.get("data"):
                    uz = ".png" if "png" in d.get("mimeType", d.get("mime_type", "")) else ".jpg"
                    hedef = cikti.with_suffix(uz)
                    hedef.write_bytes(base64.b64decode(d["data"]))
                    return hedef
        son = "yanıtta görsel yok: " + json.dumps(r.json())[:300]
    raise RuntimeError(f"Görsel üretilemedi ({son})")


def indir(url: str, hedef: Path) -> Path | None:
    """Ürün görselini indirir (AliExpress CDN). Başarısızsa None."""
    if url.startswith("//"):
        url = "https:" + url
    try:
        r = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
            uz = ".png" if "png" in r.headers["content-type"] else ".jpg"
            hedef = hedef.with_suffix(uz)
            hedef.write_bytes(r.content)
            return hedef
    except requests.RequestException:
        pass
    return None
