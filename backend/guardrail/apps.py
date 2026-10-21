from django.apps import AppConfig


class GuardrailConfig(AppConfig):
    """Sends security events to GuardRail, the monitoring dashboard. See client.py."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "guardrail"

    def ready(self):
        from guardrail import signals  # noqa: F401  (connects the login signals)
