import re

from rest_framework import serializers

from catalog.models import Category, Product, ProductImage, Seller


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["slug", "name", "tint", "art", "photo_id"]


class CategoryWithCountSerializer(CategorySerializer):
    product_count = serializers.IntegerField(read_only=True)  # live products, annotated in the view

    class Meta(CategorySerializer.Meta):
        fields = [*CategorySerializer.Meta.fields, "product_count"]


class PublicStoreSerializer(serializers.ModelSerializer):
    """What buyers see about a shop. Counts and rating are annotated from the database (browse.public_stores)."""

    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    main_category = CategorySerializer(read_only=True)  # its photo is the cover when there's no upload
    cover = serializers.SerializerMethodField()
    product_count = serializers.IntegerField(read_only=True)
    rating = serializers.SerializerMethodField()
    review_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Seller
        fields = [
            "slug",
            "name",
            "kind",
            "kind_label",
            "area",
            "bio",
            "cover",
            "main_category",
            "delivery_days",
            "delivery_fee_paise",
            "product_count",
            "rating",
            "review_count",
        ]

    def get_cover(self, store):
        return store.cover.url if store.cover else None

    def get_rating(self, store):
        return round(store.rating, 1) if store.rating is not None else None  # None = no reviews yet


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
    images = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "price_paise",
            "stock",
            "category",
            "seller",
            "image",
            "images",
            "created_at",
        ]

    def get_image(self, product):
        first = next(iter(product.images.all()), None)  # uses prefetch_related, no extra query
        return first.image.url if first else None

    def get_images(self, product):
        return [img.image.url for img in product.images.all()]  # in the seller's chosen order


SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class StoreSerializer(serializers.ModelSerializer):
    """The seller's own store: 'Open your shop' and Store settings."""

    main_category = serializers.SlugRelatedField(
        slug_field="slug", queryset=Category.objects.all(), required=False, allow_null=True
    )
    slug = serializers.CharField(max_length=60, required=False)
    cover = serializers.SerializerMethodField()

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
            "cover",
        ]
        # owner is never in this list, so it can't be changed through the API

    def get_cover(self, store):
        return store.cover.url if store.cover else None

    def validate_slug(self, value):
        value = value.strip().lower()
        if not SLUG_RE.match(value):
            raise serializers.ValidationError("Use small letters, numbers and dashes, like asha-bakes.")
        taken = Seller.objects.filter(slug=value)
        if self.instance:
            taken = taken.exclude(pk=self.instance.pk)  # keeping your own link is fine
        if taken.exists():
            raise serializers.ValidationError("That shop link is taken. Try another.")
        return value


class ProductImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "url", "position"]

    def get_url(self, img):
        return img.image.url


class SellerProductSerializer(serializers.ModelSerializer):
    """What a seller sends to add or edit their own product, and sees in their list."""

    category = serializers.SlugRelatedField(slug_field="slug", queryset=Category.objects.all())
    images = ProductImageSerializer(many=True, read_only=True)
    image = serializers.SerializerMethodField()
    sold = serializers.IntegerField(read_only=True, default=0)  # annotated in the view

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "category",
            "price_paise",
            "stock",
            "is_active",
            "images",
            "image",
            "sold",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_image(self, product):
        first = next(iter(product.images.all()), None)
        return first.image.url if first else None
