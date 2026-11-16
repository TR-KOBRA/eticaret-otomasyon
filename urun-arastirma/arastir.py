"""Ürün araştırma hattı.

Kullanım:
  python arastir.py kesfet "oda kokusu makinesi" [--sayfa 2] [--trendyol] [--trend "kelime1,kelime2"]
  python arastir.py urun <aliexpress-linki> [--kelime "oda kokusu makinesi"] [--trendyol] [--senaryo stok|dogrudan] [--kanal site|trendyol]
  python arastir.py skorla cikti/urun-....json [--trendyol --kelime "..."]   # kayıtlı ürünü yeniden değerlendir (AliExpress'e gitmez)

Çıktılar cikti/ klasörüne .md (okunabilir rapor) ve .json (ham veri) olarak yazılır.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

import aliexpress as ae
import hesap
import rakip_analiz
import rakipler
import riskler
import skor
import trendler

KOK = Path(__file__).parent
CIKTI = KOK / "cikti"
AYLAR = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos",
         "Eylül", "Ekim", "Kasım", "Aralık"]


def slug(s: str) -> str:
    tr = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    return re.sub(r"[^a-z0-9]+", "-", s.translate(tr).lower()).strip("-")[:50]


def tl(x) -> str:
    if x is None:
        return "-"
    return f"{x:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")


def kaydet(ad: str, veri: dict, md: str) -> Path:
    CIKTI.mkdir(exist_ok=True)
    zaman = dt.datetime.now().strftime("%Y%m%d-%H%M")
    j = CIKTI / f"{ad}-{zaman}.json"
    m = CIKTI / f"{ad}-{zaman}.md"
    j.write_text(json.dumps(veri, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    m.write_text(md, encoding="utf-8")
    return m


def trend_md(t: dict) -> list[str]:
    s = ["## Google Trends (Türkiye, son 12 ay)", ""]
    if t.get("hata"):
        return s + [f"_Alınamadı: {t['hata']}_", ""]
    s += ["| Kelime | Ortalama ilgi | Son 3 ay | Değişim | Zirve ayı | Dip ayı |", "|---|---|---|---|---|---|"]
    for k, v in t["kelimeler"].items():
        d = v["degisim_yuzde"]
        s.append(f"| {k} | {v['ortalama']} | {v['son_3_ay']} | {'-' if d is None else f'%{d:+}'} "
                 f"| {AYLAR[v['zirve_ay']]} | {AYLAR[v['dip_ay']]} |")
    s.append("")
    for k, v in t["kelimeler"].items():
        if v.get("yukselen"):
            s.append(f"**Yükselen aramalar ({k}):** " + ", ".join(f"{r['query']} ({r['value']})" for r in v["yukselen"][:8]))
        if v.get("en_cok"):
            s.append(f"**En çok aranan ({k}):** " + ", ".join(r["query"] for r in v["en_cok"][:8]))
    return s + [""]


def rakip_md(r: dict | None) -> list[str]:
    if r is None:
        return []
    s = ["## Trendyol rakipleri", ""]
    if r.get("hata"):
        return s + [f"_{r['hata']}_", ""]
    o = r["ozet"]
    if o:
        s += [f"{o['urun_sayisi']} ürün · fiyat {tl(o['min'])} – {tl(o['max'])} · medyan **{tl(o['medyan'])}** "
              f"· alt/üst çeyrek {tl(o['alt_ceyrek'])} / {tl(o['ust_ceyrek'])} "
              f"· toplam {o['toplam_degerlendirme']} değerlendirme", ""]
    s += ["| Ürün | Marka | Fiyat | Puan | Değerlendirme | Favori | Satıcı |", "|---|---|---|---|---|---|---|"]
    for u in sorted(r["urunler"], key=lambda x: -(int(x["degerlendirme"] or 0)))[:15]:
        s.append(f"| [{(u['ad'] or '')[:55]}]({u['link']}) | {u['marka'] or '-'} | {tl(u['fiyat'])} | "
                 f"{u['puan'] or '-'} | {u['degerlendirme'] or 0} | {u['favori'] or '-'} | {u['satici'] or '-'} |")
    dusuk = [y for y in r.get("yorumlar", []) if (y["puan"] or 5) <= 3]
    if dusuk:
        s += ["", "**Rakiplerin düşük puanlı yorumları (itiraz kaynağı):**", ""]
        s += [f"- {y['puan']}★ {(y['metin'] or '').strip()[:220]}" for y in dusuk[:15]]
    return s + [""]


def degerlendir(u: dict, rk: dict | None, tr: dict | None, senaryo: str = "stok", kanal: str = "site",
                analiz_yap: bool = True) -> dict:
    """Maliyet → hedef marjlı fiyat → riskler → rakip/yorum analizi → 20 puanlık skor."""
    kargo = sorted(u["kargo"], key=lambda k: (k["ucret_tl"] or 0)) if u.get("kargo") else []
    en_ucuz = kargo[0] if kargo else {"ucret_tl": 0, "gun_min": None, "gun_max": None, "firma": "-"}
    stok = hesap.birim_maliyet(u["fiyat"] or 0, en_ucuz["ucret_tl"] or 0, "stok")
    dogrudan = hesap.birim_maliyet(u["fiyat"] or 0, en_ucuz["ucret_tl"] or 0, "dogrudan")
    secili = stok if senaryo == "stok" else dogrudan
    iade_orani, iade_neden = hesap.iade_orani_tahmini(u)
    a = hesap.ayarlar(kanal, {"iade_orani": iade_orani})
    secenekler = hesap.fiyat_secenekleri(secili, (rk or {}).get("ozet"), a)
    rs = riskler.tara(u)
    kr = riskler.kargo_riski(u)
    an = None
    if analiz_yap:
        print("› Rakip ve yorum analizi (Gemini)…")
        an = rakip_analiz.analiz(u, rk)
    print("› 20 puanlık skor kartı…")
    sk = skor.puanla(u, secenekler, kr, iade_orani, rk, tr, an, rs)
    return {"kargo": kargo, "en_ucuz": en_ucuz, "maliyet": {"stok": stok, "dogrudan": dogrudan}, "senaryo": senaryo,
            "kanal": kanal, "ayarlar": {**a, "son_kontrol": hesap.AYARLAR_SON_KONTROL},
            "iade": {"oran": iade_orani, "neden": iade_neden}, "fiyat_secenekleri": secenekler, "riskler": rs,
            "kargo_riski": kr, "rakip_analizi": an, "skor": sk}


def skor_md(sk: dict) -> list[str]:
    ikon = {"TESTE AL": "🟢", "İYİLEŞTİR": "🟡", "ELE": "🔴", "EKSİK VERİ": "⚪"}
    s = [f"## Karar: {ikon.get(sk['karar'], '')} {sk['karar']} · {sk['toplam']}/20", "",
         "15–20 teste al · 10–14 iyileştir · 0–9 ele (kaynaklar/ozetler/arastirma.md)"
         + (f" · {sk['eksik_kriter']} kriter puanlanamadı, en fazla {sk['en_fazla_mumkun']}" if sk["eksik_kriter"] else ""), ""]
    if sk["kirmizi_bayraklar"]:
        s += ["**Kırmızı bayraklar:**", ""] + [f"- 🚩 {b}" for b in sk["kirmizi_bayraklar"]] + [""]
    s += ["| Kriter | Puan | Kaynak | Gerekçe |", "|---|---|---|---|"]
    s += [f"| {k['ad']} | {'-' if k['puan'] is None else k['puan']}/2 | {k['kaynak']} | {k['gerekce']} |" for k in sk["kriterler"]]
    if sk.get("hook_ornekleri"):
        s += ["", "**Reklam kancası denemeleri (ilk 3 sn):**", ""] + [f"- {h}" for h in sk["hook_ornekleri"]]
    if sk.get("paket_onerisi"):
        s += ["", f"**Paket önerisi:** {sk['paket_onerisi']}"]
    if sk.get("gemini_hata"):
        s += ["", f"_Gemini hatası: {sk['gemini_hata']}_"]
    return s + [""]


def analiz_md(an: dict | None) -> list[str]:
    if not an:
        return []
    s = ["## Rakip ve yorum analizi", ""]
    if an.get("hata"):
        s += [f"_{an['hata']}_", ""]
    if an.get("rakip_tablosu"):
        s += ["| Rakip | Fiyat | Puan | Değerlendirme | Ücretsiz kargo | Satıcı |", "|---|---|---|---|---|---|"]
        s += [f"| [{(t['ad'] or '')[:50]}]({t['link']}) | {tl(t['fiyat'])} | {t['puan'] or '-'} | {t['degerlendirme'] or 0} | "
              f"{'evet' if t['ucretsiz_kargo'] else '-'} | {t['satici'] or '-'} |" for t in an["rakip_tablosu"]]
        s.append("")
    if an.get("hata"):
        return s
    s.append(f"{an['yorum_sayisi']} yorum incelendi.")
    if an.get("sikayetler"):
        s += ["", "**Tekrar eden şikâyetler → fırsat:**", ""]
        s += [f"- **{x['konu']}** ({x['yorum_sayisi']} yorum) — “{x['ornek'][:160]}” → {x['firsat']}" for x in an["sikayetler"]]
    else:
        s += ["", "_Yorumlarda tekrar eden şikâyet bulunmadı._"]
    if an.get("begeniler"):
        s += ["", "**Beğenilenler (reklam dilinde kullan):**", ""]
        s += [f"- **{x['konu']}** ({x['yorum_sayisi']}) — “{x['ornek'][:160]}”" for x in an["begeniler"]]
    if an.get("farklilasma"):
        s += ["", "**Farklılaşma:**", ""] + [f"- _{x['boyut']}_: {x['oneri']}" for x in an["farklilasma"]]
    if an.get("neden_benden"):
        s += ["", f"**Neden benden alınır:** {an['neden_benden']}"]
    if an.get("sss"):
        s += ["", "**SSS taslağı:**", ""] + [f"- **{x['soru']}** {x['cevap_taslagi']}" for x in an["sss"]]
    return s + [""]


def fiyat_md(d: dict) -> list[str]:
    sec = d["fiyat_secenekleri"]
    a = d["ayarlar"]
    s = [f"## Fiyat seçenekleri ({'stok' if d['senaryo'] == 'stok' else 'doğrudan gönderim'} · kanal: {d['kanal']})", "",
         f"Kaynak: {sec[-1]['kaynak']} · reklam payı %{a['reklam_payi'] * 100:.0f} · ödeme %{a['odeme_komisyonu'] * 100:.1f}"
         f" · pazaryeri %{a['pazaryeri_komisyonu'] * 100:.0f} · iade %{a['iade_orani'] * 100:.0f} ({d['iade']['neden']}) "
         f"· hedef net marj %{a['hedef_marj'] * 100:.0f} · oranların son kontrolü {a['son_kontrol']}", "",
         "| Seçenek | Fiyat | Net kâr | Net marj | Reklam öncesi kâr | Başabaş ROAS | 0 ATC'de kapat | 0 satışta kapat | 2'li | 3'lü |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    s += [f"| {x['secenek']} | {tl(x['fiyat'])} | {tl(x['birim_kar'])} | {'✅' if x['hedefe_uygun'] else '❌'} %{x['marj_yuzde']} | "
          f"{tl(x['reklam_oncesi_kar'])} | {x['basabas_roas'] or 'zarar'} | {tl(x['kapat_0_atc_harcama'])} | "
          f"{tl(x['kapat_0_satis_harcama'])} | {tl(x['paket_2'])} | {tl(x['paket_3'])} |" for x in sec]
    s += ["", "Net kâr = reklam payı ve beklenen iade maliyeti düşüldükten sonra. Kapatma eşikleri reklam seti başına harcamadır "
          "(kaynaklar/ozetler/reklam.md).", ""]
    return s


# ------------------------------------------------------------------ keşif
def kesfet(args):
    with ae.tarayici(args.gorunur) as ctx:
        print(f"› AliExpress'te aranıyor: {args.kelime}")
        sonuc = ae.ara(ctx, args.kelime, args.sayfa, args.sirala)
    print(f"  {len(sonuc)} ürün bulundu")
    once = len(sonuc)
    sonuc = [u for u in sonuc if (u["satis"] or 0) >= args.min_satis
             and (args.max_fiyat is None or (u["fiyat"] or 0) <= args.max_fiyat)
             and (u["fiyat"] or 0) >= args.min_fiyat]
    if args.icermeli:
        kel = [k.strip().lower() for k in args.icermeli.split(",") if k.strip()]
        sonuc = [u for u in sonuc if any(k in (u["baslik"] or "").lower() for k in kel)]
    print(f"  filtre sonrası {len(sonuc)} / {once}")

    rk = None
    if args.trendyol:
        print("› Trendyol rakip fiyatları (Apify)…")
        rk = rakipler.trendyol(args.trendyol_kelime or args.kelime, adet=40)
    medyan = (rk or {}).get("ozet", {}).get("medyan")

    for u in sonuc:
        u["skor"] = hesap.firsat_skoru(u, medyan)
        u["tahmini_maliyet"] = hesap.birim_maliyet(u["fiyat"] or 0, 0, "stok")["toplam"]
    sonuc.sort(key=lambda x: -x["skor"])

    kelimeler = [k.strip() for k in (args.trend or args.kelime).split(",") if k.strip()]
    print(f"› Google Trends: {', '.join(kelimeler)}")
    tr = trendler.talep(kelimeler)

    md = [f"# Ürün keşfi: {args.kelime}", "", f"_{dt.datetime.now():%d.%m.%Y %H:%M}_ · AliExpress TR, sıralama: {args.sirala}, "
          f"{args.sayfa} sayfa · filtre: satış ≥ {args.min_satis}, fiyat {args.min_fiyat:.0f}–{args.max_fiyat or '∞'} TL · skor = talep (45) + puan (25) + fiyat boşluğu (30)", ""]
    md += trend_md(tr)
    md += rakip_md(rk)
    md += ["## En iyi adaylar", "",
           "| # | Skor | Ürün | AE fiyatı | Tahmini birim maliyet | Satış | Puan |", "|---|---|---|---|---|---|---|"]
    for i, u in enumerate(sonuc[: args.ilk], 1):
        md.append(f"| {i} | {u['skor']} | [{(u['baslik'] or '')[:60]}]({u['link']}) | {tl(u['fiyat'])} | "
                  f"{tl(u['tahmini_maliyet'])} | {u['satis'] or 0} | {u['puan'] or '-'} |")
    md += ["", "Bir adayı derinlemesine incelemek için:", "",
           f"```\npython arastir.py urun <link> --kelime \"{args.kelime}\" --trendyol\n```", ""]
    yol = kaydet(f"kesif-{slug(args.kelime)}", {"aliexpress": sonuc, "trendler": tr, "trendyol": rk}, "\n".join(md))
    print(f"✓ Rapor: {yol}")


# ------------------------------------------------------------------ tek ürün
def urun(args):
    with ae.tarayici(args.gorunur) as ctx:
        print("› AliExpress ürün sayfası okunuyor…")
        u = ae.urun(ctx, args.link, yorum_adedi=args.yorum)
    print(f"  {u['baslik'][:80]}")

    rk = None
    if args.trendyol:
        print("› Trendyol rakipleri (Apify)…")
        rk = rakipler.trendyol((args.kelime or u["baslik"][:40]).split(",")[0].strip(), adet=40, yorumlar=True, yorum_adedi=4)

    kelimeler = [k.strip() for k in (args.kelime or "").split(",") if k.strip()]
    tr = trendler.talep(kelimeler) if kelimeler else {"hata": "--kelime verilmedi"}
    rapor(u, rk, tr, args.senaryo, args.kanal)


def rapor(u: dict, rk, tr, senaryo: str, kanal: str):
    d = degerlendir(u, rk, tr, senaryo, kanal)
    kargo, en_ucuz, rs = d["kargo"], d["en_ucuz"], d["riskler"]
    stok, dogrudan = d["maliyet"]["stok"], d["maliyet"]["dogrudan"]

    y = u["yorumlar"]
    oz = y["ozet"] or {}
    dusuk = [r for r in y["liste"] if (r["yildiz"] or 5) <= 3]

    md = [f"# Ürün raporu: {u['baslik']}", "",
          f"[AliExpress]({u['link']}) · {dt.datetime.now():%d.%m.%Y %H:%M}", "",
          "## Özet", "",
          f"- **Fiyat:** {tl(u['fiyat'])} (liste {tl(u['eski_fiyat'])})",
          f"- **Satış:** {u['satis'] or '-'} · **Puan:** {u['puan'] or '-'} ({u['puan_sayisi'] or 0} değerlendirme) · **Stok:** {u['stok'] or '-'}",
          f"- **Mağaza:** {u['magaza']['ad']} · olumlu %{u['magaza']['olumlu_oran']} · {u['magaza']['toplam']} değerlendirme",
          f"- **Görseller:** {len(u['gorseller'])} ana + {len(u['aciklama']['gorseller'])} açıklama görseli"
          + (" · ürün videosu var" if u["video"] else ""), ""]
    md += skor_md(d["skor"])

    md += ["## Riskler", ""]
    if rs:
        ikon = {"yuksek": "🔴", "orta": "🟠", "bilgi": "⚪"}
        md += [f"- {ikon[x['seviye']]} **{x['konu']}**" + (f": {x['detay']}" if x["detay"] else "") for x in rs]
    else:
        md.append("- Otomatik taramada belirgin risk çıkmadı (yine de numune sipariş et).")
    md.append("")

    md += ["## Varyantlar", "", "| Varyant | Fiyat | Stok |", "|---|---|---|"]
    md += [f"| {v['ad'] or v['sku']} | {tl(v['fiyat'])} | {v['stok'] if v['stok'] is not None else '-'} |" for v in u["varyantlar"][:20]]
    md += ["", "## Satıcının verdiği özellikler", "",
           "Sitede, Instagram'da ve reklamlarda kullanılacak her teknik iddia bu listeye ya da açıklama metnine dayanmalı.", "",
           "| Özellik | Değer |", "|---|---|"]
    md += [f"| {k} | {v} |" for k, v in u["ozellikler"].items()]
    if u["aciklama"]["metin"]:
        md += ["", "**Açıklama metni:**", ""] + [f"> {t}" for t in u["aciklama"]["metin"][:30]]

    md += ["", "## Türkiye'ye kargo", "", "| Firma | Ücret | Süre (gün) | Nereden | Takip |", "|---|---|---|---|---|"]
    md += [f"| {k['firma']} | {'Ücretsiz' if k['ucretsiz'] else tl(k['ucret_tl'])} | {k['gun_min']}–{k['gun_max']} | "
           f"{k['nereden']} | {'var' if k['takip'] else 'yok'} |" for k in kargo]

    md += ["", "## Yorumlar", ""]
    if oz:
        yz = oz.get("yildiz") or {}
        md.append(f"{oz.get('toplam')} yorum · ortalama {oz.get('ortalama')} · "
                  + " · ".join(f"{i}★ {yz.get(i) or 0}" for i in (5, 4, 3, 2, 1)))
        for e in oz.get("etiketler") or []:
            md.append(f"- **{e['konu']}** ({e['oy']} oy): " + " / ".join(f"{k} {v}" for k, v in e["dagilim"].items()))
    if dusuk:
        md += ["", "**Düşük puanlı yorumlar (zayıf noktalar, SSS ve itiraz kaynağı):**", ""]
        md += [f"- {r['yildiz']}★ [{r['ulke']}] {(r['metin'] or '').strip()[:250]}" for r in dusuk[:15]]
    olumlu = [r for r in y["liste"] if (r["yildiz"] or 0) >= 4 and r["metin"]]
    if olumlu:
        md += ["", "**Olumlu yorumlardan örnekler (müşterinin kendi dili):**", ""]
        md += [f"- {(r['metin'] or '').strip()[:200]}" for r in olumlu[:8]]

    md += ["", "## Birim maliyet", "",
           "| Kalem | Türkiye'de stok | Doğrudan AliExpress gönderimi |", "|---|---|---|"]
    tum = list(dict.fromkeys(list(stok["kalemler"]) + list(dogrudan["kalemler"])))
    md += [f"| {k} | {tl(stok['kalemler'].get(k))} | {tl(dogrudan['kalemler'].get(k))} |" for k in tum]
    md += [f"| **Toplam** | **{tl(stok['toplam'])}** | **{tl(dogrudan['toplam'])}** |", "",
           f"Doğrudan gönderimde teslim süresi {en_ucuz['gun_min']}–{en_ucuz['gun_max']} gün. "
           "Vergi ve gümrük oranları `hesap.py` içindeki AYARLAR'dan gelir; kullanmadan önce güncel mevzuata göre kontrol et.", ""]

    md += fiyat_md(d)
    md += analiz_md(d["rakip_analizi"])
    md += trend_md(tr)
    md += rakip_md(rk)

    veri = {"urun": u, "riskler": rs, "maliyet": d["maliyet"], "fiyat_secenekleri": d["fiyat_secenekleri"],
            "ayarlar": d["ayarlar"], "iade": d["iade"], "kargo_riski": d["kargo_riski"],
            "rakip_analizi": d["rakip_analizi"], "skor": d["skor"], "trendler": tr, "trendyol": rk}
    yol = kaydet(f"urun-{u['id']}", veri, "\n".join(md))
    sk = d["skor"]
    print(f"✓ Karar: {sk['karar']} ({sk['toplam']}/20) · Rapor: {yol}")
    return yol, d


def skorla(args):
    eski = json.loads(Path(args.json).read_text(encoding="utf-8"))
    u = eski["urun"]
    print(f"› {u['baslik'][:80]}")
    rk = eski.get("trendyol")
    if args.trendyol:
        print("› Trendyol rakipleri (Apify)…")
        rk = rakipler.trendyol((args.kelime or u["baslik"][:40]).split(",")[0].strip(), adet=40, yorumlar=True, yorum_adedi=4)
    tr = eski.get("trendler")
    if args.kelime and (not tr or tr.get("hata")):
        tr = trendler.talep([k.strip() for k in args.kelime.split(",") if k.strip()])
    rapor(u, rk, tr or {"hata": "trend verisi yok"}, args.senaryo, args.kanal)


def main():
    load_dotenv(KOK / ".env")
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="E-ticaret ürün araştırma hattı")
    p.add_argument("--gorunur", action="store_true", help="tarayıcıyı görünür aç (doğrulama çıkarsa elle geçmek için)")
    alt = p.add_subparsers(dest="komut", required=True)

    k = alt.add_parser("kesfet", help="anahtar kelimeyle aday ürün bul")
    k.add_argument("kelime", help="AliExpress arama kelimesi (İngilizce daha iyi sonuç verir)")
    k.add_argument("--sayfa", type=int, default=3)
    k.add_argument("--ilk", type=int, default=20, help="raporda gösterilecek aday sayısı")
    k.add_argument("--min-satis", type=int, default=0, help="en az satış adedi (TR sitesinde satış sayıları düşük görünür)")
    k.add_argument("--icermeli", help="başlıkta en az biri geçmeli, virgülle (ör. 'difüzör,aroma')")
    k.add_argument("--sirala", choices=["populer", "satis", "fiyat_artan", "fiyat_azalan"], default="populer")
    k.add_argument("--min-fiyat", type=float, default=0)
    k.add_argument("--max-fiyat", type=float, default=2000, help="AliExpress fiyat üst sınırı (TL)")
    k.add_argument("--trend", help="Trends için virgülle ayrılmış Türkçe kelimeler (varsayılan: arama kelimesi)")
    k.add_argument("--trendyol", action="store_true", help="Trendyol rakip fiyatlarını da çek (Apify, ücretli)")
    k.add_argument("--trendyol-kelime", help="Trendyol'da aranacak kelime (varsayılan: arama kelimesi)")
    k.set_defaults(f=kesfet)

    u = alt.add_parser("urun", help="tek ürünü derinlemesine incele")
    u.add_argument("link")
    u.add_argument("--kelime", help="Türkçe pazar kelimesi(leri), virgülle: Trends ve Trendyol için")
    u.add_argument("--trendyol", action="store_true")
    u.add_argument("--senaryo", choices=["stok", "dogrudan"], default="stok")
    u.add_argument("--yorum", type=int, default=60, help="çekilecek AliExpress yorumu sayısı")
    u.add_argument("--kanal", choices=list(hesap.KANALLAR), default="site", help="satış kanalı (komisyon ve reklam payı)")
    u.set_defaults(f=urun)

    sk = alt.add_parser("skorla", help="kayıtlı ürün JSON'unu yeniden değerlendir (AliExpress'e gitmez)")
    sk.add_argument("json")
    sk.add_argument("--kelime", help="Türkçe pazar kelimesi (Trendyol/Trends için)")
    sk.add_argument("--trendyol", action="store_true", help="Trendyol rakiplerini yeniden çek (Apify, ücretli)")
    sk.add_argument("--senaryo", choices=["stok", "dogrudan"], default="stok")
    sk.add_argument("--kanal", choices=list(hesap.KANALLAR), default="site")
    sk.set_defaults(f=skorla)

    a = p.parse_args()
    try:
        a.f(a)
    except ae.DogrulamaGerekli as e:
        print(f"✗ AliExpress doğrulama istedi: {e}\n  Bir süre bekleyip tekrar dene (çok sık çalıştırma).")
        sys.exit(2)


if __name__ == "__main__":
    main()
