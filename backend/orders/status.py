"""
[KEY LOGIC] Moving a seller's part of an order along:

    new -> preparing -> out_for_delivery -> delivered
    new or preparing -> cancelled

Only the seller who owns that part may move it, only along these arrows,
and only the status changes: never the money.
"""

from django.db import transaction
from django.utils import timezone

from orders.models import Order, SellerOrder

S = SellerOrder.Status

# The only moves allowed: current status -> the statuses it may go to next.
ALLOWED_MOVES = {
    S.NEW: {S.PREPARING, S.CANCELLED},
    S.PREPARING: {S.OUT_FOR_DELIVERY, S.CANCELLED},
    S.OUT_FOR_DELIVERY: {S.DELIVERED},
    # delivered and cancelled are final: nothing allowed after them
}

# Which timestamp field to fill in for each new status.
TIMESTAMP_FIELD = {
    S.PREPARING: "preparing_at",
    S.OUT_FOR_DELIVERY: "out_for_delivery_at",
    S.DELIVERED: "delivered_at",
    S.CANCELLED: "cancelled_at",
}


class StatusError(Exception):
    """The move isn't allowed. `message` is safe to show to the seller."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotYourOrderError(StatusError):
    def __init__(self):
        super().__init__("Order not found.")  # same answer as a missing order: don't reveal it exists


@transaction.atomic
def advance_status(seller_order: SellerOrder, new_status: str, user) -> SellerOrder:
    # Lock this row: two taps at once (or two devices) are handled one after the other.
    part = SellerOrder.objects.select_for_update().select_related("seller", "order").get(pk=seller_order.pk)

    # 1. Ownership: only the seller of THIS part. Buyers and other sellers are refused.
    if part.seller.owner_id != user.id:
        raise NotYourOrderError()

    # 2. Only paid orders are real orders.
    if part.order.payment_status != Order.PaymentStatus.PAID:
        raise StatusError("This order hasn't been paid yet.")

    # 3. Only along the arrows.
    if new_status not in ALLOWED_MOVES.get(part.status, set()):
        current = S(part.status).label
        wanted = S(new_status).label if new_status in S.values else new_status
        raise StatusError(f"An order that is “{current}” can't be moved to “{wanted}”.")

    if new_status == S.CANCELLED:
        # Stock back + one Razorpay refund for exactly this part: all in orders/cancel.py.
        from orders.cancel import seller_cancel  # cancel imports this module, so import here

        return seller_cancel(part)

    part.status = new_status
    setattr(part, TIMESTAMP_FIELD[new_status], timezone.now())
    changed = ["status", TIMESTAMP_FIELD[new_status]]

    # update_fields: only these columns are written, so the money columns can't change here.
    part.save(update_fields=changed)
    return part
