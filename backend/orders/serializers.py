from rest_framework import serializers

from core.media import public_url
from orders.models import Order, OrderItem, Refund, SellerOrder
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
        return public_url(first.image) if first else None  # custom items: private route

    def get_tint(self, item):
        return item.product.category.tint if item.product else "soft"  # product deleted later: neutral

    def get_art(self, item):
        return item.product.category.art if item.product else "gift"


def refund_data(seller_order):
    """{amount, status} of this part's refund, or None. Uses the prefetched one-to-one when it's there."""
    try:
        refund = seller_order.refund
    except Refund.DoesNotExist:
        return None
    return {"amount": refund.amount, "status": refund.status}


def _is_custom(seller_order) -> bool:
    return any(item.product and item.product.is_custom for item in seller_order.items.all())  # prefetched


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
            "refund",
            "cancelled_by",
            "can_cancel",
            "can_request_cancel",
            "cancel_requested",
            "cancel_declined",
        ]

    can_review = serializers.SerializerMethodField()
    my_review = serializers.SerializerMethodField()
    refund = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()
    can_request_cancel = serializers.SerializerMethodField()
    cancel_requested = serializers.SerializerMethodField()
    cancel_declined = serializers.SerializerMethodField()

    # What the buyer's buttons may offer. orders/cancel.py checks the same rules again on the server.
    def get_can_cancel(self, part):
        return part.order.payment_status == Order.PaymentStatus.PAID and part.status == SellerOrder.Status.NEW

    def get_can_request_cancel(self, part):
        return (
            part.order.payment_status == Order.PaymentStatus.PAID
            and part.status == SellerOrder.Status.PREPARING
            and not part.cancel_requested_at
            and not part.cancel_declined_at
            and not _is_custom(part)
        )

    def get_cancel_requested(self, part):
        return bool(part.cancel_requested_at) and part.status == SellerOrder.Status.PREPARING

    def get_cancel_declined(self, part):
        return bool(part.cancel_declined_at) and part.status != SellerOrder.Status.CANCELLED

    def get_refund(self, part):
        return refund_data(part)

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
    refund = serializers.SerializerMethodField()
    cancel_requested = serializers.SerializerMethodField()

    def get_refund(self, part):
        return refund_data(part)

    def get_cancel_requested(self, part):
        return bool(part.cancel_requested_at) and part.status == SellerOrder.Status.PREPARING

    class Meta:
        model = SellerOrder
        fields = [
            "id",
            "order_id",
            "refund",
            "cancel_requested",
            "cancelled_by",
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
