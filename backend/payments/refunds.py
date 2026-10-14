"""
[KEY LOGIC] Sending refunds to Razorpay, exactly once per cancelled seller order.

- The Refund row (one per SellerOrder, enforced by the database) is created inside the cancel transaction.
- send_refund() runs after that commit. It locks the row, so a double click or two retries run one after the other,
  and it only calls Razorpay when no Razorpay refund id is saved yet.
- If Razorpay made the refund but our request timed out, a retry first LOOKS for it (by our note) instead of
  refunding again.
- Failures are saved as "failed" with the reason; retry_refunds (and the start script) tries them again.
"""

import logging

from django.db import transaction
from django.utils import timezone

from orders.models import Refund
from payments import razorpay_client

log = logging.getLogger("homehaat.payments")
MAX_ATTEMPTS = 10

# Razorpay's refund status -> ours.
STATUS = {"processed": Refund.Status.PROCESSED, "failed": Refund.Status.FAILED}


def _note_for(refund: Refund) -> str:
    return str(refund.seller_order_id)


def _already_at_razorpay(payment_id: str, refund: Refund):
    """A refund Razorpay already has for this part (we tag every refund with notes.homehaat_part)."""
    for existing in razorpay_client.list_refunds(payment_id):
        if str((existing.get("notes") or {}).get("homehaat_part", "")) == _note_for(refund):
            return existing
    return None


def _save_answer(refund: Refund, answer: dict) -> None:
    refund.razorpay_refund_id = answer["id"]
    refund.status = STATUS.get(answer.get("status"), Refund.Status.PENDING)
    if refund.status == Refund.Status.PROCESSED:
        refund.processed_at = timezone.now()
    refund.last_error = ""


@transaction.atomic
def send_refund(refund_id: int) -> Refund:
    """Send this refund to Razorpay if it hasn't been sent yet. Safe to call any number of times."""
    refund = Refund.objects.select_for_update().select_related("seller_order__order").get(pk=refund_id)
    if refund.razorpay_refund_id or refund.status == Refund.Status.PROCESSED:
        return refund  # already sent: never refund twice
    payment_id = refund.seller_order.order.razorpay_payment_id
    refund.attempts += 1
    try:
        if not payment_id:
            raise razorpay_client.RazorpayError("This order has no Razorpay payment to refund.")
        answer = _already_at_razorpay(payment_id, refund) if refund.attempts > 1 else None
        if answer is None:
            answer = razorpay_client.create_refund(
                payment_id=payment_id,
                amount_paise=refund.amount,  # computed on the server when the part was cancelled
                receipt=f"homehaat-part-{refund.seller_order_id}",
                notes={"homehaat_part": _note_for(refund)},
            )
        _save_answer(refund, answer)
    except razorpay_client.RazorpayError as exc:
        refund.status = Refund.Status.FAILED
        refund.last_error = str(exc)[:300]
        log.error("Refund %s for seller order %s failed: %s", refund.pk, refund.seller_order_id, exc)
    refund.save()
    return refund


@transaction.atomic
def refresh_refund(refund_id: int) -> Refund:
    """Ask Razorpay how a sent refund is doing (the webhook does this in production; this is the backup)."""
    refund = Refund.objects.select_for_update().get(pk=refund_id)
    if not refund.razorpay_refund_id or refund.status != Refund.Status.PENDING:
        return refund
    try:
        answer = razorpay_client.fetch_refund(refund.razorpay_refund_id)
    except razorpay_client.RazorpayError as exc:
        log.warning("Couldn't check refund %s: %s", refund.pk, exc)
        return refund
    apply_status(refund, answer.get("status"))
    return refund


def apply_status(refund: Refund, razorpay_status: str | None) -> None:
    """A refund's status from Razorpay (webhook or check). A failed refund is cleared so the retry sends a new one."""
    if razorpay_status == "processed" and refund.status != Refund.Status.PROCESSED:
        refund.status, refund.processed_at = Refund.Status.PROCESSED, timezone.now()
    elif razorpay_status == "failed":
        refund.last_error = f"Razorpay refund {refund.razorpay_refund_id} failed."
        refund.status, refund.razorpay_refund_id = Refund.Status.FAILED, None
    else:
        return
    refund.save()


@transaction.atomic
def apply_webhook(entity: dict) -> bool:
    """refund.processed / refund.failed from Razorpay. Returns False for a refund that isn't ours."""
    refund = Refund.objects.select_for_update().filter(razorpay_refund_id=entity.get("id")).first()
    if refund is None:
        return False
    apply_status(refund, entity.get("status"))
    return True


def retry_refunds() -> dict:
    """Send failed or unsent refunds again, and check pending ones. Run by `manage.py retry_refunds`."""
    counts = {"sent": 0, "still_failing": 0, "checked": 0}
    to_send = Refund.objects.filter(razorpay_refund_id__isnull=True, attempts__lt=MAX_ATTEMPTS).exclude(
        status=Refund.Status.PROCESSED
    )
    for refund_id in to_send.values_list("pk", flat=True):
        refund = send_refund(refund_id)
        counts["sent" if refund.status != Refund.Status.FAILED else "still_failing"] += 1
    pending = Refund.objects.filter(status=Refund.Status.PENDING, razorpay_refund_id__isnull=False)
    for refund_id in pending.values_list("pk", flat=True):
        refresh_refund(refund_id)
        counts["checked"] += 1
    return counts
