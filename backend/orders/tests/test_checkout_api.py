"""API tests for POST /api/checkout/ and order reading permissions."""

from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from core.tests.factories import add_to_cart, make_address, make_product, make_seller, make_user
from orders.models import Order
from orders.services import create_order_from_cart
from payments.webhook import mark_order_paid

FAKE_RZP_ORDER = {"id": "order_FAKE1", "amount": 49000, "currency": "INR"}


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


class CheckoutApiTests(TestCase):
    url = "/api/checkout/"

    def setUp(self):
        self.buyer = make_user()
        self.address = make_address(self.buyer)
        self.seller = make_seller(delivery_fee_paise=4000)
        self.cake = make_product(self.seller, price_paise=45000, stock=5)
        add_to_cart(self.buyer, self.cake)

    def test_creates_pending_order_and_razorpay_order(self):
        with patch("orders.views.razorpay_client.create_order", return_value=FAKE_RZP_ORDER) as create:
            res = client_for(self.buyer).post(self.url, {"address_id": self.address.id}, format="json")

        self.assertEqual(res.status_code, 201)
        create.assert_called_once()
        self.assertEqual(create.call_args.kwargs["amount_paise"], 49000)
        order = Order.objects.get()
        self.assertEqual(order.razorpay_order_id, "order_FAKE1")
        self.assertEqual(res.data["razorpay_order_id"], "order_FAKE1")
        self.assertEqual(res.data["amount"], 49000)

    def test_a_price_sent_in_the_request_body_is_ignored(self):
        body = {"address_id": self.address.id, "grand_total": 100, "price_paise": 100, "amount": 100}
        with patch("orders.views.razorpay_client.create_order", return_value=FAKE_RZP_ORDER) as create:
            res = client_for(self.buyer).post(self.url, body, format="json")

        self.assertEqual(res.status_code, 201)
        self.assertEqual(Order.objects.get().grand_total, 49000)
        self.assertEqual(create.call_args.kwargs["amount_paise"], 49000)

    def test_cannot_use_another_buyers_address(self):
        other_address = make_address(make_user())
        with patch("orders.views.razorpay_client.create_order", return_value=FAKE_RZP_ORDER):
            res = client_for(self.buyer).post(self.url, {"address_id": other_address.id}, format="json")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(Order.objects.count(), 0)

    def test_sold_out_items_are_reported(self):
        self.cake.stock = 0
        self.cake.save()
        with patch("orders.views.razorpay_client.create_order") as create:
            res = client_for(self.buyer).post(self.url, {"address_id": self.address.id}, format="json")

        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.data["sold_out"], [self.cake.name])
        create.assert_not_called()

    def test_razorpay_failure_marks_order_failed(self):
        from payments.razorpay_client import RazorpayError

        with patch("orders.views.razorpay_client.create_order", side_effect=RazorpayError("down")):
            res = client_for(self.buyer).post(self.url, {"address_id": self.address.id}, format="json")

        self.assertEqual(res.status_code, 502)
        self.assertEqual(Order.objects.get().payment_status, Order.PaymentStatus.FAILED)

    def test_requires_sign_in(self):
        res = APIClient().post(self.url, {"address_id": self.address.id}, format="json")
        self.assertEqual(res.status_code, 403)


class OrderPermissionTests(TestCase):
    def setUp(self):
        self.buyer_a = make_user()
        self.seller_a = make_seller()
        add_to_cart(self.buyer_a, make_product(self.seller_a))
        self.order = create_order_from_cart(self.buyer_a, make_address(self.buyer_a))

    def test_buyer_b_cannot_read_buyer_a_order(self):
        res = client_for(make_user()).get(f"/api/orders/{self.order.id}/")
        self.assertEqual(res.status_code, 404)

    def test_buyer_a_can_read_own_order(self):
        res = client_for(self.buyer_a).get(f"/api/orders/{self.order.id}/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["grand_total"], self.order.grand_total)

    def test_seller_sees_only_their_own_paid_orders(self):
        seller_b = make_seller()
        pending_res = client_for(self.seller_a.owner).get("/api/seller/orders/")
        self.assertEqual(pending_res.data, [])  # unpaid orders are not shown to sellers

        mark_order_paid(self.order, "pay_x", self.order.grand_total)
        self.assertEqual(len(client_for(self.seller_a.owner).get("/api/seller/orders/").data), 1)
        self.assertEqual(client_for(seller_b.owner).get("/api/seller/orders/").data, [])

    def test_buyer_without_a_store_gets_no_seller_orders(self):
        res = client_for(make_user()).get("/api/seller/orders/")
        self.assertEqual(res.status_code, 403)
