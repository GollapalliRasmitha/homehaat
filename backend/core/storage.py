"""
Photos on Cloudinary (production). Used only when CLOUDINARY_URL is set; locally photos stay in MEDIA_ROOT.

- Product photos and shop covers are uploaded as PUBLIC images ("upload" type): their URL goes straight to
  Cloudinary's CDN, with f_auto,q_auto so each browser gets a small modern format (WebP/AVIF).
- Custom request photos (names starting "requests/") are uploaded as AUTHENTICATED images: Cloudinary refuses every
  unsigned URL to them, original or resized. Their URL is never given to a browser. The browser asks Django
  (/api/private-media/requests/<file>, core/media.py), Django checks the buyer/seller, then reads the photo from
  Cloudinary itself with a signed URL (_open below) and passes the bytes on.
- The stored name stays exactly as before ("products/<uuid>.jpg"), so models, serializers and the private route
  work the same on both storages. On Cloudinary the public id is "homehaat/products/<uuid>".

This file is the only one that talks to Cloudinary.
"""

import cloudinary
import cloudinary.uploader
import cloudinary.utils
import requests
from django.core.files.base import ContentFile
from django.core.files.storage import Storage

from core.media import PRIVATE_PREFIX, PRIVATE_URL

FOLDER = "homehaat"
TIMEOUT = 20  # seconds, for reading a private photo back from Cloudinary


def _split(name: str) -> tuple[str, str]:
    """ "products/ab12.jpg" -> ("homehaat/products/ab12", "jpg")."""
    stem, _, ext = name.rpartition(".")
    return f"{FOLDER}/{stem}", ext.lower()


def delivery_type(name: str) -> str:
    return "authenticated" if name.startswith(PRIVATE_PREFIX) else "upload"


class CloudinaryStorage(Storage):
    def __init__(self):
        cloudinary.reset_config()  # (re)reads CLOUDINARY_URL from the environment (settings.py checked it)
        cloudinary.config(secure=True)  # https links only

    def _save(self, name, content):
        public_id, _ = _split(name)
        content.seek(0)
        cloudinary.uploader.upload(
            content.read(),
            public_id=public_id,
            type=delivery_type(name),
            resource_type="image",
            overwrite=False,
        )
        return name

    def _open(self, name, mode="rb"):
        """Server-side read (used for private request photos). A signed URL, used here and never sent anywhere."""
        public_id, ext = _split(name)
        url, _ = cloudinary.utils.cloudinary_url(
            public_id, format=ext, type=delivery_type(name), resource_type="image", sign_url=True, secure=True
        )
        response = requests.get(url, timeout=TIMEOUT)
        if response.status_code != 200:
            raise FileNotFoundError(name)
        return ContentFile(response.content, name=name)

    def url(self, name):
        if name.startswith(PRIVATE_PREFIX):
            return PRIVATE_URL + name  # never a Cloudinary link for a private photo
        public_id, ext = _split(name)
        url, _ = cloudinary.utils.cloudinary_url(
            public_id,
            format=ext,
            type="upload",
            resource_type="image",
            secure=True,
            fetch_format="auto",
            quality="auto",
        )
        return url

    def delete(self, name):
        public_id, _ = _split(name)
        cloudinary.uploader.destroy(public_id, type=delivery_type(name), resource_type="image", invalidate=True)

    def exists(self, name):
        # Every stored name is a fresh random uuid (catalog/images.py), so it can't already be taken. Asking
        # Cloudinary here would cost an Admin API call (limited per hour) on every upload.
        return False
