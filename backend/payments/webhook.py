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
from django.utils import timezone

from cart.models import CartItem
from catalog.models import Product
from orders.models import Order, OrderItem, SellerOrder


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
    Mark the order paid and clear those items from the cart.
    Returns True if this call did it, False if the order was already paid.
    """
    # Lock the order row: if two webhooks arrive at the same moment, the
    # second one waits here, then sees "paid" and does nothing.
    order = Order.objects.select_for_update().get(pk=order.pk)

    if order.payment_status == Order.PaymentStatus.PAID:
        return False  # idempotent: already done, so do nothing
    # "failed" is allowed: the buyer paid after the 15-minute hold ran out.
    if order.payment_status not in (Order.PaymentStatus.PENDING, Order.PaymentStatus.FAILED):
        raise PaymentError(f"Order {order.pk} is {order.payment_status}.")
    if amount_paise != order.grand_total:
        raise AmountMismatchError(f"Paid {amount_paise}, expected {order.grand_total}.")

    if not order.stock_held:
        # Late payment: the hold was released and the stock went back on the shelf.
        _take_stock_again(order)

    order.payment_status = Order.PaymentStatus.PAID
    order.razorpay_payment_id = payment_id
    order.paid_at = timezone.now()
    order.stock_held = True  # the stock now belongs to this paid order
    order.save(update_fields=["payment_status", "razorpay_payment_id", "paid_at", "stock_held"])

    # Remove only the products that were in this order; anything added later stays.
    items = OrderItem.objects.filter(seller_order__order=order, product__isnull=False)
    CartItem.objects.filter(user_id=order.buyer_id, product_id__in=items.values("product_id")).delete()
    return True


def _take_stock_again(order: Order) -> None:
    """
    For a late payment, try to take each seller's items off the shelf again.
    A seller whose items are no longer all there gets their part cancelled with
    "refund needed" (the money was taken, so we must record it, not lose it).
    """
    for seller_order in order.seller_orders.prefetch_related("items"):
        items = [item for item in seller_order.items.all() if item.product_id]
        locked = Product.objects.select_for_update().filter(id__in=[i.product_id for i in items]).order_by("id")
        stock = {product.id: product.stock for product in locked}

        if all(stock.get(item.product_id, 0) >= item.qty for item in items):
            for item in items:
                # F() = "stock = stock - qty" done by the database, on rows we have locked.
                Product.objects.filter(pk=item.product_id).update(stock=F("stock") - item.qty)
        else:
            seller_order.status = SellerOrder.Status.CANCELLED
            seller_order.cancelled_at = timezone.now()
            seller_order.refund_needed = True
            seller_order.save(update_fields=["status", "cancelled_at", "refund_needed"])
