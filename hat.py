"""E-ticaret hattı: araştırmadan sonraki adımları (2–11) proje klasöründe sırayla çalıştırır.

  python hat.py yeni <urun-arastirma/cikti/urun-....json> [--ad isim] [--zorla]
  python hat.py durum <proje>
  python hat.py calistir <proje> [adim ...]     # adım verilmezse: ön koşulu sağlanan tüm adımlar
  python hat.py onayla <proje> <adim> [--secim anahtar=deger ...]
  python hat.py sec <proje> anahtar=deger ...    # ör. fiyat=749

Para harcayan / dışarı yayın yapan işler (numune, domain, paylaşım, reklam) bu komutlarla yapılmaz;
ilgili adım ne yapılacağını raporlar ve insan onayı bekler. Reklam/mağaza gönderimi ayrıca açık bayrak ister.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "hat"))
import ortak  # noqa: E402
from ortak import ADIMLAR, PROJELER, Proje, projeyi_bul, slug  # noqa: E402


def eksikler(p: Proje, adim: str) -> list[str]:
    a = ADIMLAR[adim]
    e = [f"{o} onayı" for o in a["once"] if not p.onayli(o)]
    e += [f"{g} çıktısı" for g in a.get("gerekli", []) if not p.oku(g)]
    return e


def yeni(args):
    kaynak = Path(args.json)
    v = json.loads(kaynak.read_text(encoding="utf-8"))
    sk = v.get("skor") or {}
    if not sk:
        sys.exit("Bu JSON'da skor yok. Önce: python urun-arastirma/arastir.py skorla <json>")
    if sk.get("karar") != "TESTE AL" and not args.zorla:
        sys.exit(f"Araştırma kararı: {sk.get('karar')} ({sk.get('toplam')}/20). Hat sadece TESTE AL ürünlerle başlar "
                 "(denemek için --zorla).")
    ad = args.ad or slug(v["urun"]["baslik"])[:30] + "-" + dt.datetime.now().strftime("%m%d")
    yol = PROJELER / slug(ad)
    yol.mkdir(parents=True, exist_ok=True)
    shutil.copy(kaynak, yol / "urun.json")
    p = Proje(yol)
    p.durum["kaynak"] = str(kaynak)
    p.durum["zorla"] = bool(args.zorla)
    p.kaydet_durum()
    print(f"✓ Proje: {yol}\n  Sonraki: python hat.py calistir {p.ad}")


def durum(args):
    p = projeyi_bul(args.proje)
    print(f"Proje {p.ad} · {p.urun['baslik'][:70]}")
    if p.durum["secimler"]:
        print("Seçimler: " + ", ".join(f"{k}={v}" for k, v in p.durum["secimler"].items()))
    for ad, a in ADIMLAR.items():
        d = p.durum["adimlar"].get(ad, {})
        e = eksikler(p, ad)
        if d.get("durum"):
            s = {"tamam": "✓ tamam", "onaylandi": "✓ onaylandı", "onay_bekliyor": "⏸ onay bekliyor: " + (a["onay"] or "")}[d["durum"]]
        else:
            s = "· bekliyor: " + ", ".join(e) if e else "○ çalıştırılabilir"
        print(f"  {a['no']:>2} {ad:<10} {s}")


def calistir(args):
    p = projeyi_bul(args.proje)
    hedef = args.adimlar or [a for a in ADIMLAR if not p.durum["adimlar"].get(a)]
    ilerledi = True
    yapilan = []
    while ilerledi:
        ilerledi = False
        for ad in [a for a in hedef if a not in yapilan]:
            e = eksikler(p, ad)
            if e:
                if args.adimlar:
                    print(f"✗ {ad}: önce {', '.join(e)}")
                    yapilan.append(ad)
                continue
            print(f"› {ADIMLAR[ad]['no']} {ad}…")
            mod = importlib.import_module(ad)
            try:
                mod.calistir(p, args)
            except Exception as ex:  # bir adımın hatası diğerlerini durdurmasın
                print(f"  ✗ {ad} hata: {type(ex).__name__}: {ex}")
                yapilan.append(ad)
                continue
            p = Proje(p.yol)
            print(f"  ✓ {p.dosya(ad, 'md').name}" + (f"  ⏸ onay: {ADIMLAR[ad]['onay']}" if ADIMLAR[ad]["onay"] else ""))
            yapilan.append(ad)
            ilerledi = True
    print()
    durum(args)


def secimleri_isle(p: Proje, liste):
    for s in liste or []:
        k, _, v = s.partition("=")
        p.durum["secimler"][k.strip()] = v.strip()


def onayla(args):
    p = projeyi_bul(args.proje)
    if args.adim not in ADIMLAR:
        sys.exit(f"Bilinmeyen adım: {args.adim}")
    if not p.oku(args.adim):
        sys.exit(f"{args.adim} henüz çalıştırılmadı.")
    secimleri_isle(p, args.secim)
    if args.adim == "marka" and not p.secim("isim"):
        sys.exit("Marka onayı için isim seç: --secim isim=<Isim>")
    a = p.durum["adimlar"].setdefault(args.adim, {})
    a["durum"] = "onaylandi"
    a["onay_zamani"] = dt.datetime.now().isoformat(timespec="minutes")
    p.kaydet_durum()
    print(f"✓ {args.adim} onaylandı")


def sec(args):
    p = projeyi_bul(args.proje)
    secimleri_isle(p, args.secim)
    p.kaydet_durum()
    print("✓ " + ", ".join(f"{k}={v}" for k, v in p.durum["secimler"].items()))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="E-ticaret hattı (adım 2–11)")
    alt = ap.add_subparsers(dest="komut", required=True)
    y = alt.add_parser("yeni"); y.add_argument("json"); y.add_argument("--ad"); y.add_argument("--zorla", action="store_true")
    y.set_defaults(f=yeni)
    d = alt.add_parser("durum"); d.add_argument("proje"); d.set_defaults(f=durum)
    c = alt.add_parser("calistir"); c.add_argument("proje"); c.add_argument("adimlar", nargs="*", choices=list(ADIMLAR) + [[]])
    c.add_argument("--gonder", action="store_true", help="magaza/reklam: gerçekten API'ye gönder (varsayılan: kuru çalıştırma)")
    c.add_argument("--csv", help="analiz/operasyon: girdi CSV dosyası")
    c.set_defaults(f=calistir)
    o = alt.add_parser("onayla"); o.add_argument("proje"); o.add_argument("adim"); o.add_argument("--secim", nargs="*")
    o.set_defaults(f=onayla)
    s = alt.add_parser("sec"); s.add_argument("proje"); s.add_argument("secim", nargs="+"); s.set_defaults(f=sec)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
