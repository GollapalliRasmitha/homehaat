from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health(request):
    """GET /api/health/: "the server is up". No database, no sign-in, so it answers fast.

    Used by Render's health check, and by the website to wake the free server before checkout
    (frontend/lib/api/wake.ts).
    """
    response = JsonResponse({"ok": True})
    response["Cache-Control"] = "no-store"
    return response
