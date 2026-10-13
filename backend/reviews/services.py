"""
Writing a review [KEY LOGIC]. A buyer may review a maker only after one of that maker's
orders has been delivered to them. One review per buyer per maker: writing again edits it.
"""

from django.db import transaction

from orders.models import Order, SellerOrder
from reviews.models import Review

MAX_COMMENT = 1000


class ReviewError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


def has_delivered_order(user, seller) -> bool:
    """True if this buyer has a paid order part from this seller that reached "delivered"."""
    return SellerOrder.objects.filter(
        seller=seller,
        order__buyer=user,
        order__payment_status=Order.PaymentStatus.PAID,
        status=SellerOrder.Status.DELIVERED,
    ).exists()


@transaction.atomic
def write_review(user, seller, rating, comment=""):
    """Create or edit this buyer's review of this seller. Returns (review, created)."""
    if seller.owner_id == user.id:
        raise ReviewError("You can't review your own shop.")
    # bool is a kind of int in Python, so True would pass as 1: refuse it explicitly.
    if not isinstance(rating, int) or isinstance(rating, bool) or not 1 <= rating <= 5:
        raise ReviewError("Choose a rating from 1 to 5 stars.")
    comment = (comment or "").strip()
    if len(comment) > MAX_COMMENT:
        raise ReviewError(f"Please keep your review under {MAX_COMMENT} characters.")
    if not has_delivered_order(user, seller):
        raise ReviewError("You can review a maker once one of their orders has been delivered to you.")

    # The database allows one row per (seller, buyer), so a second review edits the first.
    return Review.objects.update_or_create(seller=seller, buyer=user, defaults={"rating": rating, "comment": comment})
