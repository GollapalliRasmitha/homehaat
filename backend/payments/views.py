import json
import logging

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from orders.models import Order
from payments import razorpay_client
from payments.refunds import apply_webhook as apply_refund_webhook
from payments.webhook import (
    PaymentError,
    mark_order_paid,
    verify_checkout_signature,
    verify_webhook_signature,
)

log = logging.getLogger("homehaat.payments")


@api_view(["POST"])
@authentication_classes([])  # Razorpay's servers call this: no session, no CSRF
@permission_classes([AllowAny])  # trust comes from the signature instead
def webhook(request):
    secret = settings.RAZORPAY_WEBHOOK_SECRET
    if not secret:
        return Response({"detail": "Webhook secret not configured."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    # Check the signature against the exact raw bytes, before trusting anything inside.
    raw_body = request.body
    if not verify_webhook_signature(raw_body, request.headers.get("X-Razorpay-Signature", ""), secret):
        log.warning("Webhook with a bad signature was rejected.")
        return Response({"detail": "Bad signature."}, status=status.HTTP_400_BAD_REQUEST)

    event = json.loads(raw_body)
    if event.get("event") in ("refund.processed", "refund.failed"):
        # A refund we started has finished (or failed: retry_refunds will send a new one).
        known = apply_refund_webhook(event["payload"]["refund"]["entity"])
        return Response({"ok": True, "refund": "updated" if known else "not ours"})
    if event.get("event") != "payment.captured":
        return Response({"ok": True, "ignored": event.get("event")})

    payment = event["payload"]["payment"]["entity"]
    order = Order.objects.filter(razorpay_order_id=payment.get("order_id")).first()
    if order is None:
        return Response({"ok": True, "ignored": "unknown order"})  # not ours; don't make Razorpay retry

    try:
        mark_order_paid(order, payment["id"], payment["amount"])
    except PaymentError as exc:
        log.error("Webhook refused for order %s: %s", order.pk, exc)
        return Response({"detail": "Payment doesn't match the order."}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"ok": True})


class VerifySerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField(max_length=40)
    razorpay_payment_id = serializers.CharField(max_length=40)
    razorpay_signature = serializers.CharField(max_length=128)


@api_view(["POST"])
def verify(request):
    """
    Local backup for the webhook (Razorpay can't reach localhost). The browser
    forwards what Checkout.js gave it; we check the signature, then ask
    Razorpay ourselves how much was actually captured.
    """
    data = VerifySerializer(data=request.data)
    data.is_valid(raise_exception=True)
    rzp_order_id = data.validated_data["razorpay_order_id"]
    payment_id = data.validated_data["razorpay_payment_id"]

    # Only the buyer's own order. Someone else's order id gives 404.
    order = get_object_or_404(Order, razorpay_order_id=rzp_order_id, buyer=request.user)

    if not verify_checkout_signature(
        rzp_order_id, payment_id, data.validated_data["razorpay_signature"], settings.RAZORPAY_KEY_SECRET
    ):
        return Response({"detail": "Bad signature."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        payment = razorpay_client.fetch_payment(payment_id)
        if payment.get("status") == "authorized":  # not captured yet: capture the exact order amount
            payment = razorpay_client.capture_payment(payment_id, order.grand_total)
    except razorpay_client.RazorpayError as exc:
        log.error("Couldn't check payment %s: %s", payment_id, exc)
        return Response({"detail": "Couldn't confirm with Razorpay. Please try again."}, status=502)

    if payment.get("status") != "captured" or payment.get("order_id") != rzp_order_id:
        return Response({"detail": "Payment not captured."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        mark_order_paid(order, payment_id, payment["amount"])  # same function as the webhook
    except PaymentError as exc:
        log.error("Verify refused for order %s: %s", order.pk, exc)
        return Response({"detail": "Payment doesn't match the order."}, status=status.HTTP_400_BAD_REQUEST)

    order.refresh_from_db()
    return Response({"order_id": order.pk, "payment_status": order.payment_status})
