"""
[KEY LOGIC] The race test: two buyers try to buy the last cake at the same moment.

TransactionTestCase (not TestCase) so each thread gets its own real database
connection and real transactions, exactly like two web requests would.
"""

import threading

from django.db import connection
from django.test import TransactionTestCase

from core.tests.factories import add_to_cart, make_address, make_product, make_seller, make_user
from orders.models import Order
from orders.services import SoldOutError, create_order_from_cart


class LastItemRaceTests(TransactionTestCase):
    def test_two_buyers_racing_for_the_last_item_give_one_order_and_one_sold_out(self):
        cake = make_product(make_seller(), stock=1, name="Last cake")
        buyers = [make_user(), make_user()]
        for buyer in buyers:
            add_to_cart(buyer, cake)
            make_address(buyer)

        start_together = threading.Barrier(len(buyers))
        results = []

        def checkout(buyer):
            try:
                start_together.wait()  # release both threads at the same instant
                create_order_from_cart(buyer, buyer.addresses.first())
                results.append("order")
            except SoldOutError:
                results.append("sold out")
            finally:
                connection.close()  # each thread opened its own connection

        threads = [threading.Thread(target=checkout, args=(b,)) for b in buyers]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(sorted(results), ["order", "sold out"])
        self.assertEqual(Order.objects.count(), 1)
        cake.refresh_from_db()
        self.assertEqual(cake.stock, 0)  # never -1
