"""
Tiny factories for tests only. Nothing here ever runs in the real site:
the test runner creates a separate, throwaway database.
"""

from itertools import count

from accounts.models import Address, User
from cart.models import CartItem
from catalog.models import Category, Product, Seller

_n = count(1)


def make_user(email=None, password="test-pass-123", **extra) -> User:
    return User.objects.create_user(email or f"user{next(_n)}@example.com", password, **extra)


def make_category(slug="cakes") -> Category:
    category, _ = Category.objects.get_or_create(
        slug=slug, defaults={"name": slug.title(), "tint": "blush", "art": "cake", "photo_id": "x"}
    )
    return category


def make_seller(owner=None, delivery_fee_paise=4000, **extra) -> Seller:
    owner = owner or make_user(role=User.Role.SELLER)
    i = next(_n)
    return Seller.objects.create(
        owner=owner, slug=f"shop-{i}", name=f"Shop {i}", delivery_fee_paise=delivery_fee_paise, **extra
    )


def make_product(seller=None, price_paise=45000, stock=5, **extra) -> Product:
    return Product.objects.create(
        seller=seller or make_seller(),
        category=make_category(),
        name=extra.pop("name", f"Product {next(_n)}"),
        price_paise=price_paise,
        stock=stock,
        **extra,
    )


def make_address(user, **extra) -> Address:
    data = dict(name="Asha Rao", phone="9876543210", line1="12 MG Road", city="Bengaluru", pincode="560001")
    data.update(extra)
    return Address.objects.create(user=user, **data)


def add_to_cart(user, product, qty=1, note="") -> CartItem:
    return CartItem.objects.create(user=user, product=product, qty=qty, note=note)
