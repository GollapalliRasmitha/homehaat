from django.db import transaction
from django.db.models import OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from rest_framework import generics, status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response

from accounts.models import User
from catalog.images import ImageError, clean_image
from catalog.models import Category, Product, ProductImage, Seller
from catalog.serializers import (
    CategorySerializer,
    ProductImageSerializer,
    ProductSerializer,
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
    serializer_class = CategorySerializer
    queryset = Category.objects.all()
    pagination_class = None


def public_products():
    """Products buyers may see: active, from a store that isn't paused."""
    return (
        Product.objects.filter(is_active=True, seller__is_active=True)
        .select_related("category", "seller")
        .prefetch_related("images")
    )


class ProductList(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductSerializer
    pagination_class = None
    filterset_fields = {"category__slug": ["exact"], "seller__slug": ["exact"]}

    def get_queryset(self):
        return public_products().order_by("-created_at")


class ProductDetail(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductSerializer

    def get_queryset(self):
        return public_products()


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
    return user.seller.products.select_related("category").prefetch_related("images").annotate(sold=sold)


class MyProductList(generics.ListCreateAPIView):
    permission_classes = [IsSeller]
    serializer_class = SellerProductSerializer
    pagination_class = None

    def get_queryset(self):
        return my_products(self.request.user)

    def perform_create(self, serializer):
        # The seller always comes from the signed-in user, never from the request body.
        serializer.save(seller=self.request.user.seller)


class MyProductDetail(generics.RetrieveUpdateAPIView):
    permission_classes = [IsSeller]
    serializer_class = SellerProductSerializer

    def get_queryset(self):
        return my_products(self.request.user)  # another seller's product id gives 404


def _my_product(request, pk) -> Product:
    return get_object_or_404(Product, pk=pk, seller=request.user.seller)  # someone else's product -> 404


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
