import logging

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from ai.listing import BLOCKED, FAILED, ListingError, write_listing
from catalog.images import ImageError, clean_image
from catalog.models import Category, ProductImage
from catalog.views import IsSeller

log = logging.getLogger("homehaat.ai")
MIME = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


class ListingThrottle(UserRateThrottle):
    scope = "ai_listing"  # 10 per hour per seller (settings)


def ai_enabled() -> bool:
    return settings.AI_ENABLED and bool(settings.GEMINI_API_KEY)


@api_view(["GET", "POST"])
@permission_classes([IsSeller])
@parser_classes([MultiPartParser, FormParser])
def listing(request):
    """
    GET: {"enabled": bool}, so the form only shows "Write listing with AI" when it can work.
    POST: a photo (`image` file, or `image_id` of a photo on one of my products) + optional `name`
    -> {title, description, category} for the seller to edit. Nothing is saved.
    """
    if request.method == "GET":
        return Response({"enabled": ai_enabled()})
    if not ai_enabled():
        return Response({"detail": FAILED}, status=503)  # the app works fully without AI
    if not ListingThrottle().allow_request(request, None):
        return Response({"detail": "You've used the AI helper a lot this hour. Please try again later."}, status=429)

    if image_id := request.data.get("image_id"):
        saved = get_object_or_404(ProductImage, pk=image_id, product__seller=request.user.seller)
        with saved.image.open("rb") as f:
            photo, name = f.read(), saved.image.name
    else:
        try:
            cleaned = clean_image(request.FILES.get("image"))  # same checks as uploads; EXIF/GPS removed
        except ImageError as exc:
            return Response({"detail": exc.message}, status=400)
        photo, name = cleaned.read(), cleaned.name
    mime = MIME.get(name.rsplit(".", 1)[-1].lower(), "image/jpeg")

    slugs = set(Category.objects.values_list("slug", flat=True))
    try:
        suggestion = write_listing(photo, mime, slugs, hint=str(request.data.get("name", "")).strip())
    except ListingError as exc:
        log.warning("AI listing failed for seller %s: %s", request.user.seller.pk, exc)
        # 422: Google refused this photo (try another); 503: AI unavailable right now.
        return Response({"detail": exc.message}, status=422 if exc.message == BLOCKED else 503)
    return Response(suggestion)
