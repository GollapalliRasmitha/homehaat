"""
Watches every response (it never changes one) and reports three kinds of trouble to GuardRail:
- suspicious_path: requests for things HomeHaat doesn't have but attackers look for (/wp-admin, /.env, /.git…)
- rate_limited: any 429 (a rate limit said no)
- permission_denied: a 403 for a signed-in user, or a wrong scheduled-jobs secret
Reporting only puts an event in a queue (guardrail/client.py), so this adds microseconds, not network time.
"""

import logging
import re

from guardrail.client import report

log = logging.getLogger("homehaat.guardrail")

# Paths scanners try. HomeHaat has none of these, so a request for one is never a real visitor.
SUSPICIOUS = re.compile(
    r"^/(wp-admin|wp-login\.php|wp-content|wp-includes|xmlrpc\.php|\.env|\.git|\.aws|\.ssh|\.DS_Store|"
    r"phpmyadmin|pma|cgi-bin|server-status|vendor/phpunit|actuator|boaform|config\.json|"
    r"[^?]*\.(php|asp|aspx|jsp|cgi|bak|sql)$)",
    re.IGNORECASE,
)


class GuardRailMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            self.inspect(request, response.status_code)
        except Exception:  # monitoring must never break a page
            log.exception("GuardRail middleware failed (ignored).")
        return response

    @staticmethod
    def inspect(request, status: int) -> None:
        path = request.path
        if SUSPICIOUS.match(path):
            report("suspicious_path", request, status_code=status)
        elif status == 429:
            report("rate_limited", request, status_code=status, meta={"reason": "throttled"})
        elif status == 403:
            user = getattr(request, "user", None)
            if path.startswith("/api/jobs/"):
                report("permission_denied", request, status_code=status, meta={"reason": "jobs_secret"})
            elif user is not None and user.is_authenticated:
                report("permission_denied", request, status_code=status)
