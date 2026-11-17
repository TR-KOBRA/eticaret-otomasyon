"""20 puanlık hızlı skor kartı (kaynaklar/ozetler/arastirma.md, MC2-06).

10 kriter × 0/1/2. 15–20 TESTE AL · 10–14 İYİLEŞTİR · 0–9 ELE.
Ölçülebilen 4 kriter veriden, yorum gerektiren 5 kriter Gemini'den (gerekçesiyle),
"rakiplerden ayrışabilir" rakip_analiz.py'den gelir.
"""
from __future__ import annotations

import gemini

KRITERLER = [
    ("net_problem", "Net bir problem çözüyor"),
    ("video_anlatim", "Videoda kolay anlatılıyor"),
    ("dikkat_cekici_demo", "Dikkat çekici demo"),
    ("genis_kitle", "Geniş hedef kitle"),
    ("kar_marji", "Yeterli kâr marjı"),
    ("kargolama", "Kargolaması kolay"),
    ("teklif", "Teklif/paket geliştirilebilir"),
    ("ayrisabilir", "Rakiplerden ayrışabilir"),
    ("tedarik", "Tedarik güvenilir"),
    ("memnuniyet", "Müşteri memnuniyeti yönetilebilir"),
]
GEMINI_KRITERLERI = ["net_problem", "video_anlatim", "dikkat_cekici_demo", "genis_kitle", "teklif"]

SISTEM = (
    "Türkiye'de Meta reklamıyla satış yapacak bir e-ticaret girişimcisi için ürün değerlendiriyorsun. "
    "Her kriteri 0/1/2 puanla: 0 = sağlamıyor, 1 = kısmen, 2 = açıkça sağlıyor. Cömert olma; "
    "kanıt yoksa 1'i geçme. Gerekçe tek cümle, Türkçe ve verilen veriye dayalı olsun. "
    "video_anlatim ve dikkat_cekici_demo ürünün POTANSİYELİdir: satıcının videosu olup olmaması puanı etkilemez, "
    "biz kendi videomuzu çekeceğiz. Kancalarda başka marka/ünlü parfüm/otel adı, 'muadil/benzeri' iması, "
    "sağlık/tedavi vaadi ve abartılı iddia kullanma."
)


def _sema():
    kr = {"type": "OBJECT", "properties": {"puan": {"type": "INTEGER"}, "gerekce": {"type": "STRING"}},
          "required": ["puan", "gerekce"]}
    return {"type": "OBJECT",
            "properties": {**{k: kr for k in GEMINI_KRITERLERI},
                           "hook_ornekleri": {"type": "ARRAY", "items": {"type": "STRING"}},
                           "paket_onerisi": {"type": "STRING"}},
            "required": GEMINI_KRITERLERI + ["hook_ornekleri", "paket_onerisi"]}


def _kar(secenekler: list[dict], rk: dict | None) -> tuple[int, str, list[str]]:
    bayrak = []
    d = next((s for s in secenekler if s["secenek"] == "dengeli"), None)
    p = next((s for s in secenekler if s["secenek"] == "premium"), None)
    mn = next((s for s in secenekler if s["secenek"].startswith("minimum")), None)
    if not d:
        return 0, "fiyat seçeneği hesaplanamadı", bayrak
    if (rk or {}).get("benzer_yok"):
        bayrak.append("Trendyol'da aynı ürün bulunamadı: fiyat piyasayla doğrulanamadı (boşluk olabilir ya da talep yok)")
        return 1, (f"aynı ürün Trendyol'da yok ({(rk or {}).get('benzer_sayisi', 0)} eşleşme); maliyet × 3 fiyatında net marj "
                   f"%{d['marj_yuzde']} — piyasa doğrulaması yok"), bayrak
    kaynak = "rakip medyanı" if (rk or {}).get("ozet", {}).get("medyan") else "maliyet × 3"
    if d["hedefe_uygun"]:
        puan, g = 2, f"{kaynak} ({d['fiyat']} TL) fiyatında net marj %{d['marj_yuzde']} (hedef ≥ %20)"
    elif d["marj_yuzde"] >= 10 or (p and p["hedefe_uygun"]):
        puan, g = 1, f"{kaynak} fiyatında net marj %{d['marj_yuzde']}; hedefe ancak daha yüksek fiyatta ulaşılıyor"
        if p and p["hedefe_uygun"]:
            bayrak.append("Kâr yalnızca yüksek satış fiyatına bağlı")
    else:
        puan, g = 0, f"{kaynak} fiyatında net marj %{d['marj_yuzde']}"
    if mn and kaynak == "rakip medyanı" and mn["fiyat"] > d["fiyat"]:
        bayrak.append(f"%20 marj için gereken minimum fiyat ({mn['fiyat']} TL) rakip medyanının ({d['fiyat']} TL) üstünde")
    return puan, g, bayrak


def _kargolama(kr: dict) -> tuple[int, str]:
    p = {"dusuk": 2, "orta": 1, "yuksek": 0}[kr["seviye"]]
    return p, ("belirgin kargo riski yok" if not kr["nedenler"] else "; ".join(kr["nedenler"]))


def _tedarik(u: dict) -> tuple[int, str]:
    m = u.get("magaza") or {}
    try:
        olumlu = float(m.get("olumlu_oran") or 0)
    except ValueError:
        olumlu = 0
    kargo = u.get("kargo") or []
    hizli_takipli = any(k.get("takip") and (k.get("gun_max") or 99) <= 20 for k in kargo)
    kosul = {
        f"mağaza olumlu %{olumlu:g} (≥95)": olumlu >= 95,
        f"mağaza {m.get('toplam') or 0} değerlendirme (≥1000)": int(m.get("toplam") or 0) >= 1000,
        f"ürün {u.get('satis') or 0} satış (≥100)": (u.get("satis") or 0) >= 100,
        "≤20 gün takipli kargo": hizli_takipli,
    }
    n = sum(kosul.values())
    puan = 2 if n >= 4 else (1 if n >= 2 else 0)
    g = "; ".join(("✓ " if v else "✗ ") + k for k, v in kosul.items())
    return puan, g + ". Numune ile doğrula; tek tedarikçiye bağlı kalma."


def _memnuniyet(u: dict, iade_orani: float) -> tuple[int, str]:
    oz = (u.get("yorumlar") or {}).get("ozet") or {}
    toplam = oz.get("toplam") or u.get("puan_sayisi") or 0
    puan_ort = oz.get("ortalama") or u.get("puan") or 0
    yz = oz.get("yildiz") or {}
    dusuk = sum(int(yz.get(str(i)) or yz.get(i) or 0) for i in (1, 2, 3))
    oran = dusuk / toplam if toplam else None
    if puan_ort >= 4.6 and (oran is None or oran < 0.10):
        p = 2
    elif puan_ort >= 4.3:
        p = 1
    else:
        p = 0
    notlar = [f"puan {puan_ort} ({toplam} yorum)"] + ([f"1–3★ oranı %{oran * 100:.0f}"] if oran is not None else [])
    if toplam < 20:
        p = min(p, 1)
        notlar.append("yorum az, kalite kanıtlanmamış")
    if iade_orani >= 0.25:
        p = max(0, p - 1)
        notlar.append("beden/uyum kaynaklı yüksek iade riski")
    return p, "; ".join(notlar)


def _gemini_istem(u, secenekler, rk, tr, analiz) -> str:
    oz = u.get("ozellikler") or {}
    d = next((s for s in secenekler if s["secenek"] == "dengeli"), {})
    s = [f"Ürün: {u.get('baslik')}",
         "Özellikler: " + "; ".join(f"{k}: {v}" for k, v in list(oz.items())[:25]),
         "Açıklama: " + " ".join((u.get("aciklama") or {}).get("metin") or [])[:1200],
         f"Ürün videosu var: {'evet' if u.get('video') else 'hayır'} · görsel sayısı {len(u.get('gorseller') or [])}",
         f"Varyantlar: {', '.join(str(v.get('ad')) for v in (u.get('varyantlar') or [])[:12])}",
         f"Planlanan satış fiyatı: {d.get('fiyat')} TL"]
    if tr and not tr.get("hata"):
        for k, v in (tr.get("kelimeler") or {}).items():
            s.append(f"Google Trends TR '{k}': ortalama ilgi {v['ortalama']}/100, son 3 ay değişim %{v['degisim_yuzde']}")
    o = (rk or {}).get("ozet") or {}
    if o.get("medyan"):
        s.append(f"Trendyol: {o['urun_sayisi']} rakip ürün, medyan {o['medyan']} TL, toplam {o['toplam_degerlendirme']} değerlendirme")
    if analiz and analiz.get("sikayetler") is not None:
        s.append("Yorumlardan şikâyetler: " + "; ".join(x["konu"] for x in analiz.get("sikayetler") or []) or "-")
    s.append("Kriterler: net_problem (net bir problemi çözüyor mu), video_anlatim (faydası ilk 3 saniyede videoda "
             "gösterilebilir mi), dikkat_cekici_demo (merak uyandıran, durdurtan bir demo var mı), genis_kitle "
             "(Türkiye'de geniş ve ölçeklenebilir kitle; Trends/Trendyol verisini dikkate al), teklif (2'li/3'lü paket, "
             "hediye, tamamlayıcı ürün, upsell kurulabilir mi). Ayrıca sağlık/abartı vaadi içermeyen 3 reklam kancası "
             "(ilk 3 saniye) ve tek cümlelik paket önerisi ver.")
    return "\n".join(s)


def puanla(u: dict, secenekler: list[dict], kargo_risk: dict, iade_orani: float,
           rk: dict | None = None, tr: dict | None = None, analiz: dict | None = None,
           riskler: list[dict] | None = None) -> dict:
    sonuc: dict[str, dict] = {}
    bayraklar: list[str] = []

    p, g, b = _kar(secenekler, rk)
    sonuc["kar_marji"] = {"puan": p, "gerekce": g, "kaynak": "veri"}
    bayraklar += b
    p, g = _kargolama(kargo_risk)
    sonuc["kargolama"] = {"puan": p, "gerekce": g, "kaynak": "veri"}
    if kargo_risk["seviye"] == "yuksek":
        bayraklar.append("Çok kırılgan/ağır/sorunlu kargo")
    p, g = _tedarik(u)
    sonuc["tedarik"] = {"puan": p, "gerekce": g, "kaynak": "veri"}
    if p == 0:
        bayraklar.append("Kalite ve tedarik belirsiz")
    p, g = _memnuniyet(u, iade_orani)
    sonuc["memnuniyet"] = {"puan": p, "gerekce": g, "kaynak": "veri"}

    if analiz and "ayrisma_puani" in analiz:
        sonuc["ayrisabilir"] = {"puan": analiz["ayrisma_puani"], "gerekce": analiz.get("ayrisma_gerekce", ""),
                                "kaynak": "gemini (yorum analizi)"}

    ek = {}
    if gemini.var_mi():
        try:
            gj = gemini.json_sor(_gemini_istem(u, secenekler, rk, tr, analiz), _sema(), sistem=SISTEM, sicaklik=0.2)
            for k in GEMINI_KRITERLERI:
                sonuc[k] = {"puan": max(0, min(2, int(gj[k]["puan"]))), "gerekce": gj[k]["gerekce"], "kaynak": "gemini"}
            ek = {"hook_ornekleri": gj.get("hook_ornekleri") or [], "paket_onerisi": gj.get("paket_onerisi"),
                  "model": gemini.son_model()}
            if sonuc["video_anlatim"]["puan"] == 0:
                bayraklar.append("Fayda videoda anlaşılmıyor")
        except Exception as e:
            ek = {"gemini_hata": str(e)[:300]}

    kriterler = []
    for k, ad in KRITERLER:
        v = sonuc.get(k) or {"puan": None, "gerekce": "puanlanamadı (Gemini/rakip verisi yok)", "kaynak": "yok"}
        kriterler.append({"kod": k, "ad": ad, **v})
    toplam = sum(x["puan"] or 0 for x in kriterler)
    eksik = sum(1 for x in kriterler if x["puan"] is None)
    en_fazla = toplam + 2 * eksik

    yuksek = [r["konu"] for r in (riskler or []) if r["seviye"] == "yuksek"]
    if yuksek:
        karar = "ELE"
        bayraklar = [f"Yüksek risk: {x}" for x in yuksek] + bayraklar
    elif ek.get("gemini_hata") or (eksik and en_fazla >= 15 > toplam):
        # Yapay zekâ kriterleri puanlanamadıysa ürün ELE edilmez: veri eksik, sonra yeniden puanlanır
        karar = "EKSİK VERİ"
        if ek.get("gemini_hata"):
            bayraklar = ["Gemini puanlayamadı → `arastir.py skorla <json>` ile yeniden puanla"] + bayraklar
    elif toplam >= 15 and (sonuc.get("kar_marji") or {}).get("puan") == 0:
        # Piyasa fiyatında kâr yoksa diğer kriterler ne kadar iyi olursa olsun test edilmez (fiyat-kar.md: hedef net marj ≥ %20)
        karar = "İYİLEŞTİR"
        bayraklar = ["Rakip fiyatında net kâr yok → maliyeti düşür, paket/teklifle fiyatı yükselt ya da ele"] + bayraklar
    elif toplam >= 15:
        karar = "TESTE AL"
    elif toplam >= 10:
        karar = "İYİLEŞTİR"
    else:
        karar = "ELE"
    return {"kriterler": kriterler, "toplam": toplam, "en_fazla_mumkun": en_fazla, "eksik_kriter": eksik,
            "karar": karar, "kirmizi_bayraklar": bayraklar, **ek}
