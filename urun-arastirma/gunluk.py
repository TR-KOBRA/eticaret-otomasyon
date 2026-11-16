"""Günlük ürün taraması: listeden sıradaki kelimeyle AliExpress'te arar, en iyi adayları 20 puanlık kartla değerlendirir.

  python gunluk.py                 # sıradaki kelime
  python gunluk.py --kelime "drawer organizer | çekmece düzenleyici"
  python gunluk.py --aday 2 --trendyol-yok

Windows Görev Zamanlayıcı her sabah `gunluk_calistir.cmd` ile çalıştırır.
Çıktı: cikti/gunluk/<tarih>.md (günün özeti) + cikti/gunluk/adaylar.md (TESTE AL / İYİLEŞTİR çıkanların birikimli listesi).
Kurallar: CAPTCHA çıkarsa durur (atlatmaz); Trendyol (Apify) aylık harcama GUNLUK_APIFY_TAVAN_USD'yi (3 $) geçmişse atlanır,
böylece 5 $'lık bütçenin kalanı elle araştırmaya kalır. Para harcayan/yayınlayan hiçbir adım yok.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import traceback
from pathlib import Path

from dotenv import load_dotenv

KOK = Path(__file__).parent
load_dotenv(KOK / ".env")
load_dotenv(KOK.parent / ".env")

import aliexpress as ae  # noqa: E402
import arastir  # noqa: E402
import hesap  # noqa: E402
import rakipler  # noqa: E402
import trendler  # noqa: E402

KELIMELER = KOK / "gunluk-kelimeler.txt"
KLASOR = KOK / "cikti" / "gunluk"
DURUM = KLASOR / "durum.json"
APIFY_TAVAN = float(os.getenv("GUNLUK_APIFY_TAVAN_USD", "3"))


def kelimeler() -> list[tuple[str, str]]:
    out = []
    for satir in KELIMELER.read_text(encoding="utf-8").splitlines():
        satir = satir.strip()
        if not satir or satir.startswith("#"):
            continue
        en, _, tr = satir.partition("|")
        out.append((en.strip(), (tr or en).strip()))
    return out


def _kelimeler(metin: str) -> list[str]:
    tr = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosucgiosu")
    return [w for w in re.findall(r"[a-z0-9]+", metin.lower().translate(tr)) if len(w) >= 3]


def _eslesen(baslik: list[str], arama: str) -> tuple[int, int]:
    kokler = {w[:4] for w in _kelimeler(arama)}
    return sum(1 for k in kokler if any(w.startswith(k) for w in baslik)), len(kokler)


def alakali(baslik: str | None, en: str, tr: str) -> bool:
    """Başlık (TR sitesinde Türkçe çevrilmiş olur) arama kelimesinin en az 2 kökünü (tek kelimeyse 1) içermeli.
    AliExpress popüler sıralaması bazen alakasız çok satanları da getiriyor (ör. tüy rulosu → takma kirpik)."""
    b = _kelimeler(baslik or "")
    for arama in (tr, en):
        n, toplam = _eslesen(b, arama)
        if toplam and n >= min(2, toplam):
            return True
    return False


def durum_oku() -> dict:
    try:
        return json.loads(DURUM.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"sira": 0, "gorulen": []}


def apify_harcama() -> float | None:
    if not os.getenv("APIFY_TOKEN"):
        return None
    try:
        from apify_client import ApifyClient
        return rakipler._aylik_harcama(ApifyClient(os.getenv("APIFY_TOKEN")))
    except Exception:
        return None


def calistir(args) -> int:
    KLASOR.mkdir(parents=True, exist_ok=True)
    d = durum_oku()
    liste = kelimeler()
    if args.kelime:
        en, _, tr = args.kelime.partition("|")
        en, tr = en.strip(), (tr or en).strip()
    else:
        en, tr = liste[d["sira"] % len(liste)]
    bugun = dt.datetime.now()
    md = [f"# Günlük ürün taraması — {bugun:%d.%m.%Y %H:%M}", "", f"Kelime: **{en}** (TR: {tr})", ""]
    sonuclar, notlar = [], []

    try:
        with ae.tarayici(False) as ctx:
            print(f"› AliExpress'te aranıyor: {en}")
            bulunan = ae.ara(ctx, en, args.sayfa, "populer")
            ilgili = [u for u in bulunan if alakali(u.get("baslik"), en, tr)]
            aday = [u for u in ilgili if (u["satis"] or 0) >= args.min_satis and args.min_fiyat <= (u["fiyat"] or 0) <= args.max_fiyat
                    and u["id"] not in d["gorulen"]]
            print(f"  {len(bulunan)} ürün, {len(ilgili)} alakalı, filtre sonrası {len(aday)}")

            rk = None
            harcama = apify_harcama()
            if not aday:
                notlar.append(f"Filtreden geçen ürün yok ({len(bulunan)} bulundu): fiyat {args.min_fiyat:.0f}–{args.max_fiyat:.0f} TL, satış ≥ {args.min_satis}.")
            elif args.trendyol_yok:
                notlar.append("Trendyol taraması kapalı (--trendyol-yok).")
            elif harcama is None:
                notlar.append("Trendyol atlandı: APIFY_TOKEN yok ya da harcama okunamadı.")
            elif harcama >= APIFY_TAVAN:
                notlar.append(f"Trendyol atlandı: bu ay Apify harcaması {harcama:.2f} $ ≥ günlük tarama tavanı {APIFY_TAVAN:.2f} $.")
            else:
                print("› Trendyol rakipleri (Apify, yorumsuz)…")
                rk = rakipler.trendyol(tr, adet=30)
                if rk.get("hata"):
                    notlar.append(f"Trendyol: {rk['hata']}")
                    rk = None
            medyan = (rk or {}).get("ozet", {}).get("medyan")
            for u in aday:
                u["skor"] = hesap.firsat_skoru(u, medyan)
            aday.sort(key=lambda x: -x["skor"])

            tr_veri = trendler.talep([tr])
            for u0 in aday[: args.aday]:
                print(f"› İnceleniyor: {(u0['baslik'] or '')[:70]}")
                try:
                    u = ae.urun(ctx, u0["link"], yorum_adedi=40)
                    yol, deg = arastir.rapor(u, rk, tr_veri, "stok", "site")
                    sk = deg["skor"]
                    f = next((s for s in deg["fiyat_secenekleri"] if s.get("secenek") == "dengeli"), deg["fiyat_secenekleri"][0])
                    sonuclar.append({"id": u["id"], "baslik": u["baslik"], "link": u0["link"], "karar": sk["karar"],
                                     "puan": sk["toplam"], "fiyat": f.get("fiyat"), "marj": f.get("marj_yuzde"),
                                     "rapor": str(yol), "json": str(yol.with_suffix(".json"))})
                    d["gorulen"].append(u["id"])
                except ae.DogrulamaGerekli:
                    raise
                except Exception as e:
                    notlar.append(f"{u0['id']} incelenemedi: {type(e).__name__}: {e}")
    except ae.DogrulamaGerekli:
        notlar.append("AliExpress doğrulama (CAPTCHA) istedi → tarama durduruldu, atlatılmadı. Yarın tekrar denenecek.")
    except Exception as e:
        notlar.append(f"Beklenmeyen hata: {type(e).__name__}: {e}")
        traceback.print_exc()

    if not args.kelime:
        d["sira"] = d["sira"] + 1
    d["gorulen"] = d["gorulen"][-500:]
    d["son"] = bugun.isoformat(timespec="minutes")
    DURUM.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")

    sira = {"TESTE AL": 0, "İYİLEŞTİR": 1, "EKSİK VERİ": 2, "ELE": 3}
    sonuclar.sort(key=lambda s: (sira.get(s["karar"], 9), -(s["puan"] or 0)))
    if sonuclar:
        md += ["| Karar | Puan | Ürün | Önerilen fiyat | Net marj | Rapor |", "|---|---|---|---|---|---|"]
        for s in sonuclar:
            md.append(f"| **{s['karar']}** | {s['puan']}/20 | [{(s['baslik'] or '')[:60]}]({s['link']}) | {arastir.tl(s['fiyat'])} | "
                      f"%{s['marj']} | `{Path(s['rapor']).name}` |")
    else:
        md.append("Bugün incelenen ürün yok.")
    if notlar:
        md += ["", "## Notlar", ""] + [f"- {n}" for n in notlar]
    iyi = [s for s in sonuclar if s["karar"] in ("TESTE AL", "İYİLEŞTİR")]
    md += ["", "TESTE AL çıkan bir ürünle hattı başlatmak için (eticaret/ klasöründe):", "",
           "```", "python hat.py yeni urun-arastirma/cikti/<urun-...json> --ad <kisaad>", "```"]
    gun = KLASOR / f"{bugun:%Y-%m-%d}.md"
    gun.write_text("\n".join(md) + "\n", encoding="utf-8")

    birikim = KLASOR / "adaylar.md"
    if not birikim.exists():
        birikim.write_text("# Aday ürünler (günlük taramadan)\n\n| Tarih | Karar | Puan | Ürün | Fiyat | Marj | JSON |\n|---|---|---|---|---|---|---|\n",
                           encoding="utf-8")
    with birikim.open("a", encoding="utf-8") as fh:
        for s in iyi:
            fh.write(f"| {bugun:%d.%m.%Y} | {s['karar']} | {s['puan']}/20 | [{(s['baslik'] or '')[:50]}]({s['link']}) | "
                     f"{arastir.tl(s['fiyat'])} | %{s['marj']} | `{Path(s['json']).name}` |\n")
    print(f"✓ Günlük özet: {gun}  ({len(sonuclar)} ürün, {len(iyi)} aday)")
    return 0


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Günlük ürün taraması")
    p.add_argument("--kelime", help="'ingilizce | türkçe' (verilmezse listeden sıradaki)")
    p.add_argument("--aday", type=int, default=3, help="derin incelenecek ürün sayısı")
    p.add_argument("--sayfa", type=int, default=2)
    p.add_argument("--min-satis", type=int, default=0, help="TR arama sonuçlarında satış sayısı çoğu üründe görünmüyor")
    p.add_argument("--min-fiyat", type=float, default=40)
    p.add_argument("--max-fiyat", type=float, default=1200)
    p.add_argument("--trendyol-yok", action="store_true")
    sys.exit(calistir(p.parse_args()))


if __name__ == "__main__":
    main()
