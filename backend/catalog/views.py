from django.db import transaction
from django.db.models import Count, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from rest_framework import generics, status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response

from accounts.models import User
from cart.models import CartItem
from catalog.browse import (
    all_stores,
    search_page,
    search_products,
    search_stores,
    shop_products,
)
from catalog.images import ImageError, clean_image
from catalog.models import Category, Product, ProductImage, Seller
from catalog.serializers import (
    CategoryWithCountSerializer,
    ProductImageSerializer,
    ProductSerializer,
    PublicStoreSerializer,
    SellerProductSerializer,
    StoreSerializer,
)

MAX_PHOTOS = 5


class IsSeller(BasePermission):
    """The signed-in user owns a store."""

    message = "Open your shop first."

    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, "seller")


class CategoryList(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CategoryWithCountSerializer
    pagination_class = None

    def get_queryset(self):
        live = Q(products__is_active=True, products__is_custom=False, products__seller__is_active=True)
        # order_by is needed: Django drops Meta.ordering in GROUP BY (counting) queries
        return Category.objects.annotate(product_count=Count("products", filter=live)).order_by("position")


class ProductList(generics.ListAPIView):
    """Search and browse. ?q= &category= &seller= &min_price= &max_price= (paise) &in_stock=1 &sort= &ids= &limit="""

    permission_classes = [AllowAny]
    serializer_class = ProductSerializer
    pagination_class = None
    filter_backends = []  # our own filtering in browse.search_products

    def get_queryset(self):
        return search_products(self.request.query_params)


@api_view(["GET"])
@permission_classes([AllowAny])
def search(request):
    """The Explore page: same filters as /products/, plus ?page=, the real total and "Did you mean…?"."""
    page = search_page(request.query_params)
    page["results"] = ProductSerializer(page["results"], many=True, context={"request": request}).data
    return Response(page)


class StoreList(generics.ListAPIView):
    """Makers: open shops, newest first. ?q= searches name, area and about."""

    permission_classes = [AllowAny]
    serializer_class = PublicStoreSerializer
    pagination_class = None
    filter_backends = []

    def get_queryset(self):
        return search_stores(self.request.query_params)


class StoreDetail(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicStoreSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return all_stores()  # a paused shop's page still opens ("taking_orders": false)


@api_view(["GET"])
@permission_classes([AllowAny])
def store_reviews(request, slug):
    store = get_object_or_404(all_stores(), slug=slug)
    return Response(
        [
            {
                "id": r.id,
                "rating": r.rating,
                "comment": r.comment,
                # first name only: buyers' full names and emails stay private
                "buyer_name": r.buyer.name.split(" ")[0] if r.buyer.name else "A buyer",
                "created_at": r.created_at,
            }
            for r in store.reviews.select_related("buyer")
        ]
    )


class ProductDetail(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductSerializer

    def get_queryset(self):
        return shop_products()  # a paused shop's products keep their page; Add to bag is refused


def unique_slug(name: str) -> str:
    base = slugify(name)[:50] or "shop"
    slug, n = base, 2
    while Seller.objects.filter(slug=slug).exists():
        slug, n = f"{base}-{n}", n + 1
    return slug


@api_view(["GET", "POST", "PATCH"])
def my_store(request):
    store = getattr(request.user, "seller", None)

    if request.method == "POST":  # Open your shop
        if store:
            return Response({"detail": "You already have a shop."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = StoreSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # The seller may choose their shop link; if not, we make one from the shop name.
        slug = serializer.validated_data.pop("slug", None) or unique_slug(serializer.validated_data["name"])
        with transaction.atomic():
            store = serializer.save(owner=request.user, slug=slug, is_active=True)
            # The server decides the role: opening a shop makes you a seller.
            if request.user.role == User.Role.BUYER:
                request.user.role = User.Role.SELLER
                request.user.save(update_fields=["role"])
        return Response(StoreSerializer(store).data, status=status.HTTP_201_CREATED)

    if store is None:
        return Response({"detail": "Open your shop first."}, status=status.HTTP_404_NOT_FOUND)
    if request.method == "PATCH":
        serializer = StoreSerializer(store, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    return Response(StoreSerializer(store).data)


@api_view(["POST", "DELETE"])
@permission_classes([IsSeller])
@parser_classes([MultiPartParser])
def my_store_cover(request):
    """Upload (POST, field "image") or remove (DELETE) the shop's cover photo."""
    store = request.user.seller
    if store.cover:
        store.cover.delete(save=False)  # remove the old file from disk
    if request.method == "DELETE":
        store.save(update_fields=["cover"])
        return Response(StoreSerializer(store).data)
    try:
        store.cover = clean_image(request.FILES.get("image"))
    except ImageError as exc:
        return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
    store.save(update_fields=["cover"])
    return Response(StoreSerializer(store).data)


def my_products(user):
    """Only your own products, with how many you've sold (paid and not cancelled)."""
    from orders.models import OrderItem  # here, not at the top: orders already imports catalog

    sold_rows = (
        OrderItem.objects.filter(product=OuterRef("pk"), seller_order__order__payment_status="paid")
        .exclude(seller_order__status="cancelled")
        .values("product")
        .annotate(total=Sum("qty"))
        .values("total")
    )
    sold = Coalesce(Subquery(sold_rows), 0)  # 0 when nothing has sold yet
    # custom-request products aren't the seller's catalogue: they show up as orders instead;
    # archived ("deleted" but kept for order history) products are gone from the seller's list
    return (
        user.seller.products.filter(is_custom=False, is_archived=False)
        .select_related("category")
        .prefetch_related("images")
        .annotate(sold=sold, past_orders=past_orders_count())
    )


def past_orders_count():
    """How many orders (paid, or being paid right now) include this product. Failed attempts don't count."""
    from orders.models import OrderItem

    rows = (
        OrderItem.objects.filter(product=OuterRef("pk"), seller_order__order__payment_status__in=["paid", "pending"])
        .values("product")
        .annotate(n=Count("seller_order__order", distinct=True))
        .values("n")
    )
    return Coalesce(Subquery(rows), 0)


class MyProductList(generics.ListCreateAPIView):
    permission_classes = [IsSeller]
    serializer_class = SellerProductSerializer
    pagination_class = None

    def get_queryset(self):
        return my_products(self.request.user)

    def perform_create(self, serializer):
        # The seller always comes from the signed-in user, never from the request body.
        serializer.save(seller=self.request.user.seller)


class MyProductDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsSeller]
    serializer_class = SellerProductSerializer

    def get_queryset(self):
        return my_products(self.request.user)  # another seller's (or an archived) product id gives 404

    def destroy(self, request, *args, **kwargs):
        """
        Delete. Never ordered -> removed completely (with its photos). In past orders -> archived: gone from the
        shop, search and this list, but the orders keep pointing to it (they also keep their own snapshot).
        """
        product = self.get_object()
        past = product.past_orders
        if past:
            product.is_archived, product.is_active = True, False
            product.save(update_fields=["is_archived", "is_active"])
            # It can never be bought again, so take it out of everyone's bag (orders keep their own snapshot).
            CartItem.objects.filter(product=product).delete()
            return Response({"result": "archived", "past_orders": past})
        files = [img.image for img in product.images.all()]
        product.delete()
        for f in files:
            f.delete(save=False)  # the photo files too: nothing else uses them
        return Response({"result": "deleted", "past_orders": 0})


def _my_product(request, pk) -> Product:
    # not yours, a custom-request item, or archived -> 404
    return get_object_or_404(Product, pk=pk, seller=request.user.seller, is_custom=False, is_archived=False)


@api_view(["POST"])
@permission_classes([IsSeller])
@parser_classes([MultiPartParser])
def product_images(request, pk):
    """Add one photo (field "image"). It goes to the end; the first photo is the one buyers see first."""
    product = _my_product(request, pk)
    count = product.images.count()
    if count >= MAX_PHOTOS:
        return Response({"detail": f"A product can have up to {MAX_PHOTOS} photos."}, status=400)
    try:
        cleaned = clean_image(request.FILES.get("image"))
    except ImageError as exc:
        return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
    image = ProductImage.objects.create(product=product, image=cleaned, position=count)
    return Response(ProductImageSerializer(image).data, status=status.HTTP_201_CREATED)


@api_view(["DELETE"])
@permission_classes([IsSeller])
def product_image_delete(request, pk, image_id):
    image = get_object_or_404(ProductImage, pk=image_id, product=_my_product(request, pk))
    image.image.delete(save=False)  # the file on disk too
    image.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@permission_classes([IsSeller])
def product_images_order(request, pk):
    """{"ids": [3, 1, 2]}: the new order of this product's photos."""
    product = _my_product(request, pk)
    ids = request.data.get("ids")
    mine = {img.id: img for img in product.images.all()}
    if not isinstance(ids, list) or sorted(ids) != sorted(mine):
        return Response({"detail": "Send every photo id of this product once."}, status=400)
    with transaction.atomic():
        for position, image_id in enumerate(ids):
            mine[image_id].position = position
            mine[image_id].save(update_fields=["position"])
    return Response(ProductImageSerializer(product.images.order_by("position"), many=True).data)
