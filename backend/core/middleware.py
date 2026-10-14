from django.conf import settings

from core.jobs import run_lazy_expiry

# Requests that must stay quick and never touch the database for this.
SKIP = ("/api/health/", "/api/jobs/", "/api/payments/webhook/")


class LazyJobsMiddleware:
    """When pages load, release expired stock holds (at most once a minute). See core/jobs.py."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if settings.LAZY_JOBS and path.startswith("/api/") and not path.startswith(SKIP):
            run_lazy_expiry()
        return self.get_response(request)
