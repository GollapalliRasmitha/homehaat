"""The safety guard: anything that deletes files or data must prove it targets the throwaway copy first."""

from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from core.safety import NotThrowawayError, assert_throwaway

REAL_MEDIA = Path(settings.BASE_DIR) / "media"
THROWAWAY_MEDIA = Path("C:/Temp/claude/scratchpad/e2e-media")


def db(name):
    return {"default": {**settings.DATABASES["default"], "NAME": name}}


class SafetyGuardTests(SimpleTestCase):
    def test_the_throwaway_copy_passes(self):
        with override_settings(DATABASES=db("homehaat_e2e"), MEDIA_ROOT=THROWAWAY_MEDIA):
            assert_throwaway()  # no error

    def test_the_real_database_is_refused(self):
        with override_settings(DATABASES=db("homehaat"), MEDIA_ROOT=THROWAWAY_MEDIA):
            with self.assertRaises(NotThrowawayError) as caught:
                assert_throwaway()
        self.assertIn("homehaat", str(caught.exception))

    def test_the_real_media_folder_is_refused_even_with_the_throwaway_database(self):
        # This is exactly the near miss from the QA run: right database, but MEDIA_ROOT pointing at real uploads.
        for media in (REAL_MEDIA, REAL_MEDIA / "products", Path(settings.BASE_DIR)):
            with override_settings(DATABASES=db("homehaat_e2e"), MEDIA_ROOT=media):
                with self.assertRaises(NotThrowawayError, msg=str(media)):
                    assert_throwaway()

    def test_a_media_folder_not_marked_as_throwaway_is_refused(self):
        with override_settings(DATABASES=db("homehaat_e2e"), MEDIA_ROOT=Path("C:/Users/rasmi/Pictures")):
            with self.assertRaises(NotThrowawayError):
                assert_throwaway()

    def test_the_command_refuses_with_a_non_zero_exit(self):
        with override_settings(DATABASES=db("homehaat"), MEDIA_ROOT=REAL_MEDIA):
            with self.assertRaises(CommandError):
                call_command("throwaway_check", stdout=StringIO())
        with override_settings(DATABASES=db("homehaat_e2e"), MEDIA_ROOT=THROWAWAY_MEDIA):
            out = StringIO()
            call_command("throwaway_check", stdout=out)
            self.assertIn("throwaway", out.getvalue())
