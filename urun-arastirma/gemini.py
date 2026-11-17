"""Gemini metin modeli için küçük REST yardımcısı (ek paket gerektirmez).

.env içinde GEMINI_API_KEY gerekir. Model GEMINI_METIN_MODEL ile değiştirilebilir.
Günlük kota (ücretsiz katmanda model başına ~20 istek/gün) dolunca GEMINI_YEDEK_MODELLER sırasıyla denenir;
kotası dolan model bu çalıştırma boyunca atlanır. Hangi modelin kullanıldığı `son_model()` ile okunur.
Anahtar asla yazdırılmaz; hata mesajlarında da geçmez.
"""
from __future__ import annotations

import json
import os
import time

import requests

URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_DOLU: set[str] = set()          # bu süreçte günlük kotası dolduğu görülen modeller
_YAVAS: set[str] = set()         # bu süreçte zaman aşımına uğrayan modeller (son çare olarak yine denenir)
_SON = {"model": None}


class GeminiYok(RuntimeError):
    pass


class GeminiKota(RuntimeError):
    """Tüm modellerin günlük kotası dolu."""


def model() -> str:
    return os.getenv("GEMINI_METIN_MODEL", "gemini-3.5-flash")


def modeller() -> list[str]:
    yedek = os.getenv("GEMINI_YEDEK_MODELLER", "gemini-3.5-flash-lite,gemini-flash-lite-latest")
    out = [model()] + [m.strip() for m in yedek.split(",") if m.strip()]
    return [m for i, m in enumerate(out) if m not in out[:i]]


def son_model() -> str | None:
    return _SON["model"]


def var_mi() -> bool:
    return bool(os.getenv("GEMINI_API_KEY"))


def _gunluk_kota_mi(r: requests.Response) -> bool:
    try:
        for d in r.json().get("error", {}).get("details", []):
            for v in d.get("violations", []) or []:
                if "PerDay" in (v.get("quotaId") or ""):
                    return True
    except ValueError:
        pass
    return False


def json_sor(istem: str, sema: dict, sistem: str | None = None, sicaklik: float = 0.3, deneme: int = 3) -> dict:
    """İstemi gönderir, `sema`ya (OpenAPI alt kümesi) uyan JSON döndürür."""
    anahtar = os.getenv("GEMINI_API_KEY")
    if not anahtar:
        raise GeminiYok("GEMINI_API_KEY tanımlı değil")
    govde = {
        "contents": [{"role": "user", "parts": [{"text": istem}]}],
        "generationConfig": {
            "temperature": sicaklik,
            "responseMimeType": "application/json",
            "responseSchema": sema,
        },
    }
    if sistem:
        govde["systemInstruction"] = {"parts": [{"text": sistem}]}
    son_hata = None
    adaylar = [x for x in modeller() if x not in _DOLU]
    for m in [x for x in adaylar if x not in _YAVAS] + [x for x in adaylar if x in _YAVAS]:
        for i in range(deneme):
            try:
                r = requests.post(URL.format(model=m), json=govde, timeout=int(os.getenv("GEMINI_ZAMAN_ASIMI", "60")),
                                  headers={"x-goog-api-key": anahtar, "Content-Type": "application/json"})
                if r.status_code == 429 and _gunluk_kota_mi(r):
                    _DOLU.add(m)
                    son_hata = f"{m} günlük kota doldu (HTTP 429)"
                    break                                  # sıradaki modele geç
                if r.status_code in (429, 500, 502, 503, 504):
                    son_hata = f"HTTP {r.status_code}"
                    time.sleep(4 * (i + 1))
                    continue
                if r.status_code == 404:
                    son_hata = f"{m} bulunamadı (HTTP 404)"
                    break
                if r.status_code != 200:
                    raise RuntimeError(f"Gemini HTTP {r.status_code}: {r.text[:300]}")
                d = r.json()
                parca = d["candidates"][0]["content"]["parts"]
                metin = "".join(p.get("text", "") for p in parca if not p.get("thought"))
                sonuc = json.loads(metin)
                _SON["model"] = m
                return sonuc
            except requests.Timeout:
                son_hata = f"{m} zaman aşımı"
                _YAVAS.add(m)
                break                                      # takılan modeli bekleme, sıradakine geç
            except (requests.RequestException, KeyError, IndexError, json.JSONDecodeError) as e:
                son_hata = f"{type(e).__name__}: {e}"
                time.sleep(2 * (i + 1))
    if all(x in _DOLU for x in modeller()):
        raise GeminiKota(f"Tüm Gemini modellerinin günlük kotası dolu ({', '.join(modeller())}); yarın sıfırlanır "
                         "ya da Google AI Studio'da faturalandırmayı aç.")
    raise RuntimeError(f"Gemini yanıtı alınamadı ({son_hata})")
