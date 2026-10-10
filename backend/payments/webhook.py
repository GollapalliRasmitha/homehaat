"""
[KEY LOGIC] Confirming a payment.

An order becomes "paid" ONLY here, after we have proved the message really
came from Razorpay (signature) and the money matches (amount check).
Both the webhook and the local /api/payments/verify/ backup end in the same
mark_order_paid(), which is safe to call many times.
"""

import hashlib
import hmac

from django.db import transaction
from django.db.models import F
from django.db.models.functions import Greatest
from django.utils import timezone

from cart.models import CartItem
from catalog.models import Product
from orders.models import Order, OrderItem


class PaymentError(Exception):
    pass


class AmountMismatchError(PaymentError):
    pass


def _signature_matches(message: bytes, signature: str, secret: str) -> bool:
    if not secret or not signature:
        return False  # no secret configured, or no signature sent: never trust it
    expected = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    # compare_digest takes the same time whether the first or last character
    # differs, so an attacker can't guess the signature one character at a time.
    return hmac.compare_digest(expected, signature)


def verify_webhook_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    """Razorpay signs the exact raw request body with the webhook secret."""
    return _signature_matches(raw_body, signature, secret)


def verify_checkout_signature(razorpay_order_id: str, payment_id: str, signature: str, secret: str) -> bool:
    """Checkout.js signs "order_id|payment_id" with the key secret."""
    return _signature_matches(f"{razorpay_order_id}|{payment_id}".encode(), signature, secret)


@transaction.atomic
def mark_order_paid(order: Order, payment_id: str, amount_paise: int) -> bool:
    """
    Mark the order paid, reduce stock and clear those items from the cart.
    Returns True if this call did it, False if the order was already paid.
    """
    # Lock the order row: if two webhooks arrive at the same moment, the
    # second one waits here, then sees "paid" and does nothing.
    order = Order.objects.select_for_update().get(pk=order.pk)

    if order.payment_status == Order.PaymentStatus.PAID:
        return False  # idempotent: already done, so do nothing
    if order.payment_status != Order.PaymentStatus.PENDING:
        raise PaymentError(f"Order {order.pk} is {order.payment_status}, not pending.")
    if amount_paise != order.grand_total:
        raise AmountMismatchError(f"Paid {amount_paise}, expected {order.grand_total}.")

    order.payment_status = Order.PaymentStatus.PAID
    order.razorpay_payment_id = payment_id
    order.paid_at = timezone.now()
    order.save(update_fields=["payment_status", "razorpay_payment_id", "paid_at"])

    items = OrderItem.objects.filter(seller_order__order=order, product__isnull=False)
    for item in items:
        # F("stock") - qty runs as "stock = stock - qty" inside the database,
        # so it can't overwrite a change someone else made a moment ago.
        # Greatest(..., 0) stops it going below zero: the money is already taken,
        # so we must still record the payment. (Stage 2 prevents overselling.)
        Product.objects.filter(pk=item.product_id).update(stock=Greatest(F("stock") - item.qty, 0))

    # Remove only the products that were in this order; anything added later stays.
    CartItem.objects.filter(user_id=order.buyer_id, product_id__in=items.values("product_id")).delete()
    return True
