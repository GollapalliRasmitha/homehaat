from datetime import date

from rest_framework import serializers

from catalog.serializers import SellerSummarySerializer
from core.media import public_url
from custom_requests.models import CustomRequest


class NewRequestSerializer(serializers.Serializer):
    """What a buyer sends. Only these fields are read."""

    seller = serializers.SlugField()  # the shop's link
    description = serializers.CharField(min_length=20, max_length=2000)
    needed_by = serializers.DateField(required=False, allow_null=True)
    budget_paise = serializers.IntegerField(required=False, allow_null=True, min_value=0, max_value=100_000_000)

    def validate_description(self, value):
        value = value.strip()
        if len(value) < 20:
            raise serializers.ValidationError(
                "Please describe what you need in a sentence or two, so the maker can price it."
            )
        return value

    def validate_needed_by(self, value):
        if value and value < date.today():
            raise serializers.ValidationError("Choose today or a later date.")
        return value


class QuoteSerializer(serializers.Serializer):
    quote_paise = serializers.IntegerField(
        min_value=100,
        max_value=100_000_000,
        # In rupees, the way sellers think (the form sends paise; ₹1 = 100 paise).
        error_messages={
            "min_value": "Enter a price of ₹1 or more.",
            "max_value": "That price is too high. Please check it.",
            "invalid": "Enter a price in rupees, like 450.",
        },
    )
    note = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")


class CustomRequestSerializer(serializers.ModelSerializer):
    """One request, as its buyer or its seller sees it."""

    seller = SellerSummarySerializer(read_only=True)
    buyer_name = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    in_bag = serializers.SerializerMethodField()
    ordered = serializers.SerializerMethodField()

    class Meta:
        model = CustomRequest
        fields = [
            "id",
            "seller",
            "buyer_name",
            "description",
            "needed_by",
            "budget_paise",
            "quote_paise",
            "seller_note",
            "status",
            "images",
            "in_bag",
            "ordered",
            "created_at",
            "responded_at",
        ]

    def get_buyer_name(self, req):
        # First name only: the buyer's full name, email and phone stay private until they order.
        return req.buyer.name.split(" ")[0] if req.buyer.name else "A buyer"

    def get_images(self, req):
        return [public_url(img.image) for img in req.images.all()]  # private route

    def get_in_bag(self, req):
        return bool(req.product_id) and req.product.cart_items.filter(user_id=req.buyer_id).exists()

    def get_ordered(self, req):
        # The one-off product had stock 1: 0 means it's in a checkout or has been bought.
        return bool(req.product_id) and req.product.stock == 0
