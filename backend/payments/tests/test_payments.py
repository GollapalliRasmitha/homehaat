"""
Tests for the payment confirmation: signature checks and mark_order_paid.
Razorpay is never called for real here; we fake its responses.
"""

import hashlib
import hmac
import json
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.tests.factories import add_to_cart, make_address, make_product, make_seller, make_user
from orders.models import Order
from orders.services import create_order_from_cart
from payments.webhook import (
    AmountMismatchError,
    mark_order_paid,
    verify_checkout_signature,
    verify_webhook_signature,
)

WEBHOOK_SECRET = "whsec_test_123"
KEY_SECRET = "key_secret_test_123"


def sign(message: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


class SignatureTests(TestCase):
    def test_webhook_signature_accepts_the_right_secret_only(self):
        body = b'{"event":"payment.captured"}'
        self.assertTrue(verify_webhook_signature(body, sign(body, WEBHOOK_SECRET), WEBHOOK_SECRET))
        self.assertFalse(verify_webhook_signature(body, sign(body, "wrong"), WEBHOOK_SECRET))
        self.assertFalse(verify_webhook_signature(body + b" ", sign(body, WEBHOOK_SECRET), WEBHOOK_SECRET))
        self.assertFalse(verify_webhook_signature(body, "", WEBHOOK_SECRET))
        self.assertFalse(verify_webhook_signature(body, sign(body, ""), ""))  # no secret configured

    def test_checkout_signature_is_hmac_of_order_and_payment_ids(self):
        good = sign(b"order_A|pay_B", KEY_SECRET)
        self.assertTrue(verify_checkout_signature("order_A", "pay_B", good, KEY_SECRET))
        self.assertFalse(verify_checkout_signature("order_A", "pay_OTHER", good, KEY_SECRET))


class PaidOrderMixin:
    """A pending ₹490 order: one ₹450 cake + ₹40 delivery, stock 5."""

    def setUp(self):
        self.buyer = make_user()
        self.seller = make_seller(delivery_fee_paise=4000)
        self.cake = make_product(self.seller, price_paise=45000, stock=5)
        add_to_cart(self.buyer, self.cake, qty=1)
        self.order = create_order_from_cart(self.buyer, make_address(self.buyer))
        self.order.razorpay_order_id = "order_TEST123"
        self.order.save()


class MarkOrderPaidTests(PaidOrderMixin, TestCase):
    def test_marks_paid_reduces_stock_and_clears_cart(self):
        changed = mark_order_paid(self.order, "pay_1", 49000)

        self.assertTrue(changed)
        self.order.refresh_from_db()
        self.cake.refresh_from_db()
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.PAID)
        self.assertEqual(self.order.razorpay_payment_id, "pay_1")
        self.assertIsNotNone(self.order.paid_at)
        self.assertEqual(self.cake.stock, 4)
        self.assertEqual(self.buyer.cart_items.count(), 0)

    def test_is_idempotent(self):
        mark_order_paid(self.order, "pay_1", 49000)
        changed = mark_order_paid(self.order, "pay_1", 49000)

        self.assertFalse(changed)
        self.cake.refresh_from_db()
        self.assertEqual(self.cake.stock, 4)  # reduced once, not twice

    def test_amount_mismatch_is_rejected(self):
        with self.assertRaises(AmountMismatchError):
            mark_order_paid(self.order, "pay_1", 100)  # ₹1 instead of ₹490

        self.order.refresh_from_db()
        self.cake.refresh_from_db()
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.PENDING)
        self.assertEqual(self.cake.stock, 5)

    def test_keeps_cart_items_added_after_checkout(self):
        later = make_product(self.seller, name="Added later")
        add_to_cart(self.buyer, later)
        mark_order_paid(self.order, "pay_1", 49000)
        self.assertEqual(list(self.buyer.cart_items.values_list("product__name", flat=True)), ["Added later"])


@override_settings(RAZORPAY_WEBHOOK_SECRET=WEBHOOK_SECRET)
class WebhookViewTests(PaidOrderMixin, TestCase):
    url = "/api/payments/webhook/"

    def captured_event(self, amount=49000, payment_id="pay_1"):
        return json.dumps(
            {
                "event": "payment.captured",
                "payload": {
                    "payment": {
                        "entity": {
                            "id": payment_id,
                            "order_id": "order_TEST123",
                            "amount": amount,
                            "status": "captured",
                        }
                    }
                },
            }
        ).encode()

    def post(self, body, signature):
        # Webhooks come from Razorpay's servers: no session, no CSRF token.
        return APIClient(enforce_csrf_checks=True).post(
            self.url, body, content_type="application/json", HTTP_X_RAZORPAY_SIGNATURE=signature
        )

    def test_happy_path(self):
        body = self.captured_event()
        res = self.post(body, sign(body, WEBHOOK_SECRET))

        self.assertEqual(res.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.PAID)

    def test_bad_signature_is_rejected(self):
        body = self.captured_event()
        res = self.post(body, sign(body, "not-the-secret"))

        self.assertEqual(res.status_code, 400)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.PENDING)

    def test_amount_mismatch_is_rejected(self):
        body = self.captured_event(amount=100)
        res = self.post(body, sign(body, WEBHOOK_SECRET))

        self.assertEqual(res.status_code, 400)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.PENDING)

    def test_repeated_webhook_does_not_reduce_stock_twice(self):
        body = self.captured_event()
        for _ in range(3):  # Razorpay may deliver the same event more than once
            self.assertEqual(self.post(body, sign(body, WEBHOOK_SECRET)).status_code, 200)

        self.cake.refresh_from_db()
        self.assertEqual(self.cake.stock, 4)

    def test_other_events_are_ignored(self):
        body = json.dumps({"event": "payment.failed", "payload": {}}).encode()
        res = self.post(body, sign(body, WEBHOOK_SECRET))

        self.assertEqual(res.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.PENDING)

    @override_settings(RAZORPAY_WEBHOOK_SECRET="")
    def test_webhook_refuses_everything_when_no_secret_is_configured(self):
        body = self.captured_event()
        self.assertEqual(self.post(body, sign(body, "")).status_code, 503)


@override_settings(RAZORPAY_KEY_SECRET=KEY_SECRET)
class VerifyViewTests(PaidOrderMixin, TestCase):
    """The local backup path: the browser forwards Razorpay's signed handler response."""

    url = "/api/payments/verify/"

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.force_authenticate(self.buyer)

    def body(self, signature=None):
        return {
            "razorpay_order_id": "order_TEST123",
            "razorpay_payment_id": "pay_1",
            "razorpay_signature": signature or sign(b"order_TEST123|pay_1", KEY_SECRET),
        }

    def fake_payment(self, amount=49000, status="captured"):
        return {"id": "pay_1", "order_id": "order_TEST123", "amount": amount, "status": status}

    def test_valid_signature_marks_order_paid(self):
        with patch("payments.views.razorpay_client.fetch_payment", return_value=self.fake_payment()):
            res = self.client.post(self.url, self.body(), format="json")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["payment_status"], "paid")
        self.cake.refresh_from_db()
        self.assertEqual(self.cake.stock, 4)

    def test_bad_signature_is_rejected(self):
        with patch("payments.views.razorpay_client.fetch_payment") as fetch:
            res = self.client.post(self.url, self.body(signature="forged"), format="json")

        self.assertEqual(res.status_code, 400)
        fetch.assert_not_called()
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.PENDING)

    def test_amount_mismatch_is_rejected(self):
        with patch("payments.views.razorpay_client.fetch_payment", return_value=self.fake_payment(amount=100)):
            res = self.client.post(self.url, self.body(), format="json")

        self.assertEqual(res.status_code, 400)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.PENDING)

    def test_uncaptured_payment_is_not_marked_paid(self):
        with (
            patch("payments.views.razorpay_client.fetch_payment", return_value=self.fake_payment(status="failed")),
        ):
            res = self.client.post(self.url, self.body(), format="json")
        self.assertEqual(res.status_code, 400)

    def test_another_buyer_cannot_confirm_this_order(self):
        intruder = APIClient()
        intruder.force_authenticate(make_user())
        with patch("payments.views.razorpay_client.fetch_payment", return_value=self.fake_payment()):
            res = intruder.post(self.url, self.body(), format="json")
        self.assertEqual(res.status_code, 404)
