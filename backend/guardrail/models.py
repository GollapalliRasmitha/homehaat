from django.db import models


class OutboxEvent(models.Model):
    """A security event GuardRail couldn't take yet (it was down or slow). Sent again later by guardrail.client."""

    payload = models.JSONField()  # the event, already masked: no passwords, no full emails
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["id"]
