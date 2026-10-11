"""
[KEY LOGIC] Tests for advance_status: the seller moves their part of an order along.
Written before the code, as the brief asks.

Allowed: new -> preparing -> out_for_delivery -> delivered, and new or preparing -> cancelled.
"""

from django.test import TestCase

from core.tests.factories import make_paid_order, make_product, make_seller, make_user
from orders.models import Order, SellerOrder
from orders.services import create_order_from_cart
from orders.status import NotYourOrderError, StatusError, advance_status

S = SellerOrder.Status


class AdvanceStatusTests(TestCase):
    def setUp(self):
        self.seller = make_seller()
        self.cake = make_product(self.seller, stock=5)
        self.part = make_paid_order(self.cake, qty=2)  # stock 5 -> 3
        self.owner = self.seller.owner

    def test_the_happy_path_new_to_delivered(self):
        for step in [S.PREPARING, S.OUT_FOR_DELIVERY, S.DELIVERED]:
            advance_status(self.part, step, self.owner)

        self.part.refresh_from_db()
        self.assertEqual(self.part.status, S.DELIVERED)
        # each step records when it happened
        self.assertIsNotNone(self.part.preparing_at)
        self.assertIsNotNone(self.part.out_for_delivery_at)
        self.assertIsNotNone(self.part.delivered_at)

    def test_cannot_skip_steps(self):
        with self.assertRaises(StatusError):
            advance_status(self.part, S.DELIVERED, self.owner)  # new -> delivered skips two steps
        self.part.refresh_from_db()
        self.assertEqual(self.part.status, S.NEW)

    def test_cannot_go_backwards(self):
        advance_status(self.part, S.PREPARING, self.owner)
        with self.assertRaises(StatusError):
            advance_status(self.part, S.NEW, self.owner)

    def test_cannot_cancel_once_out_for_delivery(self):
        advance_status(self.part, S.PREPARING, self.owner)
        advance_status(self.part, S.OUT_FOR_DELIVERY, self.owner)
        with self.assertRaises(StatusError):
            advance_status(self.part, S.CANCELLED, self.owner)

    def test_delivered_and_cancelled_are_final(self):
        advance_status(self.part, S.CANCELLED, self.owner)
        for step in [S.NEW, S.PREPARING, S.DELIVERED, S.CANCELLED]:
            with self.assertRaises(StatusError):
                advance_status(self.part, step, self.owner)

    def test_unknown_status_is_rejected(self):
        with self.assertRaises(StatusError):
            advance_status(self.part, "shipped", self.owner)

    def test_cancelling_a_paid_part_records_refund_needed_and_returns_the_stock(self):
        advance_status(self.part, S.CANCELLED, self.owner)

        self.part.refresh_from_db()
        self.cake.refresh_from_db()
        self.assertEqual(self.part.status, S.CANCELLED)
        self.assertTrue(self.part.refund_needed)
        self.assertIsNotNone(self.part.cancelled_at)
        self.assertEqual(self.cake.stock, 5)  # the 2 cakes go back on the shelf

    def test_another_seller_cannot_change_my_order(self):
        intruder = make_seller().owner
        with self.assertRaises(NotYourOrderError):
            advance_status(self.part, S.PREPARING, intruder)
        self.part.refresh_from_db()
        self.assertEqual(self.part.status, S.NEW)

    def test_the_buyer_cannot_change_the_status_either(self):
        with self.assertRaises(NotYourOrderError):
            advance_status(self.part, S.PREPARING, self.part.order.buyer)

    def test_unpaid_orders_cannot_be_moved(self):
        from core.tests.factories import add_to_cart, make_address

        buyer = make_user()
        add_to_cart(buyer, self.cake)
        unpaid = create_order_from_cart(buyer, make_address(buyer)).seller_orders.get()
        self.assertEqual(unpaid.order.payment_status, Order.PaymentStatus.PENDING)
        with self.assertRaises(StatusError):
            advance_status(unpaid, S.PREPARING, self.owner)

    def test_only_the_status_changes_never_the_money(self):
        before = (self.part.subtotal, self.part.delivery_fee, self.part.order.grand_total)
        advance_status(self.part, S.PREPARING, self.owner)
        self.part.refresh_from_db()
        self.assertEqual((self.part.subtotal, self.part.delivery_fee, self.part.order.grand_total), before)
