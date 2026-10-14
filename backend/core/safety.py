"""
Safety rule: nothing that deletes files or data may run unless it targets the THROWAWAY copy.

The throwaway copy is the test copy run beside the real one (ports 3001/8001). It is recognised by BOTH:
- its own database, THROWAWAY_DB ("homehaat_e2e"), and
- its own media folder: MEDIA_ROOT must contain THROWAWAY_MEDIA_MARK ("e2e-media") and must not be, or be inside,
  the real uploads folder (backend/media).
Checking only the database isn't enough: once a command had the right database but MEDIA_ROOT still pointing at the
real uploads, and only luck (a file name that didn't exist there) stopped it deleting a real photo.

Use assert_throwaway() at the top of any script or command that deletes, or run `manage.py throwaway_check` first
in a shell command (it exits with an error when it isn't the throwaway copy).
"""

from pathlib import Path

from django.conf import settings

THROWAWAY_DB = "homehaat_e2e"
THROWAWAY_MEDIA_MARK = "e2e-media"


class NotThrowawayError(RuntimeError):
    pass


def assert_throwaway() -> None:
    db = settings.DATABASES["default"]["NAME"]
    media = Path(settings.MEDIA_ROOT).resolve()
    real_media = (Path(settings.BASE_DIR) / "media").resolve()
    problems = []
    if db != THROWAWAY_DB:
        problems.append(f"the database is {db!r}, not {THROWAWAY_DB!r}")
    if media == real_media or real_media in media.parents or media in real_media.parents:
        problems.append(f"MEDIA_ROOT {media} is the real uploads folder (or contains it)")
    elif THROWAWAY_MEDIA_MARK not in str(media):
        problems.append(f"MEDIA_ROOT {media} isn't a throwaway media folder (no {THROWAWAY_MEDIA_MARK!r} in it)")
    if problems:
        raise NotThrowawayError("Refusing: this isn't the throwaway copy: " + "; ".join(problems) + ".")
