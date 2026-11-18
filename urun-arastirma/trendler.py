"""Google Trends (Türkiye): talep yönü, mevsimsellik, ilgili aramalar.

İstemci: trendspyg (bakımı süren, pytrends uyumlu TrendReq; pytrends arşivlendi). engine="http": Google reddederse
tarayıcı (Chrome) açarak denemez — sadece doğrudan istek; hata alınırsa sonuçta "hata" alanı dolar.
trendspyg kurulu değilse eski pytrends'e düşer.
"""
from __future__ import annotations

import time

try:
    from trendspyg.compat.request import TrendReq
    _MOTOR = {"engine": "http"}          # tarayıcıya düşme yok
except ImportError:                      # pragma: no cover
    from pytrends.request import TrendReq
    _MOTOR = {}


def _istemci():
    # retries/backoff vermiyoruz: pytrends urllib3 2.x ile uyumsuz Retry argümanı kullanıyor
    return TrendReq(hl="tr-TR", tz=-180, timeout=(10, 30), **_MOTOR)


def talep(kelimeler: list[str], donem: str = "today 12-m", geo: str = "TR") -> dict:
    """En fazla 5 kelime. Her kelime için: ortalama ilgi, son 3 ay vs önceki 3 ay değişimi,
    zirve ayı, haftalık seri ve ilgili yükselen aramalar."""
    kelimeler = kelimeler[:5]
    sonuc: dict = {"donem": donem, "geo": geo, "kelimeler": {}}
    py, df, son_hata = _istemci(), None, None
    for deneme in range(3):
        try:
            py.build_payload(kelimeler, timeframe=donem, geo=geo)
            df = py.interest_over_time()
            break
        except Exception as e:  # 429 ya da ağ hatası
            son_hata = f"{type(e).__name__}: {e}"
            time.sleep(10 * (deneme + 1))
    if df is None and son_hata:
        sonuc["hata"] = son_hata
        return sonuc
    if df is None or df.empty:
        sonuc["hata"] = "Veri yok (arama hacmi çok düşük olabilir)"
        return sonuc
    df = df.drop(columns=[c for c in ["isPartial"] if c in df.columns])
    for k in kelimeler:
        if k not in df.columns:
            continue
        s = df[k]
        n = len(s)
        son = s.iloc[-13:].mean() if n >= 26 else s.iloc[-(n // 2):].mean()
        onceki = s.iloc[-26:-13].mean() if n >= 26 else s.iloc[: n // 2].mean()
        aylik = s.groupby(s.index.month).mean()
        sonuc["kelimeler"][k] = {
            "ortalama": round(float(s.mean()), 1),
            "son_3_ay": round(float(son), 1),
            "degisim_yuzde": round(float((son - onceki) / onceki * 100), 1) if onceki else None,
            "zirve_ay": int(aylik.idxmax()),
            "dip_ay": int(aylik.idxmin()),
            "seri": {d.strftime("%Y-%m-%d"): int(v) for d, v in s.items()},
        }
    time.sleep(2)
    try:
        ilgili = py.related_queries()
        for k in kelimeler:
            r = (ilgili.get(k) or {})
            yuk, ust = r.get("rising"), r.get("top")
            if k in sonuc["kelimeler"]:
                sonuc["kelimeler"][k]["yukselen"] = [] if yuk is None else yuk.head(10).to_dict("records")
                sonuc["kelimeler"][k]["en_cok"] = [] if ust is None else ust.head(10).to_dict("records")
    except Exception as e:
        sonuc["ilgili_hata"] = f"{type(e).__name__}: {e}"
    return sonuc
