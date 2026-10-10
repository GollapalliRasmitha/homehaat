from rest_framework import serializers

from catalog.models import Category, Product, Seller


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["slug", "name", "tint", "art", "photo_id"]


class SellerSummarySerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = Seller
        fields = ["slug", "name", "kind", "kind_label", "area", "delivery_days", "delivery_fee_paise"]


class ProductSerializer(serializers.ModelSerializer):
    """Public view of a product. Prices are integer paise."""

    category = CategorySerializer(read_only=True)
    seller = SellerSummarySerializer(read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "name", "description", "price_paise", "stock", "category", "seller", "image", "created_at"]

    def get_image(self, product):
        first = next(iter(product.images.all()), None)  # uses prefetch_related, no extra query
        return first.image.url if first else None


class StoreSerializer(serializers.ModelSerializer):
    """The seller's own store, used by 'Open your shop' and (later) Store settings."""

    main_category = serializers.SlugRelatedField(
        slug_field="slug", queryset=Category.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Seller
        fields = [
            "slug",
            "name",
            "kind",
            "main_category",
            "bio",
            "area",
            "delivery_days",
            "delivery_fee_paise",
            "is_active",
        ]
        read_only_fields = ["slug", "is_active"]


class SellerProductSerializer(serializers.ModelSerializer):
    """What a seller sends to add or edit their own product."""

    category = serializers.SlugRelatedField(slug_field="slug", queryset=Category.objects.all())

    class Meta:
        model = Product
        fields = ["id", "name", "description", "category", "price_paise", "stock", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]
