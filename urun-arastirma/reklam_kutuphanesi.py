"""Meta Reklam Kütüphanesi (Türkiye) — bir anahtar kelimede kaç reklam ve kaç farklı reklamveren var?

Mert Kurtul ölçüsü: aynı ürünü ~20 kişi reklamlıyorsa pazarlama açıları tükenmiştir. Ürün ne kadar süredir reklamdaysa
o kadar sattığı düşünülür (uzun yayın = olumlu sinyal).

Yöntem ve sınırlar:
- Meta'nın resmî API'si Türkiye'deki ticari reklamları vermez; herkese açık kütüphane sayfası okunur.
- Normal Playwright tarayıcısı, gizlenme / bot-tespiti atlatma YOK (undetected-chromedriver kullanılmaz), tek sayfa, aramalar
  arasında bekleme. Giriş ya da doğrulama istenirse durur ve "erisilemedi" döner.
- İlk sayfadaki (~30) reklam kartı okunur; reklamveren sayısı bu kartlardaki farklı sayfa adlarıdır (alt sınır).

  python reklam_kutuphanesi.py "köpek havlama tasması" "tüy toplama rulosu"
"""
from __future__ import annotations

import datetime as dt
import re
import sys
import time
import urllib.parse

AYLAR = {"Oca": 1, "Şub": 2, "Mar": 3, "Nis": 4, "May": 5, "Haz": 6, "Tem": 7, "Ağu": 8, "Eyl": 9, "Eki": 10, "Kas": 11, "Ara": 12}
TARIH = re.compile(r"(\d{1,2}) (\w{3}) (\d{4}) tarihinde yayınlanmaya başladı")
SONUC = re.compile(r"~?\s?([\d.,]+)\s*sonuç")
BEKLE_SN = 6


def url(kelime: str) -> str:
    return ("https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=TR&media_type=all"
            f"&q={urllib.parse.quote(kelime)}&search_type=keyword_unordered")


def _coz(metin: str) -> dict:
    sonuc = SONUC.search(metin)
    toplam = int(sonuc.group(1).replace(".", "").replace(",", "")) if sonuc else 0
    satirlar = [s.strip() for s in metin.splitlines()]
    reklamverenler = []
    for i, s in enumerate(satirlar):
        if s == "Sponsorlu" and i > 0:
            ad = next((satirlar[j] for j in range(i - 1, max(-1, i - 4), -1) if satirlar[j] and satirlar[j] != "​"), None)
            if ad:
                reklamverenler.append(ad)
    tarihler = []
    for g, a, y in TARIH.findall(metin):
        if a in AYLAR:
            tarihler.append(dt.date(int(y), AYLAR[a], int(g)))
    bugun = dt.date.today()
    gunler = sorted((bugun - t).days for t in tarihler)
    farkli = sorted(set(reklamverenler))
    if len(farkli) >= 20:
        seviye = "doymus"
    elif len(farkli) >= 8:
        seviye = "kalabalik"
    else:
        seviye = "uygun"
    return {"toplam_reklam": toplam, "okunan_kart": len(tarihler), "reklamveren": len(farkli), "reklamverenler": farkli[:25],
            "en_uzun_gun": gunler[-1] if gunler else None, "medyan_gun": gunler[len(gunler) // 2] if gunler else None,
            "30_gun_ustu": sum(1 for g in gunler if g >= 30), "seviye": seviye if toplam else "reklam_yok"}


def ara(kelimeler: list[str], gorunur: bool = False) -> dict[str, dict]:
    from playwright.sync_api import sync_playwright
    out: dict[str, dict] = {}
    with sync_playwright() as p:
        b = p.chromium.launch(headless=not gorunur)
        sayfa = b.new_page(locale="tr-TR")
        for i, k in enumerate(kelimeler):
            if i:
                time.sleep(BEKLE_SN)
            try:
                sayfa.goto(url(k), timeout=60000)
                sayfa.wait_for_timeout(7000)
                metin = sayfa.inner_text("body")
            except Exception as e:  # noqa: BLE001
                out[k] = {"hata": f"{type(e).__name__}: {str(e)[:120]}"}
                continue
            if "Hiçbir reklam arama kriterinizle eşleşmiyor" in metin:
                out[k] = {**_coz(""), "seviye": "reklam_yok", "url": url(k)}
                continue
            if not SONUC.search(metin):
                out[k] = {"hata": "sonuç okunamadı (giriş/doğrulama istenmiş olabilir; atlatılmaz)", "url": url(k)}
                continue
            out[k] = {**_coz(metin), "url": url(k)}
        b.close()
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for k, v in ara(sys.argv[1:] or ["tasma"]).items():
        if v.get("hata"):
            print(f"{k}: {v['hata']}")
        else:
            print(f"{k}: ~{v['toplam_reklam']} reklam · ilk sayfada {v['reklamveren']} reklamveren ({v['seviye']}) · "
                  f"en uzun {v['en_uzun_gun']} gün · 30+ gün: {v['30_gun_ustu']}/{v['okunan_kart']}")


if __name__ == "__main__":
    main()
