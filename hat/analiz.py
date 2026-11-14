"""10 · Analiz: Meta Reklam Yöneticisi CSV'sini (reklam seti düzeyi) okur, kapatma/ölçekleme kurallarını uygular.

  python hat.py calistir <proje> analiz --csv rapor.csv
Türkçe ve İngilizce dışa aktarma sütun adlarını tanır. Bütçe değişikliğini sen yaparsın; bu adım öneri üretir.
"""
from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

from ortak import Proje, tl

SUTUN = {  # alan: aranan parçalar (küçük harf, ilk eşleşen)
    "ad": ["reklam seti adı", "ad set name", "reklam seti", "ad set"],
    "harcama": ["harcanan tutar", "amount spent", "harcama", "spend"],
    "gosterim": ["gösterim", "impressions"],
    "tik": ["bağlantı tıklamaları", "link clicks", "tıklamalar (bağlantı)"],
    "lpv": ["açılış sayfası görüntülemeleri", "landing page views"],
    "atc": ["sepete eklemeler", "sepete ekleme", "adds to cart"],
    "ic": ["ödeme başlatmalar", "ödeme başlatma", "checkouts initiated"],
    "satis": ["satın almalar", "satın alma", "purchases"],
    "deger": ["satın alma dönüşüm değeri", "purchases conversion value", "dönüşüm değeri", "conversion value"],
}


def _sayi(x) -> float:
    if x in (None, ""):
        return 0.0
    s = str(x).strip().replace("₺", "").replace("TRY", "").replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def oku(yol: Path) -> list[dict]:
    ham = yol.read_text(encoding="utf-8-sig")
    ayr = ";" if ham.splitlines()[0].count(";") > ham.splitlines()[0].count(",") else ","
    satirlar = list(csv.DictReader(ham.splitlines(), delimiter=ayr))
    if not satirlar:
        return []
    basliklar = list(satirlar[0].keys())
    harita = {}
    for alan, adaylar in SUTUN.items():
        for a in adaylar:
            b = next((h for h in basliklar if a in h.lower() and not (alan == "satis" and ("değer" in h.lower() or "value" in h.lower() or "maliyet" in h.lower() or "cost" in h.lower()))), None)
            if b:
                harita[alan] = b
                break
    out = []
    for r in satirlar:
        if not r.get(harita.get("ad", ""), "").strip():
            continue
        out.append({"ad": r[harita["ad"]].strip(), **{k: _sayi(r.get(v)) for k, v in harita.items() if k != "ad"}})
    return out


def degerlendir(s: dict, kural: dict, saat: float) -> tuple[str, str]:
    h, atc, satis = s.get("harcama", 0), s.get("atc", 0), s.get("satis", 0)
    roas = s["roas"]
    be = kural.get("basabas_roas") or 99
    if kural.get("kapat_0_atc_tl") and h >= kural["kapat_0_atc_tl"] and atc == 0:
        return "KAPAT", f"{tl(h)} harcadı, 0 sepete ekleme (kural 1)"
    if kural.get("kapat_0_satis_tl") and h >= kural["kapat_0_satis_tl"] and satis == 0:
        return "KAPAT", f"{tl(h)} harcadı, 0 satış (kural 2)"
    if saat >= 48 and roas < be:
        return "KAPAT", f"48 saat geçti, ROAS {roas:.2f} < başabaş {be} (kural 3)"
    if saat >= 48 and satis >= 2 and roas >= be * 1.2:
        return "ÖLÇEKLE", f"ROAS {roas:.2f} ≥ başabaşın 1,2 katı; bütçeyi %15–20 artır (24–48 saatte bir)"
    if roas >= be and satis >= 1:
        return "İZLE (iyi)", f"ROAS {roas:.2f} ≥ başabaş; 48 saati ve en az 2 satışı bekle"
    return "İZLE", "henüz karar için yeterli veri yok"


def teshis(s: dict) -> list[str]:
    n = []
    if s["ctr"] is not None and s["ctr"] < 1.5:
        n.append(f"CTR %{s['ctr']:.2f} < %1,5 → kanca (ilk 3 sn) zayıf")
    if s["lpv_orani"] is not None and s["lpv_orani"] < 80:
        n.append(f"LPV/tık %{s['lpv_orani']:.0f} < %80 → site yavaş açılıyor")
    if s.get("tik", 0) >= 100 and s.get("atc", 0) == 0:
        n.append("100+ tık, 0 sepete ekleme → ürün sayfası / fiyat / güven unsurları")
    if s.get("atc", 0) >= 5 and s.get("satis", 0) == 0:
        n.append("sepete ekleme var, satış yok → ödeme adımı, kargo ücreti sürprizi, güven")
    return n


def calistir(p: Proje, args=None):
    kaynak = getattr(args, "csv", None)
    if not kaynak:
        raise RuntimeError("CSV gerekli: python hat.py calistir <proje> analiz --csv <Reklam Yöneticisi dışa aktarımı>")
    rk = p.oku("reklam") or {}
    kural = (rk.get("plan") or {}).get("kurallar") or {}
    bas = p.secim("test_baslangic")
    saat = (dt.datetime.now() - dt.datetime.fromisoformat(bas)).total_seconds() / 3600 if bas else 0
    if p.secim("test_saat"):
        saat = float(p.secim("test_saat"))
    setler = oku(Path(kaynak))
    for s in setler:
        h, g, t = s.get("harcama", 0), s.get("gosterim", 0), s.get("tik", 0)
        s["ctr"] = t / g * 100 if g else None
        s["cpc"] = h / t if t else None
        s["lpv_orani"] = s.get("lpv", 0) / t * 100 if t and "lpv" in s else None
        s["cpa"] = h / s["satis"] if s.get("satis") else None
        s["roas"] = s.get("deger", 0) / h if h else 0
        s["karar"], s["neden"] = degerlendir(s, kural, saat)
        s["teshis"] = teshis(s)
    top = {k: sum(s.get(k, 0) for s in setler) for k in ("harcama", "satis", "deger", "atc")}
    top["roas"] = top["deger"] / top["harcama"] if top["harcama"] else 0
    kazanan = [s for s in setler if s["karar"].startswith("ÖLÇEKLE")]
    md = [f"# Reklam analizi — {dt.datetime.now():%d.%m.%Y %H:%M}", "",
          f"Test başlangıcından bu yana ~{saat:.0f} saat · başabaş ROAS {kural.get('basabas_roas')} · hedef CPA {tl(kural.get('hedef_cpa_tl'))}", "",
          f"**Toplam:** harcama {tl(top['harcama'])} · {top['satis']:.0f} satış · ciro {tl(top['deger'])} · ROAS {top['roas']:.2f}", "",
          "| Set | Harcama | CTR | CPC | ATC | Satış | CPA | ROAS | Karar | Neden |", "|---|---|---|---|---|---|---|---|---|---|"]
    for s in setler:
        ctr = "-" if s["ctr"] is None else f"%{s['ctr']:.2f}"
        md.append(f"| {s['ad']} | {tl(s.get('harcama'))} | {ctr} | "
                  f"{tl(s['cpc'])} | {s.get('atc', 0):.0f} | {s.get('satis', 0):.0f} | {tl(s['cpa'])} | {s['roas']:.2f} | "
                  f"**{s['karar']}** | {s['neden']} |")
    md += ["", "## Teşhis", ""]
    md += [f"- **{s['ad']}:** " + "; ".join(s["teshis"]) for s in setler if s["teshis"]] or ["- Belirgin huni sorunu yok."]
    md += ["", "## Sonraki adım", ""]
    if len(kazanan) >= 2:
        md.append(f"- {len(kazanan)} kazanan set var → en iyi 3–4 reklamla **CBO (Advantage kampanya bütçesi)** kampanyası aç; "
                  "kazanan ABO setlerini %15–20 artırarak sürdür.")
    elif kazanan:
        md.append("- 1 kazanan: bütçesini 24–48 saatte bir %15–20 artır; kapanan setlerin yerine kazanan açıdan yeni hook'larla set aç.")
    else:
        md.append("- Kazanan yok: kapatılan setlerin yerine kreatif adımından yeni açılar dene; CTR düşükse hook, ATC yoksa ürün sayfası/teklif.")
    p.yaz("analiz", {"saat": saat, "kurallar": kural, "setler": setler, "toplam": top, "kaynak": str(kaynak)}, md)
