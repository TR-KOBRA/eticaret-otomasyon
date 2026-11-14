"""6 · Mağaza: platformdan bağımsız ürün paketi.

Çıktılar (proje/magaza/):
  shopify-urunler.csv   Shopify ürün içe aktarma dosyası (taslak durumda; paketler varyant olarak)
  index.html            tek dosyalık ürün sayfası önizlemesi (marka renkleri, güven şeridi, paketler, SSS)
                         — Next.js'e geçilirse tasarım referansı, ya da geçici açılış sayfası olarak kullanılabilir
Shopify API (isteğe bağlı): .env'de SHOPIFY_MAGAZA (xxx.myshopify.com) + SHOPIFY_ADMIN_TOKEN varsa ve
`--gonder` verilirse ürün **DRAFT** (yayında değil) olarak oluşturulur. Yayına alma her zaman elle yapılır.
"""
from __future__ import annotations

import csv
import html
import os
import shutil

import requests

from ortak import Proje

SHOPIFY_SURUM = os.getenv("SHOPIFY_API_SURUM", "2025-10")
CSV_KOLON = ["Handle", "Title", "Body (HTML)", "Vendor", "Type", "Tags", "Published", "Option1 Name", "Option1 Value",
             "Variant SKU", "Variant Grams", "Variant Inventory Tracker", "Variant Inventory Qty", "Variant Inventory Policy",
             "Variant Fulfillment Service", "Variant Price", "Variant Compare At Price", "Variant Requires Shipping",
             "Variant Taxable", "Image Src", "Image Position", "Image Alt Text", "SEO Title", "SEO Description", "Status"]


def govde_html(ic: dict) -> str:
    e = html.escape
    s = [f"<p><strong>{e(ic['alt_baslik'])}</strong></p>", "<ul>"] + [f"<li>{e(x)}</li>" for x in ic["fayda_maddeleri"]] + ["</ul>"]
    s += [f"<p>{e(x)}</p>" for x in ic["aciklama"]]
    s += ["<h3>Kullanım</h3><ol>"] + [f"<li>{e(x)}</li>" for x in ic["kullanim"]] + ["</ol>"]
    s += ["<h3>Kutu içeriği</h3><ul>"] + [f"<li>{e(x)}</li>" for x in ic["kutu_icerigi"]] + ["</ul>"]
    s += ["<h3>Özellikler</h3><table>"] + [f"<tr><td>{e(k)}</td><td>{e(str(v))}</td></tr>" for k, v in ic["ozellik_tablosu"].items()] + ["</table>"]
    return "\n".join(s)


def paketler(f: dict) -> list[tuple[str, float, float | None]]:
    tek = float(f.get("fiyat") or 0)
    return [("Tekli", tek, None), ("2'li paket", float(f.get("paket_2") or tek * 2), tek * 2),
            ("3'lü paket", float(f.get("paket_3") or tek * 3), tek * 3)]


def shopify_csv(p: Proje, ic: dict, m: dict, hedef):
    f = ic["fiyat"]
    tutamac = ic["url"]
    satirlar = []
    for i, (ad, fiyat, eski) in enumerate(paketler(f)):
        r = dict.fromkeys(CSV_KOLON, "")
        r.update({"Handle": tutamac, "Option1 Value": ad, "Variant SKU": f"{tutamac[:20]}-{i + 1}",
                  "Variant Price": f"{fiyat:.2f}", "Variant Compare At Price": f"{eski:.2f}" if eski else "",
                  "Variant Inventory Policy": "deny", "Variant Fulfillment Service": "manual",
                  "Variant Requires Shipping": "TRUE", "Variant Taxable": "TRUE", "Variant Grams": "",
                  "Variant Inventory Tracker": "shopify", "Variant Inventory Qty": "0"})
        if i == 0:
            r.update({"Title": ic["urun_adi"], "Body (HTML)": govde_html(ic), "Vendor": m["isim"], "Type": "",
                      "Tags": ", ".join(ic["etiketler"]), "Published": "FALSE", "Option1 Name": "Paket",
                      "SEO Title": ic["seo_baslik"], "SEO Description": ic["meta_aciklama"], "Status": "draft"})
        satirlar.append(r)
    with open(hedef, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_KOLON)
        w.writeheader()
        w.writerows(satirlar)


def sayfa_html(ic: dict, m: dict, gorseller: list[str]) -> str:
    e = html.escape
    ana, iki, notr = m.get("ana_renk", "#222"), m.get("ikinci_renk", "#888"), m.get("notr_renk", "#fafafa")
    bf, mf = m.get("baslik_fontu", "Inter"), m.get("metin_fontu", "Inter")
    font_url = "https://fonts.googleapis.com/css2?family=" + "&family=".join(
        x.replace(" ", "+") + ":wght@400;600;700" for x in dict.fromkeys([bf, mf])) + "&display=swap"
    pk = "".join(
        f'<label class="pk"><input type="radio" name="pk" {"checked" if i == 0 else ""}><span>{e(ad)}</span>'
        f'<b>{fiyat:,.0f} TL</b>{f"<s>{eski:,.0f} TL</s>" if eski else ""}</label>'
        for i, (ad, fiyat, eski) in enumerate(paketler(ic["fiyat"])))
    galeri = "".join(f'<img src="{e(g)}" alt="{e(ic["urun_adi"])}">' for g in gorseller[:6])
    sss = "".join(f"<details><summary>{e(x['soru'])}</summary><p>{e(x['cevap'])}</p></details>" for x in ic["sss"])
    serit = "".join(f"<div>{e(x)}</div>" for x in ic["guven_seridi"])
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(ic['seo_baslik'])}</title><meta name="description" content="{e(ic['meta_aciklama'])}">
<link rel="stylesheet" href="{font_url}">
<style>
:root{{--ana:{ana};--iki:{iki};--notr:{notr}}}
*{{box-sizing:border-box}}body{{margin:0;font-family:'{mf}',system-ui,sans-serif;color:#1d1d1f;background:#fff}}
header{{padding:14px 16px;text-align:center;font-family:'{bf}',sans-serif;font-weight:700;letter-spacing:.12em;color:var(--ana);border-bottom:1px solid #eee}}
.serit{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;background:var(--notr);padding:10px 16px;font-size:13px;text-align:center}}
main{{max-width:1080px;margin:0 auto;padding:24px 16px;display:grid;grid-template-columns:1.1fr 1fr;gap:32px}}
.galeri{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}.galeri img{{width:100%;border-radius:10px;background:var(--notr)}}
.galeri img:first-child{{grid-column:1/-1}}
h1{{font-family:'{bf}',sans-serif;font-size:28px;margin:0 0 6px}}.alt{{color:#555;margin:0 0 16px}}
ul.f{{padding-left:18px}}ul.f li{{margin:6px 0}}
.pk{{display:flex;align-items:center;gap:10px;border:2px solid #e5e5e5;border-radius:10px;padding:12px;margin:8px 0;cursor:pointer}}
.pk:has(input:checked){{border-color:var(--ana)}}.pk span{{flex:1}}.pk s{{color:#999;font-size:13px}}
.btn{{display:block;width:100%;padding:16px;border:0;border-radius:10px;background:var(--ana);color:#fff;font-size:17px;font-weight:600;cursor:pointer;margin-top:12px}}
section{{max-width:820px;margin:0 auto;padding:8px 16px 32px}}details{{border-bottom:1px solid #eee;padding:12px 0}}summary{{font-weight:600;cursor:pointer}}
footer{{background:var(--notr);padding:24px 16px;font-size:13px;color:#555;text-align:center}}
@media(max-width:760px){{main{{grid-template-columns:1fr}}.serit{{grid-template-columns:1fr 1fr}}}}
</style></head><body>
<header>{e(m['isim'].upper())}</header>
<div class="serit">{serit}</div>
<main><div class="galeri">{galeri}</div>
<div><h1>{e(ic['urun_adi'])}</h1><p class="alt">{e(ic['alt_baslik'])}</p>
<ul class="f">{''.join(f'<li>{e(x)}</li>' for x in ic['fayda_maddeleri'])}</ul>
{pk}<button class="btn" type="button">Sepete ekle</button>
<p style="font-size:13px;color:#666">Önizleme: ödeme altyapısı bağlı değildir.</p></div></main>
<section><h2>Ürün hakkında</h2>{''.join(f'<p>{e(x)}</p>' for x in ic['aciklama'])}
<h2>Sık sorulan sorular</h2>{sss}</section>
<footer>{e(m['isim'])} · [Firma unvanı] · [Adres] · [İletişim] · Mesafeli Satış Sözleşmesi · İade Koşulları · KVKK</footer>
</body></html>"""


def shopify_gonder(ic: dict, m: dict) -> dict:
    magaza, token = os.getenv("SHOPIFY_MAGAZA"), os.getenv("SHOPIFY_ADMIN_TOKEN")
    if not (magaza and token):
        return {"durum": "atlandı", "neden": ".env'de SHOPIFY_MAGAZA ve SHOPIFY_ADMIN_TOKEN yok"}
    url = f"https://{magaza}/admin/api/{SHOPIFY_SURUM}/graphql.json"
    h = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    q = """mutation($p: ProductCreateInput!){ productCreate(product:$p){ product{ id handle variants(first:1){nodes{id}} }
             userErrors{ field message } } }"""
    girdi = {"title": ic["urun_adi"], "descriptionHtml": govde_html(ic), "vendor": m["isim"], "tags": ic["etiketler"],
             "handle": ic["url"], "status": "DRAFT", "seo": {"title": ic["seo_baslik"], "description": ic["meta_aciklama"]}}
    r = requests.post(url, json={"query": q, "variables": {"p": girdi}}, headers=h, timeout=60)
    d = r.json()
    hata = (d.get("data") or {}).get("productCreate", {}).get("userErrors") or d.get("errors")
    if r.status_code != 200 or hata:
        return {"durum": "hata", "http": r.status_code, "hata": hata}
    urun = d["data"]["productCreate"]["product"]
    vid = urun["variants"]["nodes"][0]["id"]
    q2 = """mutation($pid: ID!, $v:[ProductVariantsBulkInput!]!){ productVariantsBulkUpdate(productId:$pid, variants:$v){
              userErrors{ field message } } }"""
    r2 = requests.post(url, json={"query": q2, "variables": {"pid": urun["id"],
                       "v": [{"id": vid, "price": str(ic["fiyat"]["fiyat"])}]}}, headers=h, timeout=60)
    return {"durum": "taslak oluşturuldu", "id": urun["id"], "handle": urun["handle"], "fiyat_guncelleme": r2.json(),
            "not": "Paket varyantlarını, görselleri ve yayına almayı Shopify panelinden yap."}


def calistir(p: Proje, args=None):
    ic = p.oku("icerik")
    m = p.marka()
    g = p.oku("gorsel") or {}
    kl = p.yol / "magaza"
    (kl / "img").mkdir(parents=True, exist_ok=True)
    gorseller = []
    for x in g.get("gorseller", []):
        if x["dosya"].startswith("00-logo"):
            continue
        src = p.yol / "gorseller" / x["dosya"]
        if src.exists():
            shutil.copy(src, kl / "img" / x["dosya"])
            gorseller.append(f"img/{x['dosya']}")
    shopify_csv(p, ic, m, kl / "shopify-urunler.csv")
    (kl / "index.html").write_text(sayfa_html(ic, m, gorseller), encoding="utf-8")
    api = shopify_gonder(ic, m) if getattr(args, "gonder", False) else {"durum": "kuru çalıştırma (--gonder verilmedi)"}

    f = ic["fiyat"]
    md = [f"# Mağaza paketi — {m['isim']}", "",
          f"- **Ürün sayfası önizlemesi:** `magaza/index.html` (tarayıcıda aç; {len(gorseller)} görsel)",
          "- **Shopify içe aktarma:** `magaza/shopify-urunler.csv` → Shopify yönetici → Ürünler → İçe aktar "
          "(taslak olarak gelir; görselleri elle yükle)",
          f"- **Shopify API:** {api['durum']}" + (f" — {api.get('neden') or api.get('hata') or ''}" if api.get('neden') or api.get('hata') else ""), "",
          "## Paketler (varyant)", "", "| Paket | Fiyat | Liste fiyatı |", "|---|---|---|"]
    md += [f"| {ad} | {fi:,.0f} TL | {f'{es:,.0f} TL' if es else '-'} |" for ad, fi, es in paketler(f)]
    md += ["", "## Kurulum kontrol listesi (kaynaklar/ozetler/magaza.md)", ""] + [f"- [ ] {x}" for x in [
        "Domain bağla (marka adımındaki boş .com ya da .com.tr) — satın alma senin onayınla",
        "Tema: hızlı, sade, mobil uyumlu (Shopify'da ücretsiz Dawn yeterli; lisanssız/nulled tema KULLANMA)",
        "Renkler ve fontlar: " + f"{m.get('ana_renk')} / {m.get('ikinci_renk')} / {m.get('notr_renk')} · {m.get('baslik_fontu')} + {m.get('metin_fontu')}",
        "Ödeme: iyzico veya PayTR (komisyon ve hesaba geçiş süresini öğren); kapıda ödeme isteğe bağlı",
        "Kargo: anlaşmalı firma, ücretsiz kargo eşiği marja göre",
        "Güven şeridi: " + " · ".join(ic["guven_seridi"]),
        "Yasal sayfalar: `yasal/` klasöründeki şablonları doldur, hukukçuya kontrol ettir, footer'a bağla",
        "Uygulamalar: yalnızca gerçek müşteri yorumu toplayan bir yorum uygulaması (sahte/ithal yorum yok)",
        "Meta Pixel + Conversions API kurulumu (reklam adımı için şart)",
        "Telefonla baştan sona test siparişi ver",
    ]]
    p.yaz("magaza", {"api": api, "gorseller": gorseller, "dosyalar": ["magaza/index.html", "magaza/shopify-urunler.csv"]}, md)
