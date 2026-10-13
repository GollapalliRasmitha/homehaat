"""
Browsing: search, filters and sort for buyers. Every number (rating, trending,
counts) is computed from the database. Bad or unknown values in the URL are
ignored instead of causing errors, so a typed or old link still shows something.
"""

import difflib
import re
from datetime import timedelta

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import Avg, Case, Count, F, IntegerField, OuterRef, Q, QuerySet, Subquery, Sum, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone

from catalog.models import Product, Seller

TRENDING_DAYS = 30
MAX_LIMIT = 60
PAGE_SIZE = 24  # the Explore page shows this many per page
MAX_WORDS = 8
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
        # is_custom=False: one-off custom-request products are never listed (they live in one buyer's bag)
        Product.objects.filter(is_active=True, is_custom=False, seller__is_active=True)
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


# Postgres full-text search. "english" turns words into their stem, so "cakes" and "cake" match each other.
# Weights: the product name counts most (A), then the shop and category (B), then description and area (C).
DOCUMENT = (
    SearchVector("name", weight="A", config="english")
    + SearchVector("category__name", "seller__name", weight="B", config="english")
    + SearchVector("description", "seller__area", weight="C", config="english")
)
TEXT_FIELDS = ("name", "description", "seller__name", "seller__area", "category__name")


def _words(q) -> list[str]:
    return (q or "").split()[:MAX_WORDS]


def _word_matches(word) -> Q:
    """A word matches if it is part of any text field ("choco" in "chocolate") or has the same stem ("cakes")."""
    q = Q(document=SearchQuery(word, config="english"))
    for field in TEXT_FIELDS:
        q |= Q(**{f"{field}__icontains": word})
    return q


def find_products(params) -> QuerySet:
    """Every filter and the sort, without a limit. Used by the products list and by search pages."""
    products = public_products()

    # Search: EVERY word must match (so "mango jayanagar" means mango pickle from Jayanagar).
    words = _words(params.get("q"))
    if words:
        products = products.annotate(document=DOCUMENT)
        for word in words:
            products = products.filter(_word_matches(word))

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
        sort = "relevance" if words else "newest"

    if sort == "relevance" and words:
        # 1) how many search words are in the NAME, 2) full-text rank (name > shop/category > description),
        # 3) newest. So "chocolate cake" puts the Chocolate cake above a box that mentions one.
        name_hits = sum(
            (
                Case(When(name__icontains=w, then=Value(1)), default=Value(0), output_field=IntegerField())
                for w in words
            ),
            Value(0),
        )
        any_word = SearchQuery(words[0], config="english")
        for w in words[1:]:
            any_word |= SearchQuery(w, config="english")
        products = products.annotate(name_hits=name_hits, rank=SearchRank(DOCUMENT, any_word)).order_by(
            "-name_hits", "-rank", "-created_at", "-id"
        )
    elif sort == "price_asc":
        products = products.order_by("price_paise", "-created_at", "-id")
    elif sort == "price_desc":
        products = products.order_by("-price_paise", "-created_at", "-id")
    elif sort == "rating":
        products = products.annotate(rating=Avg("seller__reviews__rating")).order_by(
            F("rating").desc(nulls_last=True),
            "-created_at",  # no reviews yet -> at the end, never a made-up 0
            "-id",
        )
    elif sort == "trending":
        # Only products that really sold recently. No orders -> empty, so the home page hides the section.
        products = products.annotate(sold=recent_sales()).filter(sold__gt=0).order_by("-sold", "-created_at", "-id")
    else:
        products = products.order_by("-created_at", "-id")  # id breaks ties, so pages never overlap
    return products


def search_products(params) -> QuerySet:
    limit = min(_int(params.get("limit"), MAX_LIMIT) or MAX_LIMIT, MAX_LIMIT)
    return find_products(params)[:limit]


def search_page(params) -> dict:
    """One page of results with the real total, plus a "Did you mean…?" when nothing matched."""
    products = find_products(params)
    count = products.count()
    pages = max(1, -(-count // PAGE_SIZE))  # round up
    page = min(max(_int(params.get("page"), 1) or 1, 1), pages)  # bad or too big -> a page that exists
    start = (page - 1) * PAGE_SIZE
    suggestion = None
    if count == 0 and params.get("q"):
        suggestion = suggest_query(params.get("q"))
        if suggestion and not find_products({**_as_dict(params), "q": suggestion}).exists():
            suggestion = None  # only suggest something that really has results (with the same filters)
    return {
        "count": count,
        "page": page,
        "pages": pages,
        "page_size": PAGE_SIZE,
        "results": products[start : start + PAGE_SIZE],
        "suggestion": suggestion,
    }


def _as_dict(params) -> dict:
    return {k: params.get(k) for k in params.keys()}


def suggest_query(q) -> str | None:
    """
    "chocolte cak" -> "chocolate cake". Each word that isn't a real word from the listings is swapped for the
    closest one (Python's difflib, similarity 75%+). Words come from live product names, categories and shops.
    """
    vocabulary = set()
    texts = list(public_products().values_list("name", "category__name", "seller__name")[:3000])
    for row in texts:
        for text in row:
            vocabulary.update(w for w in re.findall(r"[a-z]+", (text or "").lower()) if len(w) >= 3)
    if not vocabulary:
        return None
    fixed = []
    for word in _words(q.lower()):
        if word in vocabulary:
            fixed.append(word)
            continue
        close = difflib.get_close_matches(word, vocabulary, n=1, cutoff=0.75)
        fixed.append(close[0] if close else word)
    suggestion = " ".join(fixed)
    return suggestion if suggestion != " ".join(_words(q.lower())) else None


def public_stores() -> QuerySet:
    """Open stores with their live product count and real rating (None when there are no reviews)."""
    return (
        Seller.objects.filter(is_active=True)
        .select_related("main_category")
        .annotate(
            product_count=Count(
                "products", filter=Q(products__is_active=True, products__is_custom=False), distinct=True
            ),
            rating=Avg("reviews__rating"),
            review_count=Count("reviews", distinct=True),
        )
    )


def search_stores(params) -> QuerySet:
    stores = public_stores()
    for word in _words(params.get("q")):
        stores = stores.filter(Q(name__icontains=word) | Q(area__icontains=word) | Q(bio__icontains=word))
    limit = min(_int(params.get("limit"), MAX_LIMIT) or MAX_LIMIT, MAX_LIMIT)
    return stores.order_by("-created_at")[:limit]
