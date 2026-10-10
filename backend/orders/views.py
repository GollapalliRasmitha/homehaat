import logging

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import generics, serializers, status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from accounts.models import Address
from catalog.views import IsSeller
from orders.models import Order, SellerOrder
from orders.serializers import IncomingOrderSerializer, OrderSerializer
from orders.services import CheckoutError, SoldOutError, create_order_from_cart
from payments import razorpay_client

log = logging.getLogger("homehaat.orders")


class CheckoutThrottle(UserRateThrottle):
    scope = "checkout"


class CheckoutSerializer(serializers.Serializer):
    # The only thing the browser chooses is the address. Prices and totals are
    # computed on the server, so anything else in the request is ignored.
    address_id = serializers.IntegerField()


@api_view(["POST"])
@throttle_classes([CheckoutThrottle])
def checkout(request):
    data = CheckoutSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    address = get_object_or_404(Address, pk=data.validated_data["address_id"], user=request.user)

    try:
        order = create_order_from_cart(request.user, address)
    except SoldOutError as exc:
        return Response({"detail": exc.message, "sold_out": exc.items}, status=status.HTTP_409_CONFLICT)
    except CheckoutError as exc:
        return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)

    try:
        rzp_order = razorpay_client.create_order(amount_paise=order.grand_total, receipt=f"homehaat-{order.pk}")
    except razorpay_client.RazorpayError as exc:
        log.error("Razorpay order failed for order %s: %s", order.pk, exc)
        order.payment_status = Order.PaymentStatus.FAILED
        order.save(update_fields=["payment_status"])
        return Response({"detail": "Payments are unavailable right now. You haven't been charged."}, status=502)

    order.razorpay_order_id = rzp_order["id"]
    order.save(update_fields=["razorpay_order_id"])

    # Everything Checkout.js needs. The key id is public by design; the secrets never leave the server.
    return Response(
        {
            "order_id": order.pk,
            "razorpay_order_id": order.razorpay_order_id,
            "amount": order.grand_total,
            "currency": "INR",
            "key_id": settings.RAZORPAY_KEY_ID,
            "prefill": {"name": request.user.name, "email": request.user.email, "contact": address.phone},
        },
        status=status.HTTP_201_CREATED,
    )


def orders_with_details():
    return Order.objects.prefetch_related("seller_orders__seller", "seller_orders__items")


class MyOrderList(generics.ListAPIView):
    serializer_class = OrderSerializer
    pagination_class = None

    def get_queryset(self):
        return orders_with_details().filter(buyer=self.request.user)


class MyOrderDetail(generics.RetrieveAPIView):
    serializer_class = OrderSerializer

    def get_queryset(self):
        return orders_with_details().filter(buyer=self.request.user)  # someone else's order gives 404


class IncomingOrderList(generics.ListAPIView):
    """Paid orders for the signed-in seller's store. Unpaid orders aren't shown."""

    permission_classes = [IsSeller]
    serializer_class = IncomingOrderSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            SellerOrder.objects.filter(seller=self.request.user.seller, order__payment_status=Order.PaymentStatus.PAID)
            .select_related("order")
            .prefetch_related("items")
            .order_by("-order__paid_at")
        )
