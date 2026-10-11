"""
Tests for create_order_from_cart (Stage 2: split per seller, stock held at checkout).
Written before the code, as the brief asks.
"""

from django.test import TestCase

from core.tests.factories import add_to_cart, make_address, make_product, make_seller, make_user
from orders.models import Order, OrderItem, SellerOrder
from orders.services import CheckoutError, SoldOutError, create_order_from_cart


class CreateOrderFromCartTests(TestCase):
    def setUp(self):
        self.buyer = make_user()
        self.address = make_address(self.buyer)
        self.seller = make_seller(delivery_fee_paise=4000)  # ₹40 delivery

    def test_happy_path_computes_totals_from_the_database(self):
        cake = make_product(self.seller, price_paise=45000, stock=5, name="Chocolate cake")  # ₹450
        jar = make_product(self.seller, price_paise=12000, stock=5, name="Mango pickle")  # ₹120
        add_to_cart(self.buyer, cake, qty=2, note="Write 'Happy birthday'")
        add_to_cart(self.buyer, jar, qty=1)

        order = create_order_from_cart(self.buyer, self.address)

        self.assertEqual(order.payment_status, Order.PaymentStatus.PENDING)
        self.assertEqual(order.items_total, 2 * 45000 + 12000)  # 102000 paise = ₹1,020
        self.assertEqual(order.delivery_total, 4000)
        self.assertEqual(order.grand_total, 106000)
        self.assertEqual(order.ship_to["pincode"], "560001")

        seller_order = SellerOrder.objects.get(order=order)
        self.assertEqual(seller_order.seller, self.seller)
        self.assertEqual(seller_order.subtotal, 102000)
        self.assertEqual(seller_order.delivery_fee, 4000)
        self.assertEqual(seller_order.status, SellerOrder.Status.NEW)

        item = OrderItem.objects.get(seller_order=seller_order, product=cake)
        self.assertEqual((item.name, item.unit_price, item.qty), ("Chocolate cake", 45000, 2))
        self.assertEqual(item.note, "Write 'Happy birthday'")

    def test_cart_from_three_sellers_creates_exactly_three_seller_orders(self):
        baker = make_seller(delivery_fee_paise=4000)  # ₹40
        pickler = make_seller(delivery_fee_paise=3000)  # ₹30
        artist = make_seller(delivery_fee_paise=0)  # free delivery
        add_to_cart(self.buyer, make_product(baker, price_paise=45000), qty=2)  # ₹900
        add_to_cart(self.buyer, make_product(baker, price_paise=5000), qty=1)  # ₹50
        add_to_cart(self.buyer, make_product(pickler, price_paise=12000), qty=3)  # ₹360
        add_to_cart(self.buyer, make_product(artist, price_paise=150000), qty=1)  # ₹1,500

        order = create_order_from_cart(self.buyer, self.address)

        parts = {so.seller_id: so for so in order.seller_orders.all()}
        self.assertEqual(len(parts), 3)
        self.assertEqual((parts[baker.id].subtotal, parts[baker.id].delivery_fee), (95000, 4000))
        self.assertEqual((parts[pickler.id].subtotal, parts[pickler.id].delivery_fee), (36000, 3000))
        self.assertEqual((parts[artist.id].subtotal, parts[artist.id].delivery_fee), (150000, 0))
        self.assertEqual(parts[baker.id].items.count(), 2)

        self.assertEqual(order.items_total, 95000 + 36000 + 150000)
        self.assertEqual(order.delivery_total, 4000 + 3000 + 0)  # one fee per seller
        self.assertEqual(order.grand_total, 281000 + 7000)

    def test_snapshots_do_not_change_when_the_seller_edits_the_product(self):
        cake = make_product(self.seller, price_paise=45000, name="Chocolate cake")
        add_to_cart(self.buyer, cake)
        order = create_order_from_cart(self.buyer, self.address)

        cake.name, cake.price_paise = "Renamed cake", 99900
        cake.save()

        item = OrderItem.objects.get(seller_order__order=order)
        self.assertEqual((item.name, item.unit_price), ("Chocolate cake", 45000))

    def test_holds_stock_at_checkout_but_keeps_the_cart_until_paid(self):
        cake = make_product(self.seller, stock=5)
        add_to_cart(self.buyer, cake, qty=2)
        order = create_order_from_cart(self.buyer, self.address)

        cake.refresh_from_db()
        self.assertEqual(cake.stock, 3)  # held for this buyer for 15 minutes
        self.assertTrue(order.stock_held)
        self.assertEqual(self.buyer.cart_items.count(), 1)  # cart is cleared only when paid

    def test_empty_cart_is_rejected(self):
        with self.assertRaises(CheckoutError):
            create_order_from_cart(self.buyer, self.address)
        self.assertEqual(Order.objects.count(), 0)

    def test_not_enough_stock_is_rejected_and_nothing_changes(self):
        fine = make_product(self.seller, stock=5, name="Plenty")
        last = make_product(self.seller, stock=1, name="Last cake")
        add_to_cart(self.buyer, fine, qty=1)
        add_to_cart(self.buyer, last, qty=2)

        with self.assertRaises(SoldOutError) as ctx:
            create_order_from_cart(self.buyer, self.address)

        self.assertEqual(ctx.exception.items, [{"product_id": last.id, "name": "Last cake"}])
        self.assertEqual(Order.objects.count(), 0)
        fine.refresh_from_db()
        self.assertEqual(fine.stock, 5)  # nothing was held: all or nothing

    def test_hidden_product_is_rejected(self):
        add_to_cart(self.buyer, make_product(self.seller, is_active=False))
        with self.assertRaises(SoldOutError):
            create_order_from_cart(self.buyer, self.address)

    def test_a_paused_store_stops_the_whole_checkout(self):
        add_to_cart(self.buyer, make_product(self.seller))
        add_to_cart(self.buyer, make_product(make_seller(is_active=False)))
        with self.assertRaises(CheckoutError):
            create_order_from_cart(self.buyer, self.address)
        self.assertEqual(Order.objects.count(), 0)

    def test_only_reads_this_buyers_cart(self):
        other = make_user()
        add_to_cart(other, make_product(self.seller))
        with self.assertRaises(CheckoutError):  # this buyer's own cart is empty
            create_order_from_cart(self.buyer, self.address)

    def test_trying_again_releases_the_buyers_earlier_unpaid_attempt(self):
        last = make_product(self.seller, stock=1)
        add_to_cart(self.buyer, last)
        first = create_order_from_cart(self.buyer, self.address)  # buyer closes the payment window…
        second = create_order_from_cart(self.buyer, self.address)  # …and clicks Pay again

        first.refresh_from_db()
        last.refresh_from_db()
        self.assertEqual(first.payment_status, Order.PaymentStatus.FAILED)
        self.assertFalse(first.stock_held)
        self.assertEqual(second.payment_status, Order.PaymentStatus.PENDING)
        self.assertEqual(last.stock, 0)  # held once, by the new attempt
