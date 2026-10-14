"""
Serving uploaded photos.

- Product photos and shop covers are public: /media/<path>.
- Custom request photos (MEDIA_ROOT/requests/) are PRIVATE: only that request's buyer and that shop's owner may see
  them. They are never served from /media/; their URL is /api/private-media/requests/<file>, and that view checks who
  is asking (session cookie, sent by the browser through the Next.js proxy) and answers 404 to everyone else, the same
  answer as for a file that doesn't exist, so nobody learns the photo is there.
- An accepted custom item's picture is the same file (custom_requests.services.use_reference_photo), so the bag,
  checkout and orders use the same private URL and the same rule.

public_url() is the ONE place a photo URL is made: serializers call it instead of `field.url`.
"""

import mimetypes
import re

from django.conf import settings
from django.core.files.storage import default_storage
from django.db.models import Q
from django.http import FileResponse, Http404
from django.views.static import serve

PRIVATE_PREFIX = "requests/"
PRIVATE_URL = "/api/private-media/"
SAFE_NAME = re.compile(r"^[A-Za-z0-9_-]+\.(?:jpg|jpeg|png|webp)$")  # our own file names (uuid hex + extension)


def public_url(field_file) -> str | None:
    """The URL a browser should use for this stored photo. Request photos get the private route."""
    if not field_file:
        return None
    name = field_file.name
    return PRIVATE_URL + name if name.startswith(PRIVATE_PREFIX) else field_file.url


def serve_public_media(request, path):
    """/media/<path> for public photos only. Request photos are refused here (404) whoever asks."""
    if path.startswith(PRIVATE_PREFIX) or "/" + PRIVATE_PREFIX in "/" + path:
        raise Http404
    return serve(request, path, document_root=settings.MEDIA_ROOT)


def private_request_photo(request, name):
    """/api/private-media/requests/<name>: only that request's buyer and that shop's owner. Everyone else: 404."""
    from custom_requests.models import CustomRequestImage  # here: custom_requests imports catalog, catalog imports core

    if not SAFE_NAME.match(name) or not request.user.is_authenticated:
        raise Http404
    user = request.user
    allowed = CustomRequestImage.objects.filter(image=PRIVATE_PREFIX + name).filter(
        Q(request__buyer=user) | Q(request__seller__owner=user)
    )
    if not allowed.exists():
        raise Http404
    try:
        # The configured storage: MEDIA_ROOT locally, Cloudinary's authenticated photos in production (core/storage.py).
        photo = default_storage.open(PRIVATE_PREFIX + name)
    except OSError:  # FileNotFoundError included
        raise Http404 from None
    response = FileResponse(photo, content_type=mimetypes.guess_type(name)[0] or "image/jpeg")
    response["Cache-Control"] = "private, max-age=300"  # this person's browser only; never a shared cache
    response["X-Content-Type-Options"] = "nosniff"
    return response
