"""
Browsing: search, filters and sort for buyers. Every number (rating, trending,
counts) is computed from the database. Bad or unknown values in the URL are
ignored instead of causing errors, so a typed or old link still shows something.
"""

from datetime import timedelta

from django.db.models import Avg, Case, Count, F, IntegerField, OuterRef, Q, QuerySet, Subquery, Sum, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone

from catalog.models import Product, Seller

TRENDING_DAYS = 30
MAX_LIMIT = 60
SORTS = {"relevance", "newest", "price_asc", "price_desc", "rating", "trending"}


def _int(value, default=None):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return number if number >= 0 else default


def public_products() -> QuerySet:
    """Products buyers may see: active, from a store that isn't paused."""
    return (
        Product.objects.filter(is_active=True, seller__is_active=True)
        .select_related("category", "seller")
        .prefetch_related("images")
    )


def recent_sales():
    """For each product: how many were bought (paid, not cancelled) in the last TRENDING_DAYS days."""
    from orders.models import OrderItem  # orders already imports catalog, so import here

    since = timezone.now() - timedelta(days=TRENDING_DAYS)
    rows = (
        OrderItem.objects.filter(
            product=OuterRef("pk"), seller_order__order__payment_status="paid", seller_order__order__paid_at__gte=since
        )
        .exclude(seller_order__status="cancelled")
        .values("product")
        .annotate(total=Sum("qty"))
        .values("total")
    )
    return Coalesce(Subquery(rows), 0)


def search_products(params) -> QuerySet:
    products = public_products()

    # Search: every word must appear in the name, description, shop name or category.
    q = (params.get("q") or "").strip()
    for word in q.split()[:8]:
        products = products.filter(
            Q(name__icontains=word)
            | Q(description__icontains=word)
            | Q(seller__name__icontains=word)
            | Q(category__name__icontains=word)
        )

    if category := params.get("category"):
        products = products.filter(category__slug=category)
    if seller := params.get("seller"):
        products = products.filter(seller__slug=seller)
    if params.get("in_stock") in ("1", "true"):
        products = products.filter(stock__gt=0)
    if (low := _int(params.get("min_price"))) is not None:
        products = products.filter(price_paise__gte=low)
    if (high := _int(params.get("max_price"))) is not None:
        products = products.filter(price_paise__lte=high)
    if ids := params.get("ids"):  # the wishlist asks for its products by id
        wanted = [_int(i) for i in ids.split(",")[:MAX_LIMIT]]
        products = products.filter(id__in=[i for i in wanted if i is not None])

    sort = params.get("sort")
    if sort not in SORTS:
        sort = "relevance" if q else "newest"

    if sort == "relevance" and q:
        # Products whose NAME matches the search come first, then the rest; newest first within each.
        name_hit = Case(
            When(name__icontains=q.split()[0], then=Value(1)), default=Value(0), output_field=IntegerField()
        )
        products = products.annotate(name_hit=name_hit).order_by("-name_hit", "-created_at")
    elif sort == "price_asc":
        products = products.order_by("price_paise", "-created_at")
    elif sort == "price_desc":
        products = products.order_by("-price_paise", "-created_at")
    elif sort == "rating":
        products = products.annotate(rating=Avg("seller__reviews__rating")).order_by(
            F("rating").desc(nulls_last=True),
            "-created_at",  # no reviews yet -> at the end, never a made-up 0
        )
    elif sort == "trending":
        # Only products that really sold recently. No orders -> empty, so the home page hides the section.
        products = products.annotate(sold=recent_sales()).filter(sold__gt=0).order_by("-sold", "-created_at")
    else:
        products = products.order_by("-created_at")

    limit = min(_int(params.get("limit"), MAX_LIMIT) or MAX_LIMIT, MAX_LIMIT)
    return products[:limit]


def public_stores() -> QuerySet:
    """Open stores with their live product count and real rating (None when there are no reviews)."""
    return (
        Seller.objects.filter(is_active=True)
        .select_related("main_category")
        .annotate(
            product_count=Count("products", filter=Q(products__is_active=True), distinct=True),
            rating=Avg("reviews__rating"),
            review_count=Count("reviews", distinct=True),
        )
    )


def search_stores(params) -> QuerySet:
    stores = public_stores()
    for word in (params.get("q") or "").split()[:8]:
        stores = stores.filter(Q(name__icontains=word) | Q(area__icontains=word) | Q(bio__icontains=word))
    limit = min(_int(params.get("limit"), MAX_LIMIT) or MAX_LIMIT, MAX_LIMIT)
    return stores.order_by("-created_at")[:limit]
