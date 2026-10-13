"""
The only file that talks to Google's Gemini API (free tier). Everything else calls generate_json().
The API key is sent in a header, never in the URL, so it can't end up in logs.
"""

import base64
import json
import logging

import requests
from django.conf import settings

log = logging.getLogger("homehaat.ai")
URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TIMEOUT_SECONDS = 25


class GeminiError(Exception):
    """Anything went wrong: no answer, the free limit is used up, or the answer wasn't JSON."""


def generate_json(prompt: str, image: bytes, mime_type: str, schema: dict) -> dict:
    body = {
        "contents": [
            {
                "parts": [
                    {"inline_data": {"mime_type": mime_type, "data": base64.b64encode(image).decode()}},
                    {"text": prompt},
                ]
            }
        ],
        "generationConfig": {
            # Gemini must answer with JSON in exactly this shape (we still check it afterwards).
            "responseMimeType": "application/json",
            "responseSchema": schema,
            "temperature": 0.4,
            "maxOutputTokens": 2048,
        },
    }
    try:
        response = requests.post(
            URL.format(model=settings.GEMINI_MODEL),
            headers={"x-goog-api-key": settings.GEMINI_API_KEY, "Content-Type": "application/json"},
            json=body,
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise GeminiError(f"could not reach Gemini: {type(exc).__name__}") from exc

    if response.status_code == 429:
        raise GeminiError("free limit used up (429)")
    if response.status_code != 200:
        raise GeminiError(f"Gemini answered {response.status_code}")
    try:
        candidate = response.json()["candidates"][0]
        text = "".join(part.get("text", "") for part in candidate["content"]["parts"])
        return json.loads(text)
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise GeminiError("the answer wasn't the JSON we asked for") from exc
