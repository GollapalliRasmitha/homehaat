"""
Create the admin account from two environment variables, because Render's free plan has no shell to run
`createsuperuser` in. Runs in backend/build.sh at every deploy:

- DJANGO_ADMIN_EMAIL and DJANGO_ADMIN_PASSWORD not both set -> nothing happens.
- No account with that email -> an admin account is created with that password.
- The account already exists -> nothing changes (its password is never changed). An ordinary account with that
  email is NOT turned into an admin: there's no email check at sign-up, so a stranger could have signed up with
  that address first. Use an email nobody has signed up with.

So after the first deploy the password variable can be deleted from the dashboard (docs/deploy.md).
The password is never printed.
"""

import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create the admin account from DJANGO_ADMIN_EMAIL / DJANGO_ADMIN_PASSWORD if it doesn't exist yet."

    def handle(self, *args, **options):
        email = os.getenv("DJANGO_ADMIN_EMAIL", "").strip().lower()
        password = os.getenv("DJANGO_ADMIN_PASSWORD", "")
        if not email or not password:
            self.stdout.write("Admin account: DJANGO_ADMIN_EMAIL / DJANGO_ADMIN_PASSWORD not set, nothing to do.")
            return

        User = get_user_model()
        user = User.objects.filter(email=email).first()
        if user:
            if user.is_staff and user.is_superuser:
                self.stdout.write(f"Admin account {email} already exists (password not changed).")
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"{email} is an ordinary account, so it was NOT made an admin. "
                        "Set DJANGO_ADMIN_EMAIL to an email nobody has signed up with."
                    )
                )
            return

        try:
            validate_password(password, User(email=email))
        except ValidationError as exc:
            raise CommandError("DJANGO_ADMIN_PASSWORD is too weak: " + " ".join(exc.messages)) from None
        User.objects.create_superuser(email, password, name="Admin")
        self.stdout.write(self.style.SUCCESS(f"Admin account {email} created."))
