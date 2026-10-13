"""
[KEY LOGIC] Custom requests: who may do what, and turning an accepted quote into a bag item.

    open   --seller "quote"-->   quoted   --buyer "accept"-->  accepted  (one-off product in the buyer's bag)
    open   --seller "decline"--> declined
    quoted --buyer "decline"-->  declined

Everything happens on the server inside a locked transaction. The price in the bag is
always the quote saved here, never a number sent by the browser.
"""

from django.db import transaction
from django.utils import timezone

from cart.models import CartItem
from catalog.models import Category, Product
from custom_requests.models import CustomRequest

R = CustomRequest.Status
SELLER, BUYER = "seller", "buyer"

# (current status, action) -> (who may do it, the new status). Anything not in this table is refused.
RULES = {
    (R.OPEN, "quote"): (SELLER, R.QUOTED),
    (R.OPEN, "decline"): (SELLER, R.DECLINED),
    (R.QUOTED, "accept"): (BUYER, R.ACCEPTED),
    (R.QUOTED, "decline"): (BUYER, R.DECLINED),
}

MIN_QUOTE_PAISE = 100  # ₹1, the same minimum as any product price


class RequestError(Exception):
    """The action isn't allowed. `message` is safe to show."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotYourRequestError(RequestError):
    def __init__(self):
        super().__init__("Request not found.")  # same answer as a missing request: don't reveal it exists


@transaction.atomic
def apply_action(custom_request, user, action: str, quote_paise=None, note: str = "") -> CustomRequest:
    # Lock the row: a double tap, or the buyer and seller acting at the same moment, run one after the other.
    req = CustomRequest.objects.select_for_update().select_related("seller").get(pk=custom_request.pk)

    # 1. Who is this? Only the request's buyer or the shop's owner may touch it.
    if user.id == req.buyer_id:
        side = BUYER
    elif user.id == req.seller.owner_id:
        side = SELLER
    else:
        raise NotYourRequestError()

    # 2. Is this move in the table, and is it this side's move?
    rule = RULES.get((req.status, action))
    if rule is None:
        raise RequestError(f"A request that is “{R(req.status).label.lower()}” can't be {_past(action)} now.")
    who, new_status = rule
    if side != who:
        raise RequestError(_wrong_side(action))

    # 3. Do it.
    if action == "quote":
        if not isinstance(quote_paise, int) or quote_paise < MIN_QUOTE_PAISE:
            raise RequestError("Enter a price of ₹1 or more.")
        req.quote_paise = quote_paise
        req.seller_note = (note or "")[:300]
    elif action == "accept":
        if not req.seller.is_active:
            raise RequestError(f"{req.seller.name} isn't taking orders right now.")
        req.product = _make_one_off_product(req)
        CartItem.objects.create(user=req.buyer, product=req.product, qty=1, custom_request=req)

    req.status = new_status
    req.responded_at = timezone.now()
    req.save()
    return req


def _make_one_off_product(req: CustomRequest) -> Product:
    """A private product for this one request: price = the quote, stock = 1, never listed anywhere."""
    category = req.seller.main_category or Category.objects.order_by("position").first()
    if category is None:  # only possible if seed_categories never ran
        raise RequestError("The shop isn't set up yet. Please try again later.")
    words = req.description.split()
    short = " ".join(words[:8]) + ("…" if len(words) > 8 else "")
    return Product.objects.create(
        seller=req.seller,
        category=category,
        name=f"Custom: {short}"[:120],
        description=req.description,
        price_paise=req.quote_paise,  # the saved quote, not anything from the request body
        stock=1,
        is_custom=True,
    )


@transaction.atomic
def add_quote_to_bag(custom_request, user) -> CartItem:
    """Put an accepted request back in the bag (e.g. after removing it). Never makes a second line."""
    # of=("self",): lock just the request row (Postgres can't lock the optional product side of the join)
    req = CustomRequest.objects.select_for_update(of=("self",)).select_related("product").get(pk=custom_request.pk)
    if req.buyer_id != user.id:
        raise NotYourRequestError()
    if req.status != R.ACCEPTED or req.product is None:
        raise RequestError("Only an accepted quote can go in your bag.")
    if req.product.stock < 1:
        raise RequestError("You've already ordered this one.")
    item, _ = CartItem.objects.get_or_create(user=user, product=req.product, defaults={"qty": 1, "custom_request": req})
    return item


def _past(action: str) -> str:
    return {"quote": "quoted", "accept": "accepted", "decline": "declined"}.get(action, "changed")


def _wrong_side(action: str) -> str:
    return {
        "quote": "Only the maker can send a quote.",
        "accept": "Only the buyer can accept a quote.",
        "decline": "It's not your turn to answer this request.",
    }.get(action, "You can't do that.")
