"""11 · Operasyon: müşteri mesaj şablonları, SSS hızlı yanıtları, stok yeniden sipariş eşiği, haftalık kâr tablosu.

  python hat.py calistir <proje> operasyon                  # şablonlar + boş haftalık tablo
  python hat.py calistir <proje> operasyon --csv haftalik.csv  # doldurulmuş tablodan net kâr raporu
Mesajlar otomatik gönderilmez; kargo/ödeme entegrasyonları seçilen altyapıya göre kurulur.
"""
from __future__ import annotations

import csv
from pathlib import Path

from analiz import _sayi
from ortak import Proje, tl

KOLON = ["hafta", "ziyaret", "siparis", "ciro_tl", "reklam_tl", "urun_maliyeti_tl", "kargo_tl", "komisyon_tl",
         "iade_adet", "iade_tutar_tl", "diger_gider_tl"]


def sablonlar(marka: str) -> dict:
    return {
        "Sipariş alındı": f"Merhaba {{ad}}, {marka} siparişin bize ulaştı (#{{siparis_no}}). En geç {{gun}} iş günü içinde "
                          "kargoya vereceğiz, takip numarasını buradan ileteceğiz. Sorun olursa bu numaradan yazabilirsin.",
        "Kargoya verildi": f"Merhaba {{ad}}, {marka} siparişin yola çıktı 🚚 Kargo: {{firma}} · Takip no: {{takip_no}} · "
                           "{takip_link}",
        "Teslim edildi + geri bildirim": f"Merhaba {{ad}}, siparişin teslim edilmiş görünüyor. Her şey yolunda mı? Ürünle ilgili "
                                         "düşünceni yazarsan çok seviniriz; istersen kullanırken kısa bir video/fotoğraf da "
                                         "paylaşabilirsin (izin verirsen Instagram'da paylaşırız).",
        "Gecikme bilgisi": f"Merhaba {{ad}}, siparişinde {{neden}} nedeniyle {{gun}} günlük gecikme var, kusura bakma. "
                           "Yeni tahmini teslim: {tarih}. İstersen iptal edip ücret iadesi de yapabiliriz.",
        "İade talebi": "Merhaba {ad}, iade talebini aldık. Ürünü kullanılmamış ve kutusuyla {iade_adresi} adresine "
                       "{kargo_kodu} anlaşmalı kargo koduyla gönderebilirsin. Ürün bize ulaşınca 14 gün içinde ödemeni iade ederiz.",
        "Hasarlı ürün": "Çok üzgünüz {ad}. Hasarı gösteren bir fotoğraf gönderebilir misin? Kargo ücreti bize ait olacak şekilde "
                        "hemen yenisini gönderiyoruz / dilersen ücret iadesi yapıyoruz.",
    }


def haftalik_rapor(yol: Path) -> tuple[list[dict], list[str]]:
    ham = yol.read_text(encoding="utf-8-sig").splitlines()
    ayr = ";" if ham[0].count(";") >= ham[0].count(",") else ","
    satir = [r for r in csv.DictReader(ham, delimiter=ayr) if (r.get("hafta") or "").strip()]
    md = ["| Hafta | Sipariş | Dönüşüm | Ciro | Reklam | ROAS | İade % | Net kâr | Net marj |", "|---|---|---|---|---|---|---|---|---|"]
    out = []
    for r in satir:
        v = {k: _sayi(r.get(k)) for k in KOLON[1:]}
        gider = sum(v[k] for k in ("reklam_tl", "urun_maliyeti_tl", "kargo_tl", "komisyon_tl", "iade_tutar_tl", "diger_gider_tl"))
        net = v["ciro_tl"] / 1.2 - gider          # ciro KDV dahil varsayılır
        x = {"hafta": r["hafta"], **v, "net_kar_tl": round(net, 2),
             "net_marj": round(net / v["ciro_tl"] * 100, 1) if v["ciro_tl"] else None,
             "roas": round(v["ciro_tl"] / v["reklam_tl"], 2) if v["reklam_tl"] else None,
             "donusum": round(v["siparis"] / v["ziyaret"] * 100, 2) if v["ziyaret"] else None,
             "iade_orani": round(v["iade_adet"] / v["siparis"] * 100, 1) if v["siparis"] else None}
        out.append(x)
        md.append(f"| {x['hafta']} | {v['siparis']:.0f} | %{x['donusum'] or 0} | {tl(v['ciro_tl'])} | {tl(v['reklam_tl'])} | "
                  f"{x['roas'] or '-'} | %{x['iade_orani'] or 0} | {tl(net)} | %{x['net_marj'] or 0} |")
    return out, md


def calistir(p: Proje, args=None):
    m = p.marka()
    ic = p.oku("icerik") or {}
    kl = p.yol / "operasyon"
    kl.mkdir(exist_ok=True)
    sb = sablonlar(m["isim"])
    bos = kl / "haftalik.csv"
    if not bos.exists():
        with open(bos, "w", newline="", encoding="utf-8-sig") as fh:
            csv.writer(fh, delimiter=";").writerow(KOLON)
    kargo = sorted(p.urun.get("kargo") or [], key=lambda k: (k.get("gun_max") or 999))
    tedarik_gun = (kargo[0].get("gun_max") if kargo else None) or 30
    md = [f"# Operasyon — {m['isim']}", "", "## Müşteri mesaj şablonları (WhatsApp / SMS / e-posta)", "",
          "Süslü parantezli alanları doldur. Ticari ileti (kampanya) göndereceksen İYS izni gerekir; bu şablonlar sipariş bilgilendirmesidir.", ""]
    for ad, metin in sb.items():
        md += [f"**{ad}**", "", f"> {metin}", ""]
    md += ["## SSS hızlı yanıtları", ""] + [f"- **{x['soru']}** {x['cevap']}" for x in ic.get("sss", [])]
    md += ["", "## Stok ve nakit", "",
           f"- Yeniden sipariş eşiği = günlük ortalama satış × ({tedarik_gun} gün tedarik + 7 gün emniyet). "
           f"Ör. günde 3 satışta {3 * (tedarik_gun + 7)} adet kaldığında sipariş ver.",
           "- İlk günden büyük stok alma; satış hızına göre büyü (kaynaklar/ozetler/fiyat-kar.md).",
           "- Kâr ≠ nakit: ödeme kuruluşundan para 3–7 günde geçer; reklam ve stok için nakit rezervi tut.", "",
           "## Haftalık tablo", "", f"`operasyon/haftalik.csv` dosyasını her hafta doldur (sütunlar: {', '.join(KOLON)}), sonra:",
           "`python hat.py calistir <proje> operasyon --csv operasyon/haftalik.csv`", ""]
    rapor = []
    kaynak = getattr(args, "csv", None)
    if kaynak:
        yol = Path(kaynak) if Path(kaynak).is_absolute() or Path(kaynak).exists() else p.yol / kaynak
        rapor, tablo = haftalik_rapor(yol)
        md += tablo
        if rapor and rapor[-1]["net_marj"] is not None and rapor[-1]["net_marj"] < 20:
            md += ["", f"⚠ Son hafta net marj %{rapor[-1]['net_marj']} < %20 hedefi: reklam payını, iade nedenlerini ve fiyatı gözden geçir."]
    p.yaz("operasyon", {"sablonlar": sb, "haftalik": rapor, "tedarik_gun": tedarik_gun}, md)
