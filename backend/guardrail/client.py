"""
[KEY LOGIC] Sending security events to GuardRail (the monitoring dashboard), without ever slowing down or breaking
HomeHaat.

    report("login_failed", request, actor=email)      <- the only function the rest of HomeHaat calls

1. report() builds a small event (email masked, path without its query string, only allow-listed extra details),
   puts it in an in-memory queue and returns at once. It never raises and never waits for the network.
2. A background thread takes up to 50 queued events, signs them (HMAC-SHA256, the same scheme GuardRail checks in
   lib/ingest/signature.ts) and POSTs them with a 2-second timeout.
3. GuardRail down, slow, 5xx or 429 -> the events go into the OutboxEvent table and are sent again later: right
   after the next successful send, and by the scheduled "guardrail" job (core/jobs.py). The outbox is capped.
   A 4xx answer means GuardRail refused them (it would refuse again), so they're dropped and logged.
   Every event carries a random "uid", kept through retries: if GuardRail saved a batch but answered too slowly,
   the retry is recognised and stored once (at-least-once sending + de-duplication = each event exactly once).
4. Off switch: nothing happens unless GUARDRAIL_ENABLED=true AND GUARDRAIL_URL AND GUARDRAIL_SECRET are set.
"""

import hashlib
import hmac
import json
import logging
import queue
import secrets
import threading
import time
import uuid
from datetime import timedelta

import requests
from django.conf import settings
from django.db import close_old_connections, transaction
from django.db.models import F
from django.utils import timezone

from core.client_ip import client_country, client_ip

log = logging.getLogger("homehaat.guardrail")

SOURCE = "homehaat"
TIMEOUT_SECONDS = 2  # never wait longer than this for GuardRail
BATCH_SIZE = 50  # GuardRail accepts up to 50 events per request
MAX_QUEUE = 1000  # in memory; if it's ever full, new events are dropped (never block a user)
MAX_OUTBOX = 5000  # in the database; oldest dropped first
MAX_ATTEMPTS = 20
MAX_AGE = timedelta(days=7)  # GuardRail refuses events older than 7 days anyway
META_KEYS = ("reason", "limit", "role", "order_ref", "amount_paise", "gateway", "device", "count")

_queue: "queue.Queue[dict]" = queue.Queue(maxsize=MAX_QUEUE)
_worker_lock = threading.Lock()
_worker: threading.Thread | None = None


def is_enabled() -> bool:
    return bool(settings.GUARDRAIL_ENABLED and settings.GUARDRAIL_URL and len(settings.GUARDRAIL_SECRET or "") >= 32)


# ---- building an event (privacy first) ----------------------------------------------------------------------------


def mask_actor(value: str | None) -> str | None:
    """'priya@gmail.com' -> 'pr****@gmail.com'. GuardRail masks again; this way the full email never even leaves."""
    value = (value or "").strip().lower()
    if not value:
        return None
    if "@" in value:
        name, domain = value.rsplit("@", 1)
        return f"{name[:2]}****@{domain}"
    return f"{value[:2]}****"


def actor_id(value: str | None) -> str | None:
    """
    A keyed hash of the full email: same account -> same id, different accounts -> different ids, but nobody can turn
    it back into the email. GuardRail's per-account rules need it because masked emails collide
    ("victim@" and "vivek@" both become "vi****@"). Keyed with GUARDRAIL_SECRET, so it can't be built from a list
    of known emails by someone without the secret.
    """
    value = (value or "").strip().lower()
    if not value:
        return None
    return hmac.new(settings.GUARDRAIL_SECRET.encode(), f"actor:{value}".encode(), hashlib.sha256).hexdigest()[:32]


def build_event(event_type: str, request=None, *, actor=None, path=None, status_code=None, meta=None) -> dict:
    # uid: a random id made once, here. Retries resend the same uid, so GuardRail can store each event only once
    # even when a slow answer made us retry something it had already saved.
    event = {"type": event_type, "uid": uuid.uuid4().hex, "occurred_at": timezone.now().isoformat()}
    if request is not None:
        event["ip"] = client_ip(request) or None
        event["country"] = client_country(request)
        event["method"] = request.method
        event["user_agent"] = request.META.get("HTTP_USER_AGENT", "")[:200]
        path = path or request.path
        user = getattr(request, "user", None)
        if actor is None and user is not None and user.is_authenticated:
            actor = user.email
    event["path"] = (path or "").split("?", 1)[0].split("#", 1)[0][:300] or None
    event["actor"] = mask_actor(actor)
    event["actor_id"] = actor_id(actor)
    event["status_code"] = status_code
    event["meta"] = {k: v for k, v in (meta or {}).items() if k in META_KEYS}
    return {k: v for k, v in event.items() if v not in (None, "", {})}


# ---- the public entry point -----------------------------------------------------------------------------------------


def report(event_type: str, request=None, **fields) -> None:
    """Record a security event. Returns immediately. Never raises, whatever happens."""
    try:
        if not is_enabled():
            return
        event = build_event(event_type, request, **fields)
        if settings.GUARDRAIL_SYNC:  # tests only: send right here, so tests are deterministic
            deliver([event])
            return
        _start_worker()
        _queue.put_nowait(event)
    except queue.Full:
        log.warning("GuardRail queue is full; dropped a %s event.", event_type)
    except Exception:
        log.exception("Couldn't report a %s event to GuardRail (ignored).", event_type)


# ---- sending --------------------------------------------------------------------------------------------------------


def sign(secret: str, timestamp: int, nonce: str, body: bytes) -> str:
    """hex(HMAC-SHA256(secret, "v1:<timestamp>:<nonce>:<body>")), exactly what GuardRail checks."""
    message = f"v1:{timestamp}:{nonce}:".encode() + body
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def send_batch(events: list[dict]) -> str:
    """POST one signed batch. Returns "ok", "retry" (try again later) or "drop" (GuardRail refused it)."""
    body = json.dumps({"events": events}, separators=(",", ":")).encode()
    timestamp = int(time.time())
    nonce = secrets.token_hex(16)  # new for every request, so GuardRail can refuse replays
    headers = {
        "Content-Type": "application/json",
        "X-GuardRail-Source": SOURCE,
        "X-GuardRail-Timestamp": str(timestamp),
        "X-GuardRail-Nonce": nonce,
        "X-GuardRail-Signature": sign(settings.GUARDRAIL_SECRET, timestamp, nonce, body),
    }
    url = settings.GUARDRAIL_URL.rstrip("/") + "/api/ingest"
    try:
        answer = requests.post(url, data=body, headers=headers, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        log.warning("GuardRail unreachable (%s); will retry later.", type(exc).__name__)
        return "retry"
    if 200 <= answer.status_code < 300:
        return "ok"
    if answer.status_code == 429 or answer.status_code >= 500:
        return "retry"
    log.error("GuardRail refused %d events (HTTP %s); dropped.", len(events), answer.status_code)
    return "drop"


def deliver(events: list[dict]) -> None:
    """Send now; keep for later if GuardRail can't take them. When it can, also send a little of the backlog."""
    result = send_batch(events)
    if result == "retry":
        save_to_outbox(events)
    elif result == "ok":
        try:  # the events above are delivered; a problem with the backlog must not be mistaken for losing them
            flush_outbox(max_batches=2)
        except Exception:
            log.exception("Couldn't send GuardRail's waiting events; the scheduled job will try again.")


# ---- the outbox (events waiting to be sent again) --------------------------------------------------------------------


def save_to_outbox(events: list[dict]) -> None:
    from guardrail.models import OutboxEvent

    OutboxEvent.objects.bulk_create([OutboxEvent(payload=e) for e in events])
    extra = OutboxEvent.objects.count() - MAX_OUTBOX
    if extra > 0:  # full: drop the oldest, keep the newest
        oldest = OutboxEvent.objects.order_by("id").values_list("id", flat=True)[:extra]
        OutboxEvent.objects.filter(id__in=list(oldest)).delete()
        log.warning("GuardRail outbox full; dropped %d oldest events.", extra)


def flush_outbox(max_batches: int = 10) -> dict:
    """Send waiting events, oldest first. Safe to run often and from several places (rows are locked)."""
    from guardrail.models import OutboxEvent

    counts = {"sent": 0, "dropped": 0, "waiting": 0}
    too_old = timezone.now() - MAX_AGE
    counts["dropped"] += OutboxEvent.objects.filter(created_at__lt=too_old).delete()[0]
    counts["dropped"] += OutboxEvent.objects.filter(attempts__gte=MAX_ATTEMPTS).delete()[0]
    for _ in range(max_batches):
        with transaction.atomic():
            # skip_locked: if the scheduled job and a background send flush at the same time, they take
            # different rows instead of sending the same events twice.
            rows = list(OutboxEvent.objects.select_for_update(skip_locked=True).order_by("id")[:BATCH_SIZE])
            if not rows:
                break
            result = send_batch([row.payload for row in rows])
            ids = [row.id for row in rows]
            if result == "retry":
                OutboxEvent.objects.filter(id__in=ids).update(attempts=F("attempts") + 1)
                break
            OutboxEvent.objects.filter(id__in=ids).delete()
            counts["sent" if result == "ok" else "dropped"] += len(ids)
    counts["waiting"] = OutboxEvent.objects.count()
    return counts


# ---- the background thread ------------------------------------------------------------------------------------------


def _start_worker() -> None:
    global _worker
    if _worker is not None and _worker.is_alive():
        return
    with _worker_lock:  # two requests at once must not start two threads
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_run, name="guardrail-sender", daemon=True)
            _worker.start()


def _run() -> None:
    while True:
        batch = [_queue.get()]  # wait for the first event
        deadline = time.monotonic() + 1  # then collect what arrives in the next second (fewer requests)
        while len(batch) < BATCH_SIZE:
            try:
                batch.append(_queue.get(timeout=max(0, deadline - time.monotonic())))
            except queue.Empty:
                break
        try:
            deliver(batch)
        except Exception:
            log.exception("GuardRail sender failed; %d events lost.", len(batch))
        finally:
            close_old_connections()  # this thread has its own database connection; don't leak it
