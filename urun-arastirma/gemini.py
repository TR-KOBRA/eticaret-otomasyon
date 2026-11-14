"""Gemini metin modeli için küçük REST yardımcısı (ek paket gerektirmez).

.env içinde GEMINI_API_KEY gerekir. Model GEMINI_METIN_MODEL ile değiştirilebilir.
Anahtar asla yazdırılmaz; hata mesajlarında da geçmez.
"""
from __future__ import annotations

import json
import os
import time

import requests

URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiYok(RuntimeError):
    pass


def model() -> str:
    return os.getenv("GEMINI_METIN_MODEL", "gemini-3.5-flash")


def var_mi() -> bool:
    return bool(os.getenv("GEMINI_API_KEY"))


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
    for i in range(deneme):
        try:
            r = requests.post(URL.format(model=model()), json=govde, timeout=90,
                              headers={"x-goog-api-key": anahtar, "Content-Type": "application/json"})
            if r.status_code in (429, 500, 502, 503, 504):
                son_hata = f"HTTP {r.status_code}"
                time.sleep(4 * (i + 1))
                continue
            if r.status_code != 200:
                raise RuntimeError(f"Gemini HTTP {r.status_code}: {r.text[:300]}")
            d = r.json()
            parca = d["candidates"][0]["content"]["parts"]
            metin = "".join(p.get("text", "") for p in parca if not p.get("thought"))
            return json.loads(metin)
        except (requests.RequestException, KeyError, IndexError, json.JSONDecodeError) as e:
            son_hata = f"{type(e).__name__}: {e}"
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"Gemini yanıtı alınamadı ({son_hata})")
