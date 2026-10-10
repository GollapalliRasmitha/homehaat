from django.db import transaction
from django.utils.text import slugify
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response

from accounts.models import User
from catalog.models import Category, Product, Seller
from catalog.serializers import CategorySerializer, ProductSerializer, SellerProductSerializer, StoreSerializer


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
        with transaction.atomic():
            store = serializer.save(owner=request.user, slug=unique_slug(serializer.validated_data["name"]))
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


class MyProductList(generics.ListCreateAPIView):
    permission_classes = [IsSeller]
    serializer_class = SellerProductSerializer
    pagination_class = None

    def get_queryset(self):
        return self.request.user.seller.products.select_related("category")  # only your own products

    def perform_create(self, serializer):
        # The seller always comes from the signed-in user, never from the request body.
        serializer.save(seller=self.request.user.seller)


class MyProductDetail(generics.RetrieveUpdateAPIView):
    permission_classes = [IsSeller]
    serializer_class = SellerProductSerializer

    def get_queryset(self):
        return self.request.user.seller.products.all()  # another seller's product id gives 404
