"""
[KEY LOGIC] Cancelling a maker's part of an order, by the buyer or the seller, and refunding exactly that part.

Who may do what (status of that maker's part -> what happens):

    buyer   New              -> cancelled at once (custom items too)
    buyer   Preparing        -> only a REQUEST; the seller accepts (cancelled) or declines (stays Preparing)
                                (custom items can't be requested: the maker has already started making it)
    buyer   Out for delivery / Delivered -> refused
    seller  New or Preparing -> cancelled (through advance_status)

Every cancellation goes through _cancel(): the status and the stock change and the Refund row is created in ONE
transaction, and the refund is sent to Razorpay only after that transaction is saved (on_commit).
"""

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from catalog.models import Product
from orders.models import Order, Refund, SellerOrder
from orders.status import NotYourOrderError, StatusError

S = SellerOrder.Status


def _locked(seller_order) -> SellerOrder:
    return SellerOrder.objects.select_for_update().select_related("order", "seller").get(pk=seller_order.pk)


def has_custom_items(part: SellerOrder) -> bool:
    return part.items.filter(product__is_custom=True).exists()


def _cancel(part: SellerOrder, by: str, restock: bool = True) -> SellerOrder:
    """Cancel a LOCKED, paid part: status, stock back, and one Refund for its items + delivery fee."""
    part.status = S.CANCELLED
    part.cancelled_at = timezone.now()
    part.cancelled_by = by
    part.refund_needed = True
    part.cancel_requested_at = None
    part.save(update_fields=["status", "cancelled_at", "cancelled_by", "refund_needed", "cancel_requested_at"])
    # Nothing will be made, so the items go back on the shelf. F() = done by the database.
    for item in part.items.filter(product__isnull=False) if restock else []:
        Product.objects.filter(pk=item.product_id).update(stock=F("stock") + item.qty)
    # get_or_create + the one-to-one column: there can only ever be one refund for this part.
    refund, _ = Refund.objects.get_or_create(seller_order=part, defaults={"amount": part.subtotal + part.delivery_fee})
    from payments.refunds import send_refund  # payments imports orders, so import here

    transaction.on_commit(lambda: send_refund(refund.pk))  # call Razorpay only once the cancel is saved
    return part


def _as_buyer(seller_order, user) -> SellerOrder:
    part = _locked(seller_order)
    if part.order.buyer_id != user.id:
        raise NotYourOrderError()  # 404: other buyers and sellers don't even learn it exists
    if part.order.payment_status != Order.PaymentStatus.PAID:
        raise StatusError("This order hasn't been paid, so there's nothing to cancel.")
    return part


@transaction.atomic
def buyer_cancel(seller_order, user) -> SellerOrder:
    part = _as_buyer(seller_order, user)
    if part.status == S.CANCELLED:
        return part  # a double click or a retry: already done, and still only one refund
    if part.status == S.PREPARING:
        raise StatusError("The maker has started preparing it. You can ask them to cancel instead.")
    if part.status != S.NEW:
        raise StatusError("It's already on its way, so it can't be cancelled now.")
    return _cancel(part, by="buyer")


@transaction.atomic
def request_cancellation(seller_order, user) -> SellerOrder:
    part = _as_buyer(seller_order, user)
    if part.status != S.PREPARING:
        raise StatusError("You can ask the maker to cancel only while they're preparing it.")
    if has_custom_items(part):
        raise StatusError("Custom items can't be cancelled once the maker has started making them.")
    if part.cancel_declined_at:
        raise StatusError("The maker has already said they can't cancel this one.")
    if not part.cancel_requested_at:
        part.cancel_requested_at = timezone.now()
        part.save(update_fields=["cancel_requested_at"])
    return part


@transaction.atomic
def answer_cancellation(seller_order, user, accept: bool) -> SellerOrder:
    part = _locked(seller_order)
    if part.seller.owner_id != user.id:
        raise NotYourOrderError()
    if part.status == S.CANCELLED:
        return part  # already accepted (double click)
    if not part.cancel_requested_at or part.status != S.PREPARING:
        raise StatusError("There's no cancellation request for this order.")
    if accept:
        return _cancel(part, by="buyer")  # the buyer asked; the refund is the same
    part.cancel_requested_at = None
    part.cancel_declined_at = timezone.now()
    part.save(update_fields=["cancel_requested_at", "cancel_declined_at"])
    return part


def seller_cancel(part: SellerOrder) -> SellerOrder:
    """Called by advance_status, which has already locked the row and checked ownership and the allowed move."""
    return _cancel(part, by="seller")


def system_cancel(part: SellerOrder) -> SellerOrder:
    """A late payment whose items are gone (payments.webhook._take_stock_again). Inside its transaction."""
    # restock=False: this part's stock was never taken (that's why it's being cancelled).
    return _cancel(_locked(part), by="system", restock=False)
