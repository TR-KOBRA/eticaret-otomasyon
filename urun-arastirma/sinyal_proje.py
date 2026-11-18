"""Ürün sinyalini (sinyal.py kaydı) hattın beklediği araştırma JSON'una çevirir → `hat.py yeni` ile proje açılabilir.

  python sinyal_proje.py <asin>          # en yeni sinyal kaydından → cikti/urun-sinyal-<asin>-<zaman>.json (+ .md)

Maliyet: toptancı fiyatı henüz yok → alış tavanı (Trendyol medyanında %20 net bırakan en yüksek KDV dahil alış) TAHMİN olarak
kullanılır; tedarik adımında `hat.py sec <proje> tedarik_fiyati=<TL>` girilince her şey gerçek fiyatla yeniden hesaplanır.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

KOK = Path(__file__).parent
sys.path.insert(0, str(KOK))
import hesap  # noqa: E402
import rakipler  # noqa: E402

CIKTI = KOK / "cikti"
SINYAL = CIKTI / "sinyal"


def bul(asin: str) -> dict | None:
    """En yeni sinyal çalıştırmasındaki kaydı döndürür."""
    for f in sorted(SINYAL.glob("sinyal-*.json"), reverse=True):
        v = json.loads(f.read_text(encoding="utf-8"))
        for u in v.get("urunler") or []:
            if u.get("asin") == asin:
                return {**u, "_usd_tl": v.get("usd_tl") or 41, "_zaman": v.get("zaman")}
    return None


def _baslik(s: dict) -> str:
    """Türkçe ürün adı: Gemini'nin Türkçe arama kelimesi (urun_turu bazen İngilizce gelir)."""
    k = (s.get("tr_kelime") or s.get("urun_turu") or s.get("title") or "").strip()
    if not k:
        return "Ürün"
    ilk = "İ" if k[0] == "i" else k[0].upper()       # Türkçe büyük harf: i → İ
    return ilk + k[1:]


def tahmini_alis(s: dict) -> tuple[float, str]:
    if s.get("alis_tavani"):
        return float(s["alis_tavani"]), "alış tavanı (tahmin; toptancı fiyatı girilince güncellenir)"
    # Türkiye'de benzeri yoksa: Amazon fiyatının ~%35'i (ürettirme/toptan kaba tahmini)
    return round(float(s.get("price") or 10) * float(s.get("_usd_tl") or 41) * 0.35), "Amazon fiyatından kaba tahmin (toptancı fiyatı girilmeli)"


def donustur(s: dict) -> dict:
    a = hesap.ayarlar("site")
    alis, alis_kaynak = tahmini_alis(s)
    maliyet = hesap.birim_maliyet(alis, 0, "yerli", a)
    maliyet["kaynak"] = alis_kaynak
    ty = s.get("trendyol") or {}
    benzer = [{"ad": x.get("ad"), "fiyat": x.get("fiyat"), "degerlendirme": x.get("degerlendirme"), "favori": x.get("favori"),
               "link": x.get("link")} for x in ty.get("ornekler") or []]
    ozet = rakipler.ozet_hesapla(benzer) if benzer else {}
    if ozet and ty.get("medyan"):
        ozet["medyan"] = ty["medyan"]          # tüm benzerlerin medyanı (örnekler ilk 5)
    riskler = []
    dg = ty.get("doygunluk") or {}
    if dg.get("seviye") in ("kalabalik", "doymus"):
        riskler.append({"seviye": "yuksek" if dg["seviye"] == "doymus" else "orta", "konu": f"Trendyol'da {dg['guclu_rakip']} güçlü rakip",
                        "detay": f"en çok {dg.get('en_cok_yorum')} yorum; net farklılaşma gerekir"})
    rk = s.get("reklam") or {}
    if rk.get("seviye") in ("kalabalik", "doymus"):
        riskler.append({"seviye": "yuksek" if rk["seviye"] == "doymus" else "orta", "konu": f"Meta'da {rk.get('reklamveren')} reklamveren",
                        "detay": "farklı pazarlama açısı/teklif şart"})
    if not ty.get("benzer"):
        riskler.append({"seviye": "orta", "konu": "Trendyol'da aynısı yok", "detay": "talep reklam testiyle doğrulanmalı; tedarikçi bulmak zor olabilir"})
    riskler.append({"seviye": "bilgi", "konu": "Maliyet tahmini", "detay": alis_kaynak})
    zaman = dt.datetime.now().strftime("%Y%m%d-%H%M")
    return {
        "kaynak": "sinyal",
        "urun": {"id": f"sinyal-{s.get('asin')}", "link": s.get("productUrl"), "baslik": _baslik(s),
                 "kaynak_baslik": s.get("title"), "fiyat": alis, "para": "TRY", "puan": s.get("rating"), "puan_sayisi": s.get("reviewCount"),
                 "ozellikler": {"Tür": s.get("urun_turu"), "Çözdüğü problem": s.get("problem")},
                 "varyantlar": [], "kargo": [], "magaza": {}, "gorseller": [s["imageUrl"]] if s.get("imageUrl") else [],
                 "aciklama": {"metin": [s.get("problem") or "", s.get("neden") or ""]},
                 "pazarlama_acilari": s.get("acilar") or [], "amazon": {"asin": s.get("asin"), "fiyat_usd": s.get("price"), "kategori": s.get("kategori")}},
        "riskler": riskler,
        "maliyet": {"stok": maliyet},
        "fiyat_secenekleri": hesap.fiyat_secenekleri(maliyet, ozet or None, a),
        "ayarlar": a,
        "iade": {"oran": a["iade_orani"], "neden": "varsayılan"},
        "kargo_riski": {"seviye": "dusuk", "nedenler": []},
        "rakip_analizi": {"rakip_tablosu": benzer},
        "skor": {"karar": s.get("karar"), "toplam": None, "kaynak": "sinyal", "neden": s.get("neden"),
                 "kirmizi_bayraklar": [r["konu"] for r in riskler if r["seviye"] == "yuksek"]},
        "trendler": {},
        "trendyol": {"kelime": ty.get("aranan") or s.get("tr_kelime"), "ozet": ozet, "urunler": benzer,
                     "benzer_sayisi": ty.get("benzer"), "benzer_yok": not ty.get("benzer"), "doygunluk": dg or None},
        "reklam": rk or None,
        "sinyal": {k: s.get(k) for k in ("asin", "tr_kelime", "alis_tavani", "karar", "neden", "_zaman")},
        "_dosya_zaman": zaman,
    }


def rapor(v: dict) -> str:
    u, ty, sk = v["urun"], v["trendyol"], v["skor"]
    f = next((x for x in v["fiyat_secenekleri"] if x["secenek"] == "dengeli"), v["fiyat_secenekleri"][0] if v["fiyat_secenekleri"] else {})
    md = [f"# {u['baslik']} (ürün sinyali)", "", f"Kaynak: Amazon yeni çıkanlar · {u.get('kaynak_baslik', '')[:120]}", "",
          "## Karar", f"**{sk['karar']}** — {sk.get('neden') or ''}", "",
          "## Pazar", f"- Trendyol'da aranan: **{ty.get('kelime')}** · aynı tür ürün: {ty.get('benzer_sayisi') or 0}"]
    if ty.get("ozet"):
        md.append(f"- Piyasa medyanı: {ty['ozet'].get('medyan'):.0f} TL")
    if ty.get("doygunluk"):
        md.append(f"- Güçlü rakip (100+ yorum): {ty['doygunluk'].get('guclu_rakip')}")
    if v.get("reklam") and not v["reklam"].get("hata"):
        md.append(f"- Meta reklam: ~{v['reklam'].get('toplam_reklam')} reklam, {v['reklam'].get('reklamveren')} reklamveren")
    md += ["", "## Fiyat ve kâr", f"- Tahmini alış: {u['fiyat']:.0f} TL ({v['maliyet']['stok']['kaynak']})",
           f"- Birim maliyet: {v['maliyet']['stok']['toplam']:.0f} TL"]
    if f:
        md.append(f"- {f.get('fiyat')} TL'ye satışta net kâr {f.get('birim_kar')} TL (%{f.get('marj_yuzde')})")
    md += ["", "## Pazarlama açıları"] + [f"- {x}" for x in u.get("pazarlama_acilari") or []]
    md += ["", "## Riskler"] + [f"- {r['konu']}: {r.get('detay', '')}" for r in v["riskler"]]
    return "\n".join(md) + "\n"


def kaydet(asin: str) -> Path:
    s = bul(asin)
    if not s:
        raise SystemExit(f"Sinyal bulunamadı: {asin}")
    if not s.get("karar") or s.get("karar") == "EKSİK VERİ":
        raise SystemExit("Bu sinyal Trendyol'da doğrulanmamış; önce doğrulanmalı.")
    v = donustur(s)
    yol = CIKTI / f"urun-sinyal-{asin}-{v.pop('_dosya_zaman')}.json"
    yol.write_text(json.dumps(v, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    yol.with_suffix(".md").write_text(rapor(v), encoding="utf-8")
    return yol


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(kaydet(sys.argv[1]))
