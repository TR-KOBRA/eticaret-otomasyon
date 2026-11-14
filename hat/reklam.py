"""9 · Reklam: düşük bütçeli test planı (ABO + broad TR, set başı 100–150 TL, 00:00 başlangıç) ve kapatma eşikleri.

Varsayılan kuru çalıştırmadır: Meta'ya hiçbir şey gönderilmez, API istekleri rapora yazılır.
`--gonder` + .env'de META_ERISIM_TOKENI, META_REKLAM_HESABI (act_...), META_PIXEL_ID varsa kampanya ve reklam setleri
**DURAKLATILMIŞ (PAUSED)** oluşturulur. Reklamları ekleme ve yayına alma (para harcatan adım) Reklam Yöneticisi'nde elle yapılır.
Seçimler: set_butce (TL, varsayılan 125), yas_min (22), yas_max (55), set_sayisi (4)
"""
from __future__ import annotations

import datetime as dt
import json
import os

import requests

from ortak import Proje, tl

API = os.getenv("META_API_SURUM", "v24.0")


def plan_yap(p: Proje) -> dict:
    f = p.fiyat()
    kr = p.oku("kreatif") or {}
    butce = float(p.secim("set_butce", 125))
    butce = min(max(butce, 100), 150) if not p.secim("set_butce_serbest") else butce
    n = int(p.secim("set_sayisi", 4))
    acilar = (kr.get("acilar") or [])[:n]
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
        "butce": {"gunluk_tl": gunluk, "test_3_gun_tl": gunluk * 3, "test_5_gun_tl": gunluk * 5},
        "kurallar": {
            "satis_fiyati": f.get("fiyat"),
            "basabas_roas": f.get("basabas_roas"),
            "hedef_cpa_tl": f.get("basabas_cpa"),
            "kapat_0_atc_tl": f.get("kapat_0_atc_harcama"),
            "kapat_0_satis_tl": f.get("kapat_0_satis_harcama"),
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
          f"- Meta API: {api['durum']}" + (f" — {api.get('neden')}" if api.get("neden") else ""), "",
          "## Ön koşullar (hepsi ✓ olmadan yayına alma)", ""] + [f"- [ ] {x}" for x in [
        "Numune onaylandı (tedarik adımı)", "Mağaza yayında, telefonda test siparişi verildi, ödeme ve kargo çalışıyor",
        "Meta Pixel + Conversions API kurulu; PageView / ViewContent / AddToCart / InitiateCheckout / Purchase olayları geliyor",
        "Instagram'da en az 20 içerik, 4 öne çıkan, bio ve link hazır", "Yasal sayfalar ve iletişim bilgileri sitede",
        "Reklamlar gerçek ürün görüntüsüyle (numune çekimi/UGC); yanıltıcı AI görseli yok"]]
    md += ["", "## Reklam setleri", ""]
    for s in plan["setler"]:
        h = s["hedefleme"]
        md += [f"### {s['ad']}", f"Günlük {tl(s['gunluk_butce_tl'])} · {h['ulke']} · {h['yas'][0]}–{h['yas'][1]} · {h['ilgi_alani']} · {h['yerlesim']}", ""]
        md += [f"- **Hook:** {x['hook']}  \n  **Başlık:** {x['baslik']}  \n  **Metin:** {x['ana_metin']}" for x in s["reklamlar"]] + [""]
    md += ["## Karar kuralları (48 saat, set başına)", "",
           f"Satış fiyatı {tl(r['satis_fiyati'])} · başabaş ROAS **{r['basabas_roas']}** · hedef CPA **{tl(r['hedef_cpa_tl'])}** · net kâr {tl(r['net_kar_tl'])}", "",
           f"1. {tl(r['kapat_0_atc_tl'])} harcadı ve **0 sepete ekleme** → kapat",
           f"2. {tl(r['kapat_0_satis_tl'])} harcadı ve **0 satın alma** → kapat",
           f"3. 48 saat sonunda ROAS < {r['basabas_roas']} → kapat",
           "En az 3–5 gün veri topla; 2 saatte kapatma, ilk satışta bütçeyi katlama.", "",
           "Sonuçları değerlendirmek için Reklam Yöneticisi'nden reklam seti düzeyinde CSV indir:",
           "`python hat.py calistir <proje> analiz --csv <dosya.csv>`", "",
           "<details><summary>Meta API istekleri (kuru çalıştırma)</summary>", "", "```json",
           json.dumps(ist, ensure_ascii=False, indent=1), "```", "</details>"]
    p.yaz("reklam", {"plan": plan, "meta_istekleri": ist, "api": api}, md)
