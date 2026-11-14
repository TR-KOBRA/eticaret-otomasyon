"""4 · İçerik: ürün sayfası metni, fayda maddeleri, özellik tablosu, SSS, SEO, kargo/iade metni, yasal sayfa taslakları.

Teknik iddialar yalnızca satıcı verisinden; bilinmeyenler [doğrula] ile işaretlenir.
Yasal metinler ŞABLONDUR: yayından önce avukat / mali müşavir kontrolü gerekir.
"""
from __future__ import annotations

from ortak import Proje, metin_json, ozet

SEMA = {
    "type": "OBJECT",
    "properties": {
        "urun_adi": {"type": "STRING", "description": "mağazadaki ürün adı, ≤ 70 karakter"},
        "alt_baslik": {"type": "STRING", "description": "fayda odaklı tek cümle"},
        "fayda_maddeleri": {"type": "ARRAY", "items": {"type": "STRING"}},
        "aciklama": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "3–5 kısa paragraf"},
        "kullanim": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "adım adım kullanım"},
        "kutu_icerigi": {"type": "ARRAY", "items": {"type": "STRING"}},
        "sss": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "soru": {"type": "STRING"}, "cevap": {"type": "STRING"}}, "required": ["soru", "cevap"]}},
        "seo_baslik": {"type": "STRING", "description": "≤ 60 karakter"},
        "meta_aciklama": {"type": "STRING", "description": "≤ 155 karakter"},
        "url": {"type": "STRING", "description": "küçük harf, tireli, Türkçe karaktersiz"},
        "etiketler": {"type": "ARRAY", "items": {"type": "STRING"}},
        "paket_metinleri": {"type": "OBJECT", "properties": {
            "tekli": {"type": "STRING"}, "ikili": {"type": "STRING"}, "uclu": {"type": "STRING"}},
            "required": ["tekli", "ikili", "uclu"]},
    },
    "required": ["urun_adi", "alt_baslik", "fayda_maddeleri", "aciklama", "kullanim", "kutu_icerigi", "sss",
                 "seo_baslik", "meta_aciklama", "url", "etiketler", "paket_metinleri"],
}

GUVEN_SERIDI = ["Hızlı kargo — [X] TL üzeri ücretsiz", "Güvenli ödeme (SSL / iyzico-PayTR)",
                "WhatsApp destek hattı", "14 gün içinde kolay iade"]

YASAL = {
    "mesafeli-satis-sozlesmesi": """# Mesafeli Satış Sözleşmesi (ŞABLON)

> 6502 sayılı Tüketicinin Korunması Hakkında Kanun ve Mesafeli Sözleşmeler Yönetmeliği'ne göre hazırlanmalıdır.
> Bu taslak yayından önce bir hukukçu tarafından kontrol edilmelidir.

**Madde 1 – Taraflar.** SATICI: [Ticari unvan], [Adres], [Vergi dairesi / no], [MERSİS no], [Telefon], [E-posta], [KEP].
ALICI: Sipariş sırasında bilgileri girilen kişi.

**Madde 2 – Konu.** ALICI'nın [{marka}] internet sitesinden elektronik ortamda siparişini verdiği ürünün satışı ve teslimi.

**Madde 3 – Ürün ve fiyat.** Ürün adı, adedi, KDV dahil satış fiyatı, kargo ücreti ve ödeme şekli sipariş özetinde ve
faturada belirtildiği gibidir.

**Madde 4 – Teslimat.** Ürün, ödemenin onayından itibaren en geç [X] iş günü içinde kargoya verilir; yasal azami süre 30 gündür.

**Madde 5 – Cayma hakkı.** ALICI, ürünü teslim aldığı tarihten itibaren 14 gün içinde gerekçe göstermeden cayma hakkına sahiptir.
Cayma bildirimi [e-posta / iletişim formu] ile yapılır. Ürün, kullanılmamış ve yeniden satılabilir halde iade edilir.
Bedel, iadenin SATICI'ya ulaşmasından itibaren 14 gün içinde ödeme yöntemine iade edilir. [İade kargo ücretini kimin karşıladığı]
[Cayma hakkı istisnaları: hijyen nedeniyle ambalajı açılmış ürünler vb. — ürünün durumuna göre hukukçuyla belirle]

**Madde 6 – Uyuşmazlık.** Parasal sınırlar dahilinde Tüketici Hakem Heyetleri, üzerinde Tüketici Mahkemeleri yetkilidir.
""",
    "iade-ve-degisim": """# İade ve Değişim Koşulları (ŞABLON)

- Ürünü teslim aldığınız tarihten itibaren **14 gün** içinde iade edebilirsiniz.
- İade için [WhatsApp / e-posta] üzerinden sipariş numaranızla bize yazın; size iade kodu ve adresi iletilir.
- Ürün kullanılmamış, orijinal ambalajında ve tüm parçalarıyla gönderilmelidir.
- Hasarlı veya hatalı ürünlerde kargo ücreti bize aittir; teslimatta kargo görevlisine tutanak tutturmanızı rica ederiz.
- Onaylanan iadelerde ödeme 14 gün içinde kartınıza / hesabınıza iade edilir.
- [Hijyen nedeniyle iade alınamayan durumlar — varsa]
""",
    "kvkk-aydinlatma": """# KVKK Aydınlatma Metni (ŞABLON)

> 6698 sayılı Kişisel Verilerin Korunması Kanunu kapsamında hazırlanmalıdır; yayından önce hukukçu kontrolü gerekir.

**Veri sorumlusu:** [Ticari unvan], [Adres].
**İşlenen veriler:** ad-soyad, telefon, e-posta, teslimat/fatura adresi, sipariş ve ödeme işlem bilgileri (kart bilgileri
ödeme kuruluşu tarafından işlenir, tarafımızca saklanmaz), çerez verileri.
**Amaçlar:** siparişin alınması, teslimatı, faturalandırma, müşteri desteği, yasal yükümlülükler; açık rızanız varsa
kampanya bildirimleri.
**Aktarım:** kargo firması, ödeme kuruluşu, muhasebe/mali müşavir, e-ticaret altyapı sağlayıcısı, yetkili kamu kurumları.
[Yurt dışına aktarım varsa (ör. altyapı sunucuları) açıkça belirt.]
**Hukuki sebepler:** sözleşmenin ifası, hukuki yükümlülük, meşru menfaat, açık rıza.
**Haklarınız (KVKK m.11):** [e-posta] adresine başvurarak bilgi talep etme, düzeltme, silme, itiraz vb.
""",
    "gizlilik-ve-cerez": """# Gizlilik ve Çerez Politikası (ŞABLON)

Sitemizde zorunlu çerezler (sepet, oturum) ve izninizle analiz/pazarlama çerezleri (ör. Meta Pixel, Google Analytics)
kullanılır. Çerez tercihlerinizi site altındaki bağlantıdan değiştirebilirsiniz. Ayrıntılar için KVKK Aydınlatma Metni'ne bakın.
""",
}

KONTROL = [
    "Şahıs veya şirket kaydı + vergi mükellefiyeti (mali müşavir)",
    "ETBİS kaydı (e-ticaret bilgi sistemi) — siteyi açtıktan sonra yasal süre içinde",
    "Ticari ileti izni (İYS) — e-posta/SMS kampanyası göndereceksen",
    "Sitenin altında firma unvanı, adres, iletişim, MERSİS/vergi no",
    "Ön bilgilendirme formu + mesafeli satış sözleşmesi ödeme adımında onaylatılmalı",
    "Ürün etiketi/ithalat: kategori özel mevzuat (kozmetik, oyuncak, elektrik, gıda temaslı) varsa uygunluk",
]


def calistir(p: Proje, args=None):
    m = p.marka()
    istem = "\n".join([
        p.urun_ozeti(uzun=True), "",
        f"Marka: {m['isim']} · konumlandırma: {m.get('konumlandirma')} · ton: {m.get('ton')} · hedef kitle: {m.get('hedef_kitle')}",
        "",
        "Bu ürün için kendi sitemizdeki ürün sayfasının metinlerini yaz. Satıcının ürün adındaki marka adını kullanma; ürünü "
        f"'{m['isim']}' markasıyla anlat. Fayda odaklı ol ama yalnızca verilen özelliklere dayan. 5 fayda maddesi (emoji yok, "
        "her biri ≤ 12 kelime), 3–5 paragraf açıklama, kullanım adımları, kutu içeriği (bilinmiyorsa [doğrula]), "
        "8 SSS (kargo süresi, iade, ödeme güvenliği, kullanım, ürüne özel itirazlar; firma bilgisi gerekenleri [X] ile bırak), "
        "SEO başlık/meta/url/etiketler, tekli/2'li/3'lü paket için birer kısa satış cümlesi.",
        "", "Bilgi bankası (mağaza kuralları):", ozet("magaza")[:2500],
    ])
    g = metin_json(istem, SEMA, sicaklik=0.6)
    import re
    g["kullanim"] = [re.sub(r"^\s*\d+[.)]\s*", "", x) for x in g["kullanim"]]
    oz = p.urun.get("ozellikler") or {}
    g["ozellik_tablosu"] = {k: v for k, v in oz.items() if "marka" not in k.lower() and "brand" not in k.lower()}
    g["guven_seridi"] = GUVEN_SERIDI
    g["yasal"] = {k: v.replace("{marka}", m["isim"]) for k, v in YASAL.items()}
    g["yasal_kontrol"] = KONTROL
    g["fiyat"] = p.fiyat()

    yasal_dir = p.yol / "yasal"
    yasal_dir.mkdir(exist_ok=True)
    for k, v in g["yasal"].items():
        (yasal_dir / f"{k}.md").write_text(v, encoding="utf-8")

    f = g["fiyat"]
    md = [f"# {g['urun_adi']}", "", f"_{g['alt_baslik']}_", "",
          f"**Fiyat:** {f.get('fiyat')} TL · 2'li {f.get('paket_2')} TL · 3'lü {f.get('paket_3')} TL "
          f"(net marj %{f.get('marj_yuzde')}; değiştirmek için `hat.py sec <proje> fiyat=...`)", "",
          "## Faydalar", ""] + [f"- {x}" for x in g["fayda_maddeleri"]]
    md += ["", "## Açıklama", ""] + [x + "\n" for x in g["aciklama"]]
    md += ["## Kullanım", ""] + [f"{i}. {x}" for i, x in enumerate(g["kullanim"], 1)]
    md += ["", "## Kutu içeriği", ""] + [f"- {x}" for x in g["kutu_icerigi"]]
    md += ["", "## Özellikler (satıcı verisi — numuneyle doğrula)", "", "| Özellik | Değer |", "|---|---|"]
    md += [f"| {k} | {v} |" for k, v in g["ozellik_tablosu"].items()]
    md += ["", "## Paketler", "", f"- Tekli: {g['paket_metinleri']['tekli']}", f"- 2'li: {g['paket_metinleri']['ikili']}",
           f"- 3'lü: {g['paket_metinleri']['uclu']}"]
    md += ["", "## Güven şeridi", ""] + [f"- {x}" for x in GUVEN_SERIDI]
    md += ["", "## SSS", ""] + [f"**{x['soru']}**  \n{x['cevap']}\n" for x in g["sss"]]
    md += ["## SEO", "", f"- Başlık: {g['seo_baslik']}", f"- Meta: {g['meta_aciklama']}", f"- URL: /{g['url']}",
           "- Etiketler: " + ", ".join(g["etiketler"])]
    md += ["", "## Yasal sayfalar (şablon, `yasal/` klasöründe)", "",
           "Köşeli parantezli alanları doldur ve **yayından önce hukukçu / mali müşavire kontrol ettir.**", ""]
    md += [f"- {k}.md" for k in g["yasal"]] + ["", "## Yasal kontrol listesi", ""] + [f"- [ ] {x}" for x in KONTROL]
    p.yaz("icerik", g, md)
