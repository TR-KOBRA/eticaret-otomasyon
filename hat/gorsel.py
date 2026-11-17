"""5 · Görsel: satıcının ürün fotoğraflarını referans alıp Gemini ile mağaza/Instagram görselleri üretir + logo (wordmark).

Kural: ürün referans fotoğraftakiyle AYNI görünmeli (şekil, renk, oran, parça sayısı). Yanıltıcı görsel = müşteri
güveni ve reklam hesabı riski. Sonuçları insan onaylar: python hat.py onayla <proje> gorsel
Model: GEMINI_GORSEL_MODEL (varsayılan gemini-3.1-flash-image; kalite için gemini-3-pro-image).
"""
from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ortak import Proje, gorsel_modeli, gorsel_uret, indir, tr_upper

SADAKAT = ("The product must look EXACTLY like in the reference photo(s): same shape, proportions, colors, materials, "
           "number of parts and size. Do not add features, accessories, labels or text that are not in the reference. "
           "Remove any third-party brand names or logos from the product. Photorealistic, no watermark.")

PLAN = [
    ("01-beyaz-zemin", "1:1", "Clean e-commerce main image: the product centered on a pure white (#FFFFFF) seamless background, "
                              "soft studio lighting, subtle natural shadow, product fills ~70% of the frame."),
    ("02-yasam-1", "4:5", "Lifestyle photo for Instagram: the product in use in a real Turkish home setting that fits this visual "
                          "language: {gorsel_dil}. Natural light, the product is the clear focal point."),
    ("03-yasam-2", "4:5", "Second lifestyle photo, different scene and angle from a typical day of the target customer "
                          "({hedef_kitle}). Warm, authentic, not overly staged."),
    ("04-detay", "1:1", "Close-up detail shot showing the product's material and build quality, shallow depth of field, "
                        "background in the brand neutral color {notr_renk}."),
    ("05-kapak", "4:5", "Instagram carousel cover: the product on a solid background in brand color {ana_renk}, generous empty "
                        "space at the top third for a headline that will be added later. No text in the image."),
]


def _font(boyut: int, kalin: bool = True):
    for ad in (["segoeuib.ttf", "arialbd.ttf"] if kalin else ["segoeui.ttf", "arial.ttf"]):
        yol = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / ad
        if yol.exists():
            return ImageFont.truetype(str(yol), boyut)
    return ImageFont.load_default()


def wordmark(isim: str, renk: str, zemin: str, hedef: Path) -> Path:
    """Sade yazı logo (geçici). Kalıcı logo için logo brifini bir tasarımcıya ver."""
    img = Image.new("RGB", (1080, 1080), zemin or "#FFFFFF")
    d = ImageDraw.Draw(img)
    f = _font(170)
    metin = tr_upper(isim)
    x0, y0, x1, y1 = d.textbbox((0, 0), metin, font=f)
    d.text(((1080 - (x1 - x0)) / 2 - x0, (1080 - (y1 - y0)) / 2 - y0), metin, font=f, fill=renk or "#111111")
    img.save(hedef)
    return hedef


def calistir(p: Proje, args=None):
    m = p.marka()
    kl = p.yol / "gorseller"
    (kl / "kaynak").mkdir(parents=True, exist_ok=True)
    refs = []
    for i, url in enumerate((p.urun.get("gorseller") or [])[:3], 1):
        r = indir(url, kl / "kaynak" / f"ref{i}")
        if r:
            refs.append(r)
    if not refs:
        raise RuntimeError("Satıcı görselleri indirilemedi; referanssız üretim yapılmaz (ürün yanlış görünür).")

    ciktilar, hatalar = [], []
    wm = wordmark(m["isim"], m.get("ana_renk"), m.get("notr_renk"), kl / "00-logo-yazi.png")
    ciktilar.append({"dosya": wm.name, "tur": "logo (geçici wordmark)"})
    for ad, oran, sablon in PLAN:
        istem = sablon.format(gorsel_dil=m.get("gorsel_dil", ""), hedef_kitle=m.get("hedef_kitle", ""),
                              notr_renk=m.get("notr_renk", "#F5F5F5"), ana_renk=m.get("ana_renk", "#333333"))
        istem = f"{istem}\n\n{SADAKAT}"
        try:
            yol = gorsel_uret(istem, refs, kl / ad, oran)
            ciktilar.append({"dosya": yol.name, "tur": ad, "oran": oran, "istem": istem})
            print(f"    · {yol.name}")
        except Exception as e:
            hatalar.append({"tur": ad, "hata": str(e)[:300]})
            print(f"    ✗ {ad}: {str(e)[:120]}")
            if "429" in str(e) or "quota" in str(e).lower():
                break
    if len(ciktilar) == 1:  # sadece logo: üretim yapılamadı → satıcı fotoğrafları geçici olarak kullanılır
        import shutil
        for r in refs:
            hedef = kl / f"satici-{r.name}"
            shutil.copy(r, hedef)
            ciktilar.append({"dosya": hedef.name, "tur": "satıcı fotoğrafı (GEÇİCİ — kullanım izni sor, marka adlarını kırp)"})
        if any("429" in h["hata"] for h in hatalar):
            hatalar.insert(0, {"tur": "kota", "hata": "Gemini görsel modelleri ücretsiz katmanda kapalı (günlük kota 0). "
                               "Google AI Studio → Billing ile faturalandırmayı aç, sonra `hat.py calistir <proje> gorsel`."})
    md = [f"# Görseller — {m['isim']}", "", f"Model: `{gorsel_modeli()}` · referans: {len(refs)} satıcı fotoğrafı "
          "(`gorseller/kaynak/`)", "",
          "**Onaydan önce her görseli referansla karşılaştır:** ürün şekli, rengi, boyutu ve parçaları aynı mı? "
          "Fark varsa o görseli sil ya da yeniden üret (`hat.py calistir <proje> gorsel`).", ""]
    md += [f"![{c['tur']}](gorseller/{c['dosya']})" for c in ciktilar]
    if hatalar:
        md += ["", "## Üretilemeyenler", ""] + [f"- {h['tur']}: {h['hata']}" for h in hatalar]
    md += ["", f"**Logo brifi (tasarımcı için):** {m.get('logo_brifi', '-')}"]
    p.yaz("gorsel", {"referanslar": [r.name for r in refs], "gorseller": ciktilar, "hatalar": hatalar,
                     "model": gorsel_modeli()}, md)
