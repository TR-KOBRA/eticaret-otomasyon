"""9 · Reklam: düşük bütçeli test planı (ABO + broad TR, bütçe = 3 × hedef CPA, 00:00 başlangıç) ve kapatma eşikleri.

Varsayılan kuru çalıştırmadır: Meta'ya hiçbir şey gönderilmez, API istekleri rapora yazılır.
`--gonder` + .env'de META_ERISIM_TOKENI, META_REKLAM_HESABI (act_...), META_PIXEL_ID varsa kampanya ve reklam setleri
**DURAKLATILMIŞ (PAUSED)** oluşturulur. Reklamları ekleme ve yayına alma (para harcatan adım) Reklam Yöneticisi'nde elle yapılır.
Bütçe (İleri Seviye Reklamcılık 8–9, 13): günlük toplam ≈ hedef CPA × 3; set başı en az 100 TL ve en az 0,4 × hedef CPA
(böylece "2 × hedef CPA harca, 0 satış → kapat" kuralı 5 günlük testte çalışabilir); düşük bütçe çok sete bölünmez (en fazla 4).
Seçimler: gunluk_butce (TL, toplam), set_butce (TL), set_sayisi, yas_min (22), yas_max (55)
"""
from __future__ import annotations

import datetime as dt
import json
import os

import requests

from ortak import Proje, tl

API = os.getenv("META_API_SURUM", "v24.0")


def butce_hesapla(hedef_cpa, aci_sayisi: int, gunluk=None, set_butce=None, set_sayisi=None) -> dict:
    """Ders kuralları: günlük ≈ hedef CPA × 3; set başı ≥ 100 TL ve ≥ 0,4 × hedef CPA (5 günde 2 × hedef CPA'ya ulaşsın);
    bütçe yetmiyorsa set sayısı azaltılır (en az 1, en fazla 4 ve açı sayısı)."""
    uyarilar = []
    onerilen = round(3 * hedef_cpa, 2) if hedef_cpa else 500.0
    if not hedef_cpa:
        uyarilar.append("Hedef CPA hesaplanamadı (fiyat/maliyet eksik) → varsayılan günlük 500 TL kullanıldı.")
    toplam = float(gunluk) if gunluk else onerilen
    min_set = max(100.0, round(0.4 * hedef_cpa, 2)) if hedef_cpa else 100.0
    ust = max(1, min(4, aci_sayisi))
    if set_sayisi:
        n = max(1, min(int(set_sayisi), aci_sayisi))
    else:
        n = max(1, min(ust, int(toplam // min_set)))
    # Elle girilmediyse 5 TL'ye yukarı yuvarla (Reklam Yöneticisi'nde 179,85 yerine 180)
    sb = round(float(set_butce), 2) if set_butce else float(-(-max(min_set, toplam / n) // 5) * 5)
    if hedef_cpa and sb * 5 < 2 * hedef_cpa:
        uyarilar.append(f"Set başı {tl(sb)} ile 5 günde {tl(sb * 5)} harcanır; '0 satış → kapat' eşiği {tl(2 * hedef_cpa)}. "
                        "Kural test süresinde çalışmaz: set sayısını azalt ya da set bütçesini artır.")
    if hedef_cpa and n * sb < onerilen * 0.8:
        uyarilar.append(f"Günlük toplam {tl(n * sb)}, önerilenin ({tl(onerilen)} = 3 × hedef CPA) altında; veri toplamak uzar.")
    if hedef_cpa and toplam > onerilen * 1.2 and not set_sayisi:
        uyarilar.append(f"Günlük bütçe önerilenin ({tl(onerilen)}) üstünde; tek seferde büyük bütçeyle başlamak yerine %10–20 adımlarla artır.")
    return {"onerilen_gunluk": onerilen, "min_set": min_set, "set_sayisi": n, "set_butce": sb, "uyarilar": uyarilar}


def plan_yap(p: Proje) -> dict:
    f = p.fiyat()
    hedef_cpa = f.get("hedef_cpa") or f.get("reklam_payi")
    kr = p.oku("kreatif") or {}
    acilar_hepsi = kr.get("acilar") or []
    b = butce_hesapla(hedef_cpa, len(acilar_hepsi) or 1, p.secim("gunluk_butce"), p.secim("set_butce"), p.secim("set_sayisi"))
    butce, n = b["set_butce"], b["set_sayisi"]
    acilar = acilar_hepsi[:n]
    yarin = (dt.datetime.now() + dt.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    setler = []
    for i, a in enumerate(acilar, 1):
        setler.append({
            "ad": f"T1 | {i} {a['ad'][:30]} | broad TR",
            "gunluk_butce_tl": butce,
            "hedefleme": {"ulke": "TR", "yas": [int(p.secim("yas_min", 22)), int(p.secim("yas_max", 55))], "cinsiyet": "hepsi",
                          "ilgi_alani": "yok (broad)", "yerlesim": "Advantage+ yerleşimler"},
            "reklamlar": [{"hook": h, "baslik": (kr.get("basliklar") or [""])[j % max(1, len(kr.get("basliklar") or [1]))],
                           "ana_metin": (kr.get("ana_metinler") or [{"metin": ""}])[j % max(1, len(kr.get("ana_metinler") or [1]))]["metin"],
                           "cta": "Şimdi Alışveriş Yap"} for j, h in enumerate(a["hooklar"][:2])],
        })
    gunluk = butce * len(setler)
    return {
        "kampanya": {"ad": f"{p.marka()['isim']} | Test 1 | Satış | ABO", "amac": "Satış (OUTCOME_SALES)",
                     "butce_tipi": "ABO (reklam seti bütçesi)", "baslangic": yarin.isoformat(), "olay": "Purchase"},
        "setler": setler,
        "butce": {"gunluk_tl": gunluk, "test_3_gun_tl": gunluk * 3, "test_5_gun_tl": gunluk * 5,
                  "onerilen_gunluk_tl": b["onerilen_gunluk"], "min_set_tl": b["min_set"], "uyarilar": b["uyarilar"]},
        "kurallar": {
            "satis_fiyati": f.get("fiyat"),
            "basabas_roas": f.get("basabas_roas"),
            # Eski fiyat çıktılarında hedef_cpa yok → reklam payından türet
            "hedef_cpa_tl": hedef_cpa,
            "basabas_cpa_tl": f.get("basabas_cpa"),
            "kapat_0_atc_tl": f.get("kapat_0_atc_harcama"),
            "kapat_0_satis_tl": round(2 * hedef_cpa, 2) if hedef_cpa else None,
            "kapat_yuksek_cpa_tl": round(2 * hedef_cpa, 2) if hedef_cpa else None,
            "net_kar_tl": f.get("birim_kar"),
        },
    }


def meta_istekleri(plan: dict) -> list[dict]:
    hesap = os.getenv("META_REKLAM_HESABI", "act_<REKLAM_HESABI>")
    pixel = os.getenv("META_PIXEL_ID", "<PIXEL_ID>")
    k = plan["kampanya"]
    out = [{"uc": f"{hesap}/campaigns", "veri": {
        "name": k["ad"], "objective": "OUTCOME_SALES", "status": "PAUSED", "special_ad_categories": [],
        "buying_type": "AUCTION", "is_adset_budget_sharing_enabled": False}}]
    for s in plan["setler"]:
        out.append({"uc": f"{hesap}/adsets", "veri": {
            "name": s["ad"], "campaign_id": "<KAMPANYA_ID>", "status": "PAUSED",
            "daily_budget": int(s["gunluk_butce_tl"] * 100), "billing_event": "IMPRESSIONS",
            "optimization_goal": "OFFSITE_CONVERSIONS", "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
            "promoted_object": {"pixel_id": pixel, "custom_event_type": "PURCHASE"},
            "targeting": {"geo_locations": {"countries": ["TR"]}, "age_min": s["hedefleme"]["yas"][0],
                          "age_max": s["hedefleme"]["yas"][1]},
            "start_time": k["baslangic"]}})
    return out


def meta_gonder(istekler: list[dict]) -> dict:
    token = os.getenv("META_ERISIM_TOKENI")
    if not (token and os.getenv("META_REKLAM_HESABI") and os.getenv("META_PIXEL_ID")):
        return {"durum": "atlandı", "neden": ".env'de META_ERISIM_TOKENI / META_REKLAM_HESABI / META_PIXEL_ID eksik"}
    sonuc, kampanya_id = [], None
    for ist in istekler:
        veri = dict(ist["veri"])
        if veri.get("campaign_id") == "<KAMPANYA_ID>":
            veri["campaign_id"] = kampanya_id
        govde = {k: (json.dumps(v) if isinstance(v, (dict, list, bool)) else v) for k, v in veri.items()}
        r = requests.post(f"https://graph.facebook.com/{API}/{ist['uc']}", data={**govde, "access_token": token}, timeout=60)
        d = r.json()
        if r.status_code != 200 or "error" in d:
            sonuc.append({"uc": ist["uc"], "hata": d.get("error", d)})
            break
        if ist["uc"].endswith("/campaigns"):
            kampanya_id = d["id"]
        sonuc.append({"uc": ist["uc"], "id": d.get("id")})
    return {"durum": "duraklatılmış olarak oluşturuldu" if all("id" in s for s in sonuc) else "hata", "sonuc": sonuc}


def calistir(p: Proje, args=None):
    plan = plan_yap(p)
    ist = meta_istekleri(plan)
    api = meta_gonder(ist) if getattr(args, "gonder", False) else {"durum": "kuru çalıştırma (--gonder verilmedi)"}
    p.durum["secimler"].setdefault("test_baslangic", plan["kampanya"]["baslangic"])
    p.kaydet_durum()
    k, b, r = plan["kampanya"], plan["butce"], plan["kurallar"]
    md = [f"# Reklam test planı — {k['ad']}", "",
          f"- Amaç: {k['amac']} · {k['butce_tipi']} · olay: {k['olay']} · başlangıç: **{k['baslangic'][:16].replace('T', ' ')}**",
          f"- {len(plan['setler'])} set × {tl(plan['setler'][0]['gunluk_butce_tl']) if plan['setler'] else '-'} = günlük **{tl(b['gunluk_tl'])}** · "
          f"3 gün {tl(b['test_3_gun_tl'])} · 5 gün {tl(b['test_5_gun_tl'])}",
          f"- Bütçe hesabı: önerilen günlük = 3 × hedef CPA = **{tl(b.get('onerilen_gunluk_tl'))}**; set başı en az {tl(b.get('min_set_tl'))} "
          "(100 TL ve 0,4 × hedef CPA'dan büyüğü); bütçe yetmezse daha az set. Değiştirmek için: `python hat.py sec <proje> gunluk_butce=...`",
          f"- Meta API: {api['durum']}" + (f" — {api.get('neden')}" if api.get("neden") else ""), ""]
    md += [f"> ⚠ {u}" for u in b.get("uyarilar") or []] + ([""] if b.get("uyarilar") else [])
    md += ["## Ön koşullar (hepsi ✓ olmadan yayına alma)", "",
           f"- [{'x' if p.onayli('tedarik') else ' '}] Numune onaylandı (tedarik adımı)"
           + (" (deneme projesi)" if p.durum.get("zorla") else "")] + [f"- [ ] {x}" for x in [
        "Mağaza yayında, telefonda test siparişi verildi, ödeme ve kargo çalışıyor",
        "Meta Pixel + Conversions API kurulu; PageView / ViewContent / AddToCart / InitiateCheckout / Purchase olayları geliyor",
        "Instagram'da en az 20 içerik, 4 öne çıkan, bio ve link hazır", "Yasal sayfalar ve iletişim bilgileri sitede",
        "Reklamlar gerçek ürün görüntüsüyle (numune çekimi/UGC); yanıltıcı AI görseli yok"]]
    md += ["", "## Reklam setleri", ""]
    for s in plan["setler"]:
        h = s["hedefleme"]
        md += [f"### {s['ad']}", f"Günlük {tl(s['gunluk_butce_tl'])} · {h['ulke']} · {h['yas'][0]}–{h['yas'][1]} · {h['ilgi_alani']} · {h['yerlesim']}", ""]
        md += [f"- **Hook:** {x['hook']}  \n  **Başlık:** {x['baslik']}  \n  **Metin:** {x['ana_metin']}" for x in s["reklamlar"]] + [""]
    md += ["## Karar kuralları (48 saat, set başına)", "",
           f"Satış fiyatı {tl(r['satis_fiyati'])} · başabaş ROAS **{r['basabas_roas']}** · hedef CPA **{tl(r['hedef_cpa_tl'])}** "
           f"(başabaş CPA {tl(r.get('basabas_cpa_tl'))}) · net kâr {tl(r['net_kar_tl'])}", "",
           f"1. {tl(r['kapat_0_atc_tl'])} harcadı ve **0 sepete ekleme** → kapat",
           f"2. {tl(r['kapat_0_satis_tl'])} (2 × hedef CPA) harcadı ve **0 satın alma** → kapat",
           f"3. 48 saat sonunda ROAS < {r['basabas_roas']} → kapat",
           f"4. 3+ satıştan sonra CPA sürekli ≥ {tl(r.get('kapat_yuksek_cpa_tl'))} (2 × hedef CPA) → kapat veya kreatifi değiştir",
           f"Ölçekle: 48 saat + en az 2 satış + CPA ≤ hedef CPA → bütçeyi %10–20 artır (500 → 600 → 720), bir anda katlama.",
           "En az 3–5 gün veri topla; 2 saatte, tek günlük ROAS'a ya da sadece düşük CTR'ye bakıp kapatma.", "",
           "Sonuçları değerlendirmek için Reklam Yöneticisi'nden reklam seti düzeyinde CSV indir:",
           "`python hat.py calistir <proje> analiz --csv <dosya.csv>`", "",
           "<details><summary>Meta API istekleri (kuru çalıştırma)</summary>", "", "```json",
           json.dumps(ist, ensure_ascii=False, indent=1), "```", "</details>"]
    p.yaz("reklam", {"plan": plan, "meta_istekleri": ist, "api": api}, md)
