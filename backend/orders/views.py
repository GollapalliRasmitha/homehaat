import logging
from datetime import timedelta

from django.conf import settings
from django.db.models import Avg, Count, F, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, serializers, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from accounts.address_rules import address_problems
from accounts.models import Address
from catalog.views import IsSeller
from orders.cancel import answer_cancellation, buyer_cancel, request_cancellation
from orders.models import Order, Refund, SellerOrder
from orders.serializers import IncomingOrderSerializer, OrderSerializer
from orders.services import (
    CheckoutError,
    SoldOutError,
    create_order_from_cart,
    expire_unpaid_orders,
    hold_expires_at,
    release_hold,
)
from orders.status import NotYourOrderError, StatusError, advance_status
from payments import razorpay_client
from reviews.models import Review

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
    # An address saved before the address rules may be wrong (e.g. no real phone): ask for an update first,
    # before any order is created or stock is held.
    if problems := address_problems(address.__dict__):
        return Response(
            {"detail": "Please update this delivery address before paying.", "address_problems": problems},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Free anything whose 15-minute hold has run out, so this buyer can have it
    # even if the scheduled expire_orders job hasn't run yet.
    expire_unpaid_orders()

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
        release_hold(order)  # failed, and the held stock goes back on the shelf
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
            # Always the delivery address's phone (checked above), in Razorpay's +91 format, so Razorpay
            # doesn't ask the buyer for contact details again.
            "prefill": {
                "name": address.name or request.user.name,
                "email": request.user.email,
                "contact": f"+91{address.phone}",
            },
            "hold_expires_at": hold_expires_at(order),  # Checkout.js closes itself at this time
        },
        status=status.HTTP_201_CREATED,
    )


def orders_with_details():
    return Order.objects.prefetch_related(
        "seller_orders__seller",
        "seller_orders__items__product__category",
        "seller_orders__items__product__images",
        "seller_orders__refund",
    )


class BuyerOrderView:
    """Adds the buyer's own reviews (one query), so each seller block can show "Your review"."""

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["my_reviews"] = {r.seller_id: r for r in Review.objects.filter(buyer=self.request.user)}
        return context


class MyOrderList(BuyerOrderView, generics.ListAPIView):
    serializer_class = OrderSerializer
    pagination_class = None

    def get_queryset(self):
        # Failed attempts (closed payment window, expired hold) would only clutter the list.
        mine = orders_with_details().filter(buyer=self.request.user)
        return mine.exclude(payment_status=Order.PaymentStatus.FAILED)


class MyOrderDetail(BuyerOrderView, generics.RetrieveAPIView):
    serializer_class = OrderSerializer

    def get_queryset(self):
        return orders_with_details().filter(buyer=self.request.user)  # someone else's order gives 404


class IncomingOrderList(generics.ListAPIView):
    """Paid orders for the signed-in seller's store. Unpaid orders aren't shown."""

    permission_classes = [IsSeller]
    serializer_class = IncomingOrderSerializer
    pagination_class = None

    def get_queryset(self):
        mine = paid_parts(self.request.user.seller).order_by("-order__paid_at")
        wanted = self.request.query_params.get("status")
        return mine.filter(status=wanted) if wanted in SellerOrder.Status.values else mine


def paid_parts(seller):
    """This seller's parts of PAID orders, with what's needed to show them."""
    return (
        SellerOrder.objects.filter(seller=seller, order__payment_status=Order.PaymentStatus.PAID)
        .select_related("order", "refund")
        .prefetch_related("items__product__category", "items__product__images")
    )


class StatusSerializer(serializers.Serializer):
    status = serializers.CharField(max_length=20)  # the ONLY field read; amounts in the body are ignored


@api_view(["POST"])
@permission_classes([IsSeller])
def change_status(request, pk):
    data = StatusSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    part = get_object_or_404(SellerOrder, pk=pk)
    try:
        part = advance_status(part, data.validated_data["status"], request.user)
    except NotYourOrderError:
        return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
    except StatusError as exc:
        return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
    return Response(IncomingOrderSerializer(paid_parts(request.user.seller).get(pk=part.pk)).data)


OPEN = [SellerOrder.Status.NEW, SellerOrder.Status.PREPARING, SellerOrder.Status.OUT_FOR_DELIVERY]


def _buyer_part(request, pk):
    return get_object_or_404(SellerOrder, pk=pk)  # cancel.py then checks it's this buyer's (else 404)


def _buyer_answer(request, action):
    """Run a buyer action on one maker's part, then return the whole order as the buyer sees it."""
    try:
        part = action()
    except NotYourOrderError:
        return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
    except StatusError as exc:
        return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
    order = orders_with_details().get(pk=part.order_id)
    context = {"request": request, "my_reviews": {r.seller_id: r for r in Review.objects.filter(buyer=request.user)}}
    return Response(OrderSerializer(order, context=context).data)


@api_view(["POST"])
def cancel_part(request, pk):
    """Buyer: cancel one maker's part while it's New. Refunds exactly that part. Nothing is read from the body."""
    return _buyer_answer(request, lambda: buyer_cancel(_buyer_part(request, pk), request.user))


@api_view(["POST"])
def request_cancel(request, pk):
    """Buyer: ask the maker to cancel while they're preparing it."""
    return _buyer_answer(request, lambda: request_cancellation(_buyer_part(request, pk), request.user))


@api_view(["POST"])
@permission_classes([IsSeller])
def answer_cancel_request(request, pk):
    """Seller: {accept: true} cancels and refunds; {accept: false} keeps preparing it."""
    part = get_object_or_404(SellerOrder, pk=pk)
    try:
        part = answer_cancellation(part, request.user, accept=request.data.get("accept") is True)
    except NotYourOrderError:
        return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
    except StatusError as exc:
        return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
    return Response(IncomingOrderSerializer(paid_parts(request.user.seller).get(pk=part.pk)).data)


@api_view(["GET"])
@permission_classes([IsSeller])
def overview(request):
    """Dashboard numbers, all computed from the database. No data -> 0 or None, never a made-up number."""
    seller = request.user.seller
    parts = paid_parts(seller)
    week_ago = timezone.now() - timedelta(days=7)

    earnings = (
        parts.filter(order__paid_at__gte=week_ago)
        .exclude(status=SellerOrder.Status.CANCELLED)
        .aggregate(total=Coalesce(Sum(F("subtotal") + F("delivery_fee")), 0))["total"]
    )
    reviews = seller.reviews.aggregate(average=Avg("rating"), count=Count("id"))
    open_parts = parts.filter(status__in=OPEN)
    live = seller.products.filter(is_active=True, is_custom=False, is_archived=False)  # what buyers can see

    return Response(
        {
            "earnings_week": earnings,  # paise: items + delivery, paid in the last 7 days, not cancelled
            "open_orders": open_parts.count(),
            "products_listed": live.count(),
            "out_of_stock": live.filter(stock=0).count(),
            "open_requests": seller.custom_requests.filter(status="open").count(),
            # Refunds Razorpay refused or couldn't take yet: shown to the seller until a retry works.
            "refund_problems": [
                {"order_id": r.seller_order.order_id, "seller_order_id": r.seller_order_id, "amount": r.amount}
                for r in Refund.objects.filter(seller_order__seller=seller, status=Refund.Status.FAILED).select_related(
                    "seller_order"
                )
            ],
            "rating": round(reviews["average"], 1) if reviews["average"] is not None else None,
            "review_count": reviews["count"],
            "incoming": IncomingOrderSerializer(open_parts.order_by("order__paid_at")[:5], many=True).data,
        }
    )
