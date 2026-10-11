"""
[KEY LOGIC] Turning a buyer's bag into an order, and holding the stock.

One checkout = one Order (one payment) split into one SellerOrder per seller.
The stock is taken off the shelf at checkout and held for ORDER_HOLD_MINUTES.
If the order isn't paid in time, release_hold() puts the stock back.
"""

from collections import defaultdict
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from cart.models import CartItem
from catalog.models import Product
from orders.models import Order, OrderItem, SellerOrder


class CheckoutError(Exception):
    """Checkout can't go ahead. `message` is safe to show to the buyer."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class SoldOutError(CheckoutError):
    def __init__(self, items: list[dict]):
        super().__init__("Some items sold out while you were shopping.")
        self.items = items  # [{"product_id", "name"}], so the bag can show and remove them


def hold_expires_at(order: Order):
    return order.created_at + timedelta(minutes=settings.ORDER_HOLD_MINUTES)


@transaction.atomic  # everything below is saved together, or not at all
def create_order_from_cart(user, address) -> Order:
    # 0. The buyer closed the payment window and pressed Pay again: let go of the
    #    earlier unpaid attempt first, so it doesn't keep their own stock locked up.
    for earlier in Order.objects.filter(buyer=user, payment_status=Order.PaymentStatus.PENDING):
        release_hold(earlier)

    # 1. Only THIS buyer's bag.
    cart_items = list(CartItem.objects.filter(user=user).order_by("created_at"))
    if not cart_items:
        raise CheckoutError("Your bag is empty.")

    # 2. Lock the product rows until this transaction ends. A second buyer checking
    #    out the same cake waits here, then reads the stock we left behind.
    #    order_by("id") locks rows in the same order every time, so two checkouts
    #    can never each hold one lock and wait for the other's (a deadlock).
    product_ids = [item.product_id for item in cart_items]
    locked = Product.objects.select_for_update(of=("self",)).select_related("seller").filter(id__in=product_ids)
    products = {product.id: product for product in locked.order_by("id")}

    # 3. Group the bag by seller: each seller gets their own part of the order.
    by_seller = defaultdict(list)
    for item in cart_items:
        by_seller[products[item.product_id].seller].append(item)

    paused = [seller.name for seller in by_seller if not seller.is_active]
    if paused:
        raise CheckoutError(f"{', '.join(paused)} isn't taking orders right now. Remove their items to continue.")
    if any(seller.owner_id == user.id for seller in by_seller):
        raise CheckoutError("You can't buy from your own shop.")

    # 4. Every item must still be for sale, with enough stock.
    sold_out = [
        {"product_id": item.product_id, "name": products[item.product_id].name}
        for item in cart_items
        if not products[item.product_id].is_active or products[item.product_id].stock < item.qty
    ]
    if sold_out:
        raise SoldOutError(sold_out)

    # 5. Money, from database prices only. Integer paise: 45000 = ₹450.
    def line_total(item):
        return products[item.product_id].price_paise * item.qty

    items_total = sum(line_total(item) for item in cart_items)
    delivery_total = sum(seller.delivery_fee_paise for seller in by_seller)  # one fee per seller

    order = Order.objects.create(
        buyer=user,
        items_total=items_total,
        delivery_total=delivery_total,
        grand_total=items_total + delivery_total,
        ship_to=address.snapshot(),  # frozen copy of the address
        stock_held=True,
    )
    for seller, items in by_seller.items():
        seller_order = SellerOrder.objects.create(
            order=order,
            seller=seller,
            subtotal=sum(line_total(item) for item in items),
            delivery_fee=seller.delivery_fee_paise,
        )
        OrderItem.objects.bulk_create(
            OrderItem(
                seller_order=seller_order,
                product=products[item.product_id],
                name=products[item.product_id].name,  # snapshot: what they bought...
                unit_price=products[item.product_id].price_paise,  # ...and the price they paid
                qty=item.qty,
                note=item.note,
            )
            for item in items
        )

    # 6. Hold the stock. F() makes Postgres do "stock = stock - qty" itself.
    #    The rows are still locked, so nobody can sneak in between the check and this.
    for item in cart_items:
        Product.objects.filter(pk=item.product_id).update(stock=F("stock") - item.qty)

    # The cart is NOT cleared here: only once the payment is confirmed.
    return order


@transaction.atomic
def release_hold(order: Order) -> bool:
    """
    An unpaid order gives up: pending -> failed, and its held stock goes back
    on the shelf. Returns True if it did that, False if there was nothing to do.
    """
    # Lock the order row, so a payment confirmation and a release can't both run at once.
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.payment_status != Order.PaymentStatus.PENDING:
        return False  # already paid or already failed: leave it alone

    if order.stock_held:  # orders from before Stage 2 never held stock, so they give nothing back
        for item in OrderItem.objects.filter(seller_order__order=order, product__isnull=False):
            Product.objects.filter(pk=item.product_id).update(stock=F("stock") + item.qty)

    order.payment_status = Order.PaymentStatus.FAILED
    order.stock_held = False
    order.save(update_fields=["payment_status", "stock_held"])
    return True


def expire_unpaid_orders() -> int:
    """Release every order still unpaid after the hold time. Returns how many."""
    cutoff = timezone.now() - timedelta(minutes=settings.ORDER_HOLD_MINUTES)
    expired = Order.objects.filter(payment_status=Order.PaymentStatus.PENDING, created_at__lt=cutoff)
    return sum(release_hold(order) for order in expired)
