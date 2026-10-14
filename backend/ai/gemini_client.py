"""
The only file that talks to Google's Gemini API (free tier). Everything else calls generate_json().
The API key is sent in a header, never in the URL, and never written to the logs.

Models: settings.GEMINI_MODELS, tried in order. Google retires model names (that's what broke
gemini-2.5-flash for new keys) and busy models answer 503, so if one model is retired, busy, over its
free limit or too slow, we try the next. A key or request problem stops at once: another model won't fix it.
If every model was only busy, we wait 2 seconds and try the busy ones once more (within TIME_BUDGET).
A 429 is "busy" when it's the per-minute limit, but "daily_limit" when today's free quota is used up.
"""

import base64
import json
import logging
import time

import requests
from django.conf import settings

log = logging.getLogger("homehaat.ai")
URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
# Seconds to wait for an answer (connect, read). Flash-Lite gets a bit longer: when Google is busy it is
# often just slow (it timed out at 15 s), and it's the model most likely to answer on the free tier.
TIMEOUT = (5, 15)
LITE_TIMEOUT = (5, 20)
TIME_BUDGET = 50  # seconds for everything, retry included (the Next.js proxy waits 60 s, next.config.ts)
RETRY_AFTER = 2  # seconds before the one automatic retry
MIN_TIME_FOR_A_TRY = 8  # don't start a retry with less time left than this
TRY_NEXT_MODEL = {404, 429, 500, 502, 503, 504}  # retired, free limit, busy or broken on Google's side
# Google's reasons for refusing to describe a photo (e.g. a cartoon character or other protected content).
BLOCK_REASONS = {"SAFETY", "PROHIBITED_CONTENT", "IMAGE_SAFETY", "BLOCKLIST", "SPII", "RECITATION", "OTHER"}


class GeminiError(Exception):
    """
    No usable answer. `kind` says why, so the seller gets the right message:
    "busy" (Google overloaded or slow: try again in a minute), "daily_limit" (today's free quota is used up:
    try tomorrow) or "failed" (a key or request problem, or an answer we couldn't use).
    """

    def __init__(self, message, kind="failed"):
        super().__init__(message)
        self.kind = kind

    @property
    def busy(self):
        return self.kind == "busy"


class GeminiBlocked(GeminiError):
    """Google refused this photo or this answer for its own content rules."""


def _scrub(text) -> str:
    key = settings.GEMINI_API_KEY
    text = str(text)
    return text.replace(key, "<key>") if key else text


def timeout_for(model: str, seconds_left: float) -> tuple:
    connect, read = LITE_TIMEOUT if "lite" in model else TIMEOUT
    return connect, max(1, min(read, int(seconds_left)))  # never wait past the overall budget


def _error_kind(status: int, data) -> str:
    if status == 429:
        # Google names the quota that ran out: "...PerDay..." (wait until tomorrow) or "...PerMinute..." (busy).
        return "daily_limit" if "PerDay" in json.dumps(data) else "busy"
    return "busy" if status in TRY_NEXT_MODEL else "failed"


def _ask(model: str, body: dict, timeout: tuple) -> dict:
    try:
        response = requests.post(
            URL.format(model=model),
            headers={"x-goog-api-key": settings.GEMINI_API_KEY, "Content-Type": "application/json"},
            json=body,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise GeminiError(f"{model}: could not reach Gemini ({type(exc).__name__})", kind="busy") from exc

    try:
        data = response.json()
    except ValueError:
        data = {}
    if response.status_code != 200:
        error = data.get("error", {}) if isinstance(data, dict) else {}
        # Google's own words, e.g. "This model ... is no longer available to new users" (key removed).
        reason = _scrub(error.get("message", ""))[:300]
        kind = _error_kind(response.status_code, data)
        raise GeminiError(f"{model}: Gemini answered {response.status_code} ({kind}): {reason}", kind=kind)

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
    seconds_left = lambda: TIME_BUDGET - (time.monotonic() - started)  # noqa: E731
    models, errors = list(settings.GEMINI_MODELS), []
    for attempt in (1, 2):
        if attempt == 2:
            # Only busy models are worth another go; one that's out of quota for today will say so again.
            models = [m for m, e in errors if e.busy]
            if not models or seconds_left() < RETRY_AFTER + MIN_TIME_FOR_A_TRY:
                break
            log.info("AI: every model was busy; trying again in %s s", RETRY_AFTER)
            time.sleep(RETRY_AFTER)
            errors = []
        for model in models:
            if seconds_left() <= 0:
                break
            try:
                return _ask(model, body, timeout_for(model, seconds_left()))
            except GeminiBlocked:
                raise  # the same photo would be refused by the next model too
            except GeminiError as exc:
                log.warning("AI: %s", exc)  # the exact reason, for the Django window (never the key)
                if exc.kind == "failed":
                    raise  # a key or request problem: another model won't help
                errors.append((model, exc))
    if not errors:
        raise GeminiError("no Gemini model configured, or no time left", kind="busy")
    # Any model busy: "try again in a minute" can still work. Only if all are out for today: "try tomorrow".
    busy = [e for _, e in errors if e.busy]
    raise busy[-1] if busy else errors[-1][1]
