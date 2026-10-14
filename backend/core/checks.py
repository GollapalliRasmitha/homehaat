from django.conf import settings
from django.core.checks import Warning, register


@register()
def production_photos(app_configs, **kwargs):
    """In production without Cloudinary, photos would be saved on Render's disk, which is wiped at every restart."""
    if settings.DEBUG or settings.TESTING or settings.USE_CLOUDINARY:
        return []
    return [
        Warning(
            "Photos are being saved on this server's own disk. On Render that disk is wiped at every restart, "
            "so photos would disappear.",
            hint="Set CLOUDINARY_URL in the Render dashboard (docs/deploy.md, step 3).",
            id="homehaat.W001",
        )
    ]
