"""
The only file that talks to Google's Gemini API (free tier). Everything else calls generate_json().
The API key is sent in a header, never in the URL, and never written to the logs.

Models: settings.GEMINI_MODELS, tried in order. Google retires model names (that's what broke
gemini-2.5-flash for new keys) and busy models answer 503, so if one model is retired, busy, over its
free limit or too slow, we try the next. A key or request problem stops at once: another model won't fix it.
"""

import base64
import json
import logging
import time

import requests
from django.conf import settings

log = logging.getLogger("homehaat.ai")
URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TIMEOUT = (5, 15)  # seconds: connect, read (Flash-Lite usually answers in 2-3 s)
TIME_BUDGET = 30  # seconds for all models together, so the seller isn't left waiting
TRY_NEXT_MODEL = {404, 429, 500, 502, 503, 504}  # retired, free limit, busy or broken on Google's side
# Google's reasons for refusing to describe a photo (e.g. a cartoon character or other protected content).
BLOCK_REASONS = {"SAFETY", "PROHIBITED_CONTENT", "IMAGE_SAFETY", "BLOCKLIST", "SPII", "RECITATION", "OTHER"}


class GeminiError(Exception):
    """No usable answer. `busy` = Google was busy/unreachable (try again later), not a problem with our request."""

    def __init__(self, message, busy=False):
        super().__init__(message)
        self.busy = busy


class GeminiBlocked(GeminiError):
    """Google refused this photo or this answer for its own content rules."""


def _scrub(text) -> str:
    key = settings.GEMINI_API_KEY
    text = str(text)
    return text.replace(key, "<key>") if key else text


def _ask(model: str, body: dict) -> dict:
    try:
        response = requests.post(
            URL.format(model=model),
            headers={"x-goog-api-key": settings.GEMINI_API_KEY, "Content-Type": "application/json"},
            json=body,
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        raise GeminiError(f"{model}: could not reach Gemini ({type(exc).__name__})", busy=True) from exc

    try:
        data = response.json()
    except ValueError:
        data = {}
    if response.status_code != 200:
        error = data.get("error", {}) if isinstance(data, dict) else {}
        # Google's own words, e.g. "This model ... is no longer available to new users" (key removed).
        reason = _scrub(error.get("message", ""))[:300]
        busy = response.status_code in TRY_NEXT_MODEL
        raise GeminiError(f"{model}: Gemini answered {response.status_code}: {reason}", busy=busy)

    if block := (data.get("promptFeedback") or {}).get("blockReason"):
        raise GeminiBlocked(f"{model}: photo blocked by Google ({block})")
    try:
        candidate = data["candidates"][0]
    except (KeyError, IndexError, TypeError) as exc:
        raise GeminiError(f"{model}: no answer in the reply") from exc
    if candidate.get("finishReason") in BLOCK_REASONS:
        raise GeminiBlocked(f"{model}: answer blocked by Google ({candidate['finishReason']})")
    try:
        text = "".join(part.get("text", "") for part in candidate["content"]["parts"])
        return json.loads(text)
    except (ValueError, KeyError, TypeError) as exc:
        finish = candidate.get("finishReason")
        raise GeminiError(f"{model}: the answer wasn't the JSON we asked for ({finish})") from exc


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
    started = time.monotonic()
    last = GeminiError("no Gemini model configured")
    for model in settings.GEMINI_MODELS:
        if time.monotonic() - started > TIME_BUDGET:
            break
        try:
            return _ask(model, body)
        except GeminiBlocked:
            raise  # the same photo would be refused by the next model too
        except GeminiError as exc:
            log.warning("AI: %s", exc)  # the exact reason, for the Django window (never the key)
            last = exc
            if not exc.busy:
                raise  # a key or request problem: another model won't help
    raise last
