from rest_framework import serializers

from orders.models import Order, OrderItem, SellerOrder
from orders.services import hold_expires_at


class OrderItemSerializer(serializers.ModelSerializer):
    # The item's picture (its product's first photo) and its category's drawing + tint for when there's none.
    # Order endpoints are already limited to that order's buyer and its sellers.
    image = serializers.SerializerMethodField()
    tint = serializers.SerializerMethodField()
    art = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ["id", "product_id", "name", "unit_price", "qty", "note", "line_total", "image", "tint", "art"]

    def get_image(self, item):
        first = next(iter(item.product.images.all()), None) if item.product else None  # prefetched
        return first.image.url if first else None

    def get_tint(self, item):
        return item.product.category.tint if item.product else "soft"  # product deleted later: neutral

    def get_art(self, item):
        return item.product.category.art if item.product else "gift"


class SellerOrderSerializer(serializers.ModelSerializer):
    seller = serializers.SerializerMethodField()
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = SellerOrder
        fields = [
            "id",
            "seller",
            "subtotal",
            "delivery_fee",
            "status",
            "refund_needed",
            "items",
            "can_review",
            "my_review",
        ]

    can_review = serializers.SerializerMethodField()
    my_review = serializers.SerializerMethodField()

    def get_seller(self, seller_order):
        return {"slug": seller_order.seller.slug, "name": seller_order.seller.name}

    def get_can_review(self, seller_order):
        return seller_order.status == SellerOrder.Status.DELIVERED  # write_review checks this again on the server

    def get_my_review(self, seller_order):
        # The buyer's reviews, loaded once per request by the view (seller id -> review).
        review = self.context.get("my_reviews", {}).get(seller_order.seller_id)
        return {"rating": review.rating, "comment": review.comment} if review else None


class OrderSerializer(serializers.ModelSerializer):
    """The buyer's view of their order: one block per seller."""

    seller_orders = SellerOrderSerializer(many=True, read_only=True)
    hold_expires_at = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "payment_status",
            "items_total",
            "delivery_total",
            "grand_total",
            "ship_to",
            "created_at",
            "paid_at",
            "hold_expires_at",
            "seller_orders",
        ]

    def get_hold_expires_at(self, order):
        return hold_expires_at(order) if order.payment_status == Order.PaymentStatus.PENDING else None


class IncomingOrderSerializer(serializers.ModelSerializer):
    """The seller's view: their share only, plus where to deliver it."""

    order_id = serializers.IntegerField(source="order.id")
    paid_at = serializers.DateTimeField(source="order.paid_at")
    # Buyer's name, phone and address: visible only to the sellers of this order.
    ship_to = serializers.JSONField(source="order.ship_to")
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = SellerOrder
        fields = [
            "id",
            "order_id",
            "paid_at",
            "status",
            "subtotal",
            "delivery_fee",
            "refund_needed",
            "preparing_at",
            "out_for_delivery_at",
            "delivered_at",
            "cancelled_at",
            "ship_to",
            "items",
        ]
        read_only_fields = fields  # sellers change the status only through advance_status
