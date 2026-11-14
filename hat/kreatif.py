"""8 · Kreatif: 10 hook, 5 başlık, 3 CTA, 3 tonda ana metin, 3 UGC senaryosu (30 sn), 3–4 test açısı (kaynaklar/ozetler/reklam.md)."""
from __future__ import annotations

from ortak import Proje, metin_json, ozet

SEMA = {"type": "OBJECT", "properties": {
    "acilar": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
        "ad": {"type": "STRING"}, "fikir": {"type": "STRING"}, "hooklar": {"type": "ARRAY", "items": {"type": "STRING"}}},
        "required": ["ad", "fikir", "hooklar"]}, "description": "test kampanyasındaki her reklam seti için bir kanca açısı"},
    "basliklar": {"type": "ARRAY", "items": {"type": "STRING"}},
    "cta": {"type": "ARRAY", "items": {"type": "STRING"}},
    "ana_metinler": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
        "ton": {"type": "STRING", "enum": ["mizahi", "ciddi", "duygusal"]}, "metin": {"type": "STRING"}},
        "required": ["ton", "metin"]}},
    "ugc": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
        "aci": {"type": "STRING"},
        "sahneler": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "zaman": {"type": "STRING"}, "goruntu": {"type": "STRING"}, "ses": {"type": "STRING"}},
            "required": ["zaman", "goruntu", "ses"]}}},
        "required": ["aci", "sahneler"]}},
}, "required": ["acilar", "basliklar", "cta", "ana_metinler", "ugc"]}


def calistir(p: Proje, args=None):
    m = p.marka()
    ic = p.oku("icerik") or {}
    istem = "\n".join([
        p.urun_ozeti(),
        f"Marka: {m['isim']} · ton: {m.get('ton')} · hedef kitle: {m.get('hedef_kitle')}",
        "Fayda maddeleri: " + "; ".join(ic.get("fayda_maddeleri", [])),
        "", "Bilgi bankası (reklam):", ozet("reklam")[:2500], "",
        "Görev: Meta (Instagram/Facebook) test kampanyası için kreatif paketi. 4 farklı kanca AÇISI (ör. problem, demo/sonuç, "
        "hediye/an, karşılaştırma — ürüne uygun olanları seç), her açı için 3 hook (ilk 3 saniye, ≤ 10 kelime) → toplam 12; "
        "5 başlık (≤ 8 kelime); 3 CTA; aynı mesajın mizahi/ciddi/duygusal tonda ≤ 60 kelimelik ana metni; "
        "3 UGC senaryosu (30 sn: 0–3 hook, 3–15 problem + ürün, 15–25 kullanım + fayda, 25–30 CTA) sahne sahne, "
        "çekilebilir ve gerçek ürünle gösterilebilir şeyler. Önce/sonra iddiası, sağlık etkisi, sahte müşteri yorumu yok; "
        "UGC'yi gerçek bir kişi kendi deneyimiyle çekecek.",
    ])
    g = metin_json(istem, SEMA, sicaklik=0.9)
    md = [f"# Kreatif — {m['isim']}", "", "## Test açıları (her biri bir reklam seti)", ""]
    for i, a in enumerate(g["acilar"], 1):
        md += [f"### Açı {i}: {a['ad']}", a["fikir"], ""] + [f"- {h}" for h in a["hooklar"]] + [""]
    md += ["## Başlıklar", ""] + [f"- {x}" for x in g["basliklar"]]
    md += ["", "## CTA", ""] + [f"- {x}" for x in g["cta"]]
    md += ["", "## Ana metinler (A/B ton testi)", ""] + [f"**{x['ton']}:** {x['metin']}\n" for x in g["ana_metinler"]]
    md += ["## UGC senaryoları (30 sn)", ""]
    for u in g["ugc"]:
        md += [f"### {u['aci']}", "", "| Zaman | Görüntü | Ses/yazı |", "|---|---|---|"]
        md += [f"| {s['zaman']} | {s['goruntu']} | {s['ses']} |" for s in u["sahneler"]] + [""]
    md += ["Onay: metinleri oku, ürünün gerçekten yapamadığı bir şey vaat edilmiyorsa `hat.py onayla <proje> kreatif`."]
    p.yaz("kreatif", g, md)
