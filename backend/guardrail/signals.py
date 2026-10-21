"""
Sign-ins, reported through Django's own login signals. Django sends them for the HomeHaat API sign-in AND the
Django admin, so no view had to change. user_login_failed gets the credentials with the password already blanked by
Django; we only ever read the email from them.
"""

from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver

from guardrail.client import report


@receiver(user_login_failed)
def on_login_failed(sender, credentials, request=None, **kwargs):
    email = credentials.get("email") or credentials.get("username")
    meta = {"reason": "admin_form"} if request is not None and request.path.startswith("/admin/") else None
    report("login_failed", request, actor=email, meta=meta)


@receiver(user_logged_in)
def on_logged_in(sender, request, user, **kwargs):
    is_admin = user.is_staff or getattr(user, "role", "") == "admin"
    report("admin_login" if is_admin else "login_success", request, actor=user.email, meta={"role": user.role})
