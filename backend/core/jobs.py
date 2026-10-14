"""
Scheduled jobs without a paid scheduler [KEY LOGIC].

Two jobs keep HomeHaat tidy:
- "expire": give back stock held by checkouts left unpaid for 15 minutes (orders.services.expire_unpaid_orders).
- "refunds": send failed refunds again and check pending ones (payments.refunds.retry_refunds).

Render's cron jobs cost money, so they run in three free ways:
1. A GitHub Actions schedule (.github/workflows/scheduled-jobs.yml) calls POST /api/jobs/run/ with JOBS_SECRET in a
   header (run_jobs_view). Without the right secret nothing runs, so strangers can't trigger it.
2. When pages load: LazyJobsMiddleware runs "expire" at most once a minute while people use the site.
3. Checkout itself releases expired holds first (orders/services.py), so an old hold never blocks a buyer.

Both jobs are safe to run any time and any number of times (each one locks rows and skips work already done).
"""

import hmac
import logging

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger("homehaat")

LAZY_EVERY_SECONDS = 60
LAZY_KEY = "homehaat:lazy-expire"


def _expire():
    from orders.services import expire_unpaid_orders  # here: core is imported by every app

    return {"released": expire_unpaid_orders()}


def _refunds():
    from payments.refunds import retry_refunds

    return retry_refunds()


JOBS = {"expire": _expire, "refunds": _refunds}


def run_jobs(names) -> tuple[dict, bool]:
    """Run the named jobs one after another. One failing doesn't stop the others. Returns (results, all_ok)."""
    results, ok = {}, True
    for name in names:
        try:
            results[name] = JOBS[name]()
        except Exception:
            logger.exception("Scheduled job %s failed", name)
            results[name] = "failed"
            ok = False
    return results, ok


def secret_matches(sent: str) -> bool:
    secret = settings.JOBS_SECRET
    # Empty secret = switched off, never "anyone may". Constant-time compare, like the payment signatures.
    return bool(secret) and bool(sent) and hmac.compare_digest(sent.encode(), secret.encode())


@csrf_exempt  # called by the scheduler, not a browser; protected by the secret instead
@require_POST
def run_jobs_view(request):
    if not settings.JOBS_SECRET:
        return JsonResponse({"detail": "Scheduled jobs are switched off (JOBS_SECRET is not set)."}, status=503)
    if not secret_matches(request.headers.get("X-HomeHaat-Jobs-Secret", "")):
        return JsonResponse({"detail": "Not allowed."}, status=403)
    names = [n.strip() for n in request.GET.get("jobs", "expire,refunds").split(",") if n.strip()]
    unknown = [n for n in names if n not in JOBS]
    if unknown or not names:
        return JsonResponse({"detail": f"Unknown job: {', '.join(unknown) or '(none)'}."}, status=400)
    results, ok = run_jobs(names)
    return JsonResponse({"ok": ok, **results}, status=200 if ok else 500)


def run_lazy_expiry():
    """At most once a minute (per server process): release expired holds. Never breaks the page that triggered it."""
    if not cache.add(LAZY_KEY, True, LAZY_EVERY_SECONDS):  # add() only succeeds if nobody ran it in the last minute
        return
    run_jobs(["expire"])
