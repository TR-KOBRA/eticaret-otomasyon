"""Otomatik testler (internet, API anahtarı ve para harcamadan): hesap, doygunluk, alış tavanı, riskler, reklam kararı,
Shopify özeti, günlük alaka, sinyal → proje dönüşümü, tedarik metni, panel toptancı kartı doğrulaması.

  python testler.py            # hepsi
  python testler.py -k tavan   # adında 'tavan' geçenler
"""
from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent
for alt in ("urun-arastirma", "hat", "panel"):
    sys.path.insert(0, str(KOK / alt))

import hesap  # noqa: E402
import rakipler  # noqa: E402
import riskler  # noqa: E402


class Hesap(unittest.TestCase):
    def setUp(self):
        self.a = hesap.ayarlar("site")

    def test_yerli_maliyet_kalemleri(self):
        m = hesap.birim_maliyet(150, 0, "yerli", self.a)
        self.assertEqual(set(m["kalemler"]), {"urun", "paketleme", "yurtici_kargo"})
        self.assertAlmostEqual(m["toplam"], 150 + self.a["paketleme_tl"] + self.a["yurtici_kargo_tl"])

    def test_bilinen_ornek_150tl_699tl(self):
        """2026-11-18'de elle doğrulanan örnek: 150 TL yerli alış, 699 TL satış → brüt %46,2, net %20,4, minimum 691."""
        m = hesap.birim_maliyet(150, 0, "yerli", self.a)
        f = hesap.fiyat_analizi(699, m, self.a)
        self.assertAlmostEqual(f["brut_marj_yuzde"], 46.2, delta=0.15)
        self.assertAlmostEqual(f["marj_yuzde"], 20.4, delta=0.15)
        self.assertAlmostEqual(hesap.minimum_fiyat(m, self.a), 691, delta=2)

    def test_kdv_mahsup_kari_artirir(self):
        m = hesap.birim_maliyet(150, 0, "yerli", self.a)
        acik = hesap.fiyat_analizi(699, m, {**self.a, "kdv_mahsup": True})
        kapali = hesap.fiyat_analizi(699, m, {**self.a, "kdv_mahsup": False})
        self.assertGreater(acik["birim_kar"], kapali["birim_kar"])
        self.assertGreater(acik["mahsup_kdv"], 0)

    def test_shopify_komisyonu_sitede_var_trendyolda_yok(self):
        self.assertEqual(hesap.ayarlar("site")["shopify_komisyonu"], 0.02)
        self.assertEqual(hesap.ayarlar("trendyol").get("shopify_komisyonu", 0), 0)

    def test_alis_tavani_sinirda_hedef_marj(self):
        t = hesap.alis_tavani(699, self.a)
        self.assertIsNotNone(t)
        tam = hesap.fiyat_analizi(699, hesap.birim_maliyet(t, 0, "yerli", self.a), self.a)["marj_yuzde"]
        fazla = hesap.fiyat_analizi(699, hesap.birim_maliyet(t + 5, 0, "yerli", self.a), self.a)["marj_yuzde"]
        self.assertGreaterEqual(tam, self.a["hedef_marj"] * 100 - 0.1)
        self.assertLess(fazla, self.a["hedef_marj"] * 100)

    def test_alis_tavani_ucuz_piyasada_yok(self):
        self.assertIsNone(hesap.alis_tavani(150, self.a))
        self.assertIsNone(hesap.alis_tavani(0, self.a))

    def test_fiyat_secenekleri_rakip_verisiyle(self):
        m = hesap.birim_maliyet(150, 0, "yerli", self.a)
        s = hesap.fiyat_secenekleri(m, {"medyan": 699, "alt_ceyrek": 549, "ust_ceyrek": 899}, self.a)
        adlar = [x["secenek"] for x in s]
        self.assertIn("dengeli", adlar)
        self.assertTrue(adlar[0].startswith("minimum"))


class Doygunluk(unittest.TestCase):
    @staticmethod
    def _liste(yorumlar):
        return [{"degerlendirme": y} for y in yorumlar]

    def test_uygun(self):
        self.assertEqual(rakipler.doygunluk(self._liste([150, 120, 30, 5]))["seviye"], "uygun")

    def test_tek_dev_rakip_kalabalik(self):
        self.assertEqual(rakipler.doygunluk(self._liste([700, 10]))["seviye"], "kalabalik")

    def test_alti_guclu_kalabalik(self):
        self.assertEqual(rakipler.doygunluk(self._liste([101] * 6))["seviye"], "kalabalik")

    def test_on_guclu_doymus(self):
        d = rakipler.doygunluk(self._liste([100] * 10 + [3]))
        self.assertEqual((d["seviye"], d["guclu_rakip"]), ("doymus", 10))

    def test_ozet(self):
        o = rakipler.ozet_hesapla([{"fiyat": f} for f in (100, 200, 300, 400)])
        self.assertEqual((o["min"], o["max"], o["medyan"]), (100, 400, 250))


class Riskler(unittest.TestCase):
    def test_giyim_baslangica_uygun_degil(self):
        r = riskler.tara({"baslik": "Kadın kapüşonlu sweatshirt", "kargo": [{"gun_max": 10, "takip": True}]})
        self.assertTrue(any(x.get("kod") == "baslangic_kategori" for x in r))

    def test_normal_urun_kategori_uyarisi_yok(self):
        r = riskler.tara({"baslik": "Kedi tüy toplama rulosu", "kargo": [{"gun_max": 10, "takip": True}]})
        self.assertFalse(any(x.get("kod") == "baslangic_kategori" for x in r))


class ReklamKarari(unittest.TestCase):
    def setUp(self):
        import analiz
        self.d = analiz.degerlendir
        self.k = {"basabas_roas": 2.0, "hedef_cpa_tl": 200, "kapat_0_atc_tl": 150, "kapat_0_satis_tl": 400}

    def test_sepetsiz_harcama_kapat(self):
        self.assertEqual(self.d({"harcama": 160, "atc": 0, "satis": 0, "roas": 0, "cpa": None}, self.k, 12)[0], "KAPAT")

    def test_iyi_set_olcekle(self):
        s = {"harcama": 400, "atc": 10, "satis": 3, "roas": 3.0, "cpa": 133}
        self.assertEqual(self.d(s, self.k, 50)[0], "ÖLÇEKLE")

    def test_erken_bekle(self):
        self.assertEqual(self.d({"harcama": 50, "atc": 1, "satis": 0, "roas": 0, "cpa": None}, self.k, 6)[0], "İZLE")


class ShopifyOzet(unittest.TestCase):
    def test_iptal_atlanir_iade_sayilir(self):
        import shopify_baglanti as sb
        bugun = dt.date(2026, 11, 18)
        s = lambda g, tutar, iade="0", iptal=None: {"createdAt": f"{g}T10:00:00Z", "cancelledAt": iptal, "currentSubtotalLineItemsQuantity": 1,  # noqa: E731
                                                    "totalPriceSet": {"shopMoney": {"amount": tutar}}, "totalRefundedSet": {"shopMoney": {"amount": iade}}}
        o = sb.ozetle([s("2026-11-18", "500"), s("2026-11-17", "300", "300"), s("2026-11-17", "999", iptal="x"), s("2026-10-01", "700")], 7, bugun)
        self.assertEqual((o["ciro"], o["siparis"], o["iade"], o["iade_orani"]), (800.0, 2, 300.0, 37.5))
        self.assertEqual(len(o["seri"]), 7)


class GunlukAlaka(unittest.TestCase):
    def test_alakali(self):
        import gunluk
        self.assertTrue(gunluk.alakali("Evcil hayvan tüy toplama rulosu yeniden kullanılabilir", "lint roller", "tüy toplama rulosu"))
        self.assertFalse(gunluk.alakali("Takma kirpik seti 10 çift", "lint roller", "tüy toplama rulosu"))


ORNEK_SINYAL = {
    "asin": "B0TEST0001", "title": "Automatic Cat Ball", "price": 15.0, "rating": 4.6, "reviewCount": 12,
    "imageUrl": "https://example.com/a.jpg", "productUrl": "https://www.amazon.com/dp/B0TEST0001", "kategori": "pet-supplies",
    "tr_kelime": "otomatik kedi topu", "urun_turu": "Otomatik kedi topu", "problem": "Evde yalnız kalan kedi sıkılıyor",
    "acilar": ["a", "b", "c"], "neden": "Az rakip", "karar": "TESTE AL", "alis_tavani": 180.0,
    "trendyol": {"aranan": "otomatik kedi topu", "sonuc": 20, "benzer": 4, "medyan": 699,
                 "doygunluk": {"seviye": "uygun", "guclu_rakip": 1, "en_cok_yorum": 150},
                 "ornekler": [{"ad": f"Kedi topu {i}", "fiyat": 600 + i * 50, "degerlendirme": 10 * i,
                               "link": f"https://www.trendyol.com/marka{i}/kedi-topu-p-{1000 + i}?merchantId=1"} for i in range(4)]},
    "reklam": {"toplam_reklam": 5, "reklamveren": 2, "seviye": "uygun"},
}


class SinyalProje(unittest.TestCase):
    def test_donusum_hattin_bekledigi_alanlar(self):
        import sinyal_proje
        v = sinyal_proje.donustur({**ORNEK_SINYAL, "_usd_tl": 41})
        for k in ("urun", "maliyet", "fiyat_secenekleri", "skor", "trendyol", "riskler", "ayarlar"):
            self.assertIn(k, v)
        self.assertEqual(v["skor"]["karar"], "TESTE AL")
        self.assertEqual(v["maliyet"]["stok"]["senaryo"], "yerli")
        self.assertEqual(v["urun"]["fiyat"], 180.0)                       # alış tavanı tahmin olarak
        self.assertEqual(v["trendyol"]["ozet"]["medyan"], 699)
        self.assertIn("dengeli", [x["secenek"] for x in v["fiyat_secenekleri"]])
        self.assertIn("Karar", sinyal_proje.rapor(v))

    def test_tavan_yoksa_kaba_tahmin(self):
        import sinyal_proje
        alis, neden = sinyal_proje.tahmini_alis({**ORNEK_SINYAL, "alis_tavani": None, "_usd_tl": 40})
        self.assertEqual(alis, round(15 * 40 * 0.35))
        self.assertIn("kaba", neden)


class Tedarik(unittest.TestCase):
    def test_yerli_tedarik_raporu(self):
        import ortak
        import sinyal_proje
        import tedarik
        gecici = Path(tempfile.mkdtemp())
        try:
            v = sinyal_proje.donustur({**ORNEK_SINYAL, "_usd_tl": 41})
            v.pop("_dosya_zaman", None)
            (gecici / "urun.json").write_text(json.dumps(v, ensure_ascii=False), encoding="utf-8")
            p = ortak.Proje(gecici)
            p.durum["secimler"].update({"toptanci_ad": "Deneme Toptan", "tedarik_fiyati": "120", "fatura": "var"})
            tedarik.calistir(p)
            md = p.dosya("tedarik", "md").read_text(encoding="utf-8")
            veri = p.oku("tedarik")
            self.assertIn("Toptan alış tavanı", md)
            self.assertIn("Mesafeli Satış Sözleşmesi", md)
            self.assertIn("Deneme Toptan", md)
            self.assertNotIn("AliExpress satıcısına", md)                 # Amazon kaynaklıda İngilizce ek yok
            self.assertEqual(len(veri["saticilar"]), 4)                   # ?merchantId kopyaları tekilleşti
            self.assertTrue(all("?" not in s["link"] for s in veri["saticilar"]))
            self.assertEqual(p.maliyet()["kaynak"], "tedarikçi toptan fiyatı (yerli, KDV dahil)")
        finally:
            shutil.rmtree(gecici, ignore_errors=True)


class PanelToptanciKarti(unittest.TestCase):
    def test_metin_ve_secenek_alanlari(self):
        from fastapi.testclient import TestClient
        import sunucu
        import sinyal_proje
        ad = "zz-test-toptanci"
        yol = sunucu.PROJELER / ad
        yol.mkdir(parents=True, exist_ok=True)
        try:
            v = sinyal_proje.donustur({**ORNEK_SINYAL, "_usd_tl": 41})
            v.pop("_dosya_zaman", None)
            (yol / "urun.json").write_text(json.dumps(v, ensure_ascii=False), encoding="utf-8")
            c = TestClient(sunucu.app)
            r = c.post(f"/api/proje/{ad}/sec", json={"toptanci_ad": "Yıldız\nToptan", "fatura": "var", "dropship": "evet", "moq": "50"})
            self.assertEqual(r.status_code, 200, r.text)
            self.assertEqual(r.json()["toptanci_ad"], "Yıldız Toptan")    # satır sonu temizlendi
            self.assertEqual(c.post(f"/api/proje/{ad}/sec", json={"fatura": "belki"}).status_code, 400)
            self.assertEqual(c.post(f"/api/proje/{ad}/sec", json={"moq": "elli"}).status_code, 400)
            self.assertEqual(c.post(f"/api/proje/{ad}/sec", json={"isim": "x"}).status_code, 400)
        finally:
            shutil.rmtree(yol, ignore_errors=True)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    unittest.main(verbosity=2)
