"""
Checking and cleaning uploaded photos (product photos, shop covers).

- Only real JPEG, PNG or WebP images, at most 5 MB. The file is opened and decoded,
  so a renamed script or a broken file is refused, whatever its name says.
- The photo is re-saved without its EXIF data. Phone photos often contain the GPS
  location where they were taken (often the seller's home), so we never keep it.
- Big photos are shrunk so the longest side is at most 1600 px.
"""

import io
import uuid

from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 5 * 1024 * 1024
MAX_SIDE = 1600
ALLOWED = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


class ImageError(Exception):
    """`message` is safe to show to the seller."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def clean_image(upload) -> ContentFile:
    if upload is None:
        raise ImageError("Please choose a photo.")
    if upload.size > MAX_BYTES:
        raise ImageError("That photo is over 5 MB. Please choose a smaller one.")
    try:
        with Image.open(upload) as original:
            kind = original.format
            if kind not in ALLOWED:
                raise ImageError("Please use a JPEG, PNG or WebP photo.")
            image = ImageOps.exif_transpose(original)  # turn it upright before the rotation info is dropped
            image.load()  # actually decode it: proves it's a real image
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ImageError("That file isn't a photo we can read.") from exc

    image.thumbnail((MAX_SIDE, MAX_SIDE))  # keeps the shape; does nothing if already small enough
    if kind == "JPEG" and image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    out = io.BytesIO()
    # Saving without exif=... writes a clean file: no GPS, no camera details.
    image.save(out, kind, quality=85, optimize=True)
    return ContentFile(out.getvalue(), name=f"{uuid.uuid4().hex}.{ALLOWED[kind]}")
