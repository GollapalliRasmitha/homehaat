from django.core.management.base import BaseCommand, CommandError

from core.safety import NotThrowawayError, assert_throwaway


class Command(BaseCommand):
    help = "Exit with an error unless this is the throwaway copy (its own database AND its own media folder)."

    def handle(self, *args, **options):
        try:
            assert_throwaway()
        except NotThrowawayError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write("OK: this is the throwaway copy.")
