"""
[KEY LOGIC] Turning a buyer's cart into an order.

Stage 1: the cart holds products from ONE seller, so we create
one Order + one SellerOrder + its OrderItems. Stage 2 splits by seller.
"""

from django.db import transaction

from cart.models import CartItem
from catalog.models import Product
from orders.models import Order, OrderItem, SellerOrder


class CheckoutError(Exception):
    """Checkout can't go ahead. `message` is safe to show to the buyer."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class SoldOutError(CheckoutError):
    def __init__(self, items: list[str]):
        super().__init__("Some items sold out while you were shopping.")
        self.items = items  # product names, so the bag can show which ones


@transaction.atomic  # everything below is saved together, or not at all
def create_order_from_cart(user, address) -> Order:
    cart_items = list(CartItem.objects.filter(user=user))  # only THIS buyer's cart
    if not cart_items:
        raise CheckoutError("Your bag is empty.")

    # Lock these product rows until the transaction ends, so nobody else can
    # change their stock while we check it. Prices are read here, from the
    # database, never from the request.
    product_ids = [item.product_id for item in cart_items]
    # of=("self",) locks only the product rows, not the joined seller row.
    products = Product.objects.select_for_update(of=("self",)).select_related("seller").filter(id__in=product_ids)
    products = {product.id: product for product in products}

    sellers = {product.seller for product in products.values()}
    if len(sellers) != 1:
        raise CheckoutError("For now, one order can only have products from one maker.")
    seller = sellers.pop()
    if not seller.is_active:
        raise CheckoutError(f"{seller.name} isn't taking orders right now.")

    sold_out = [
        products[item.product_id].name
        for item in cart_items
        if not products[item.product_id].is_active or products[item.product_id].stock < item.qty
    ]
    if sold_out:
        raise SoldOutError(sold_out)

    # All money is integer paise: 45000 = ₹450.
    items_total = sum(products[item.product_id].price_paise * item.qty for item in cart_items)
    delivery_fee = seller.delivery_fee_paise

    order = Order.objects.create(
        buyer=user,
        items_total=items_total,
        delivery_total=delivery_fee,
        grand_total=items_total + delivery_fee,
        ship_to=address.snapshot(),  # frozen copy of the address
    )
    seller_order = SellerOrder.objects.create(
        order=order, seller=seller, subtotal=items_total, delivery_fee=delivery_fee
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
        for item in cart_items
    )
    # Stock and cart are NOT changed here: that happens only once payment is confirmed.
    return order
