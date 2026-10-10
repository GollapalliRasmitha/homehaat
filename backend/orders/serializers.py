from rest_framework import serializers

from orders.models import Order, OrderItem, SellerOrder


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["id", "product_id", "name", "unit_price", "qty", "note", "line_total"]


class SellerOrderSerializer(serializers.ModelSerializer):
    seller = serializers.SerializerMethodField()
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = SellerOrder
        fields = ["id", "seller", "subtotal", "delivery_fee", "status", "items"]

    def get_seller(self, seller_order):
        return {"slug": seller_order.seller.slug, "name": seller_order.seller.name}


class OrderSerializer(serializers.ModelSerializer):
    """The buyer's view of their order: one block per seller."""

    seller_orders = SellerOrderSerializer(many=True, read_only=True)

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
            "seller_orders",
        ]


class IncomingOrderSerializer(serializers.ModelSerializer):
    """The seller's view: their share only, plus where to deliver it."""

    order_id = serializers.IntegerField(source="order.id")
    paid_at = serializers.DateTimeField(source="order.paid_at")
    # Buyer's name, phone and address: visible only to the sellers of this order.
    ship_to = serializers.JSONField(source="order.ship_to")
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = SellerOrder
        fields = ["id", "order_id", "paid_at", "status", "subtotal", "delivery_fee", "ship_to", "items"]
