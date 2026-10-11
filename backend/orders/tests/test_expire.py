"""Unpaid orders give their held stock back after 15 minutes."""

from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from core.tests.factories import add_to_cart, make_address, make_product, make_seller, make_user
from orders.models import Order
from orders.services import create_order_from_cart, expire_unpaid_orders
from payments.webhook import mark_order_paid


class ExpireOrdersTests(TestCase):
    def setUp(self):
        self.cake = make_product(make_seller(), stock=5)

    def checkout(self, minutes_ago=0, qty=1):
        buyer = make_user()
        add_to_cart(buyer, self.cake, qty=qty)
        order = create_order_from_cart(buyer, make_address(buyer))
        Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - timedelta(minutes=minutes_ago))
        return order

    def test_old_unpaid_order_fails_and_gives_stock_back(self):
        old = self.checkout(minutes_ago=16, qty=2)
        self.cake.refresh_from_db()
        self.assertEqual(self.cake.stock, 3)

        self.assertEqual(expire_unpaid_orders(), 1)

        old.refresh_from_db()
        self.cake.refresh_from_db()
        self.assertEqual(old.payment_status, Order.PaymentStatus.FAILED)
        self.assertFalse(old.stock_held)
        self.assertEqual(self.cake.stock, 5)

    def test_fresh_and_paid_orders_are_left_alone(self):
        fresh = self.checkout(minutes_ago=5)
        paid = self.checkout(minutes_ago=60)
        mark_order_paid(paid, "pay_1", paid.grand_total)

        self.assertEqual(expire_unpaid_orders(), 0)

        fresh.refresh_from_db()
        paid.refresh_from_db()
        self.assertEqual(fresh.payment_status, Order.PaymentStatus.PENDING)
        self.assertEqual(paid.payment_status, Order.PaymentStatus.PAID)
        self.cake.refresh_from_db()
        self.assertEqual(self.cake.stock, 3)  # both still hold their cake

    def test_running_twice_gives_stock_back_only_once(self):
        self.checkout(minutes_ago=20)
        expire_unpaid_orders()
        expire_unpaid_orders()
        self.cake.refresh_from_db()
        self.assertEqual(self.cake.stock, 5)

    def test_management_command(self):
        self.checkout(minutes_ago=30)
        out = StringIO()
        call_command("expire_orders", stdout=out)
        self.assertIn("1 unpaid order", out.getvalue())
