"""Seller product controls: out of stock / back in stock, delete (or archive when ordered), and who may do it."""

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from cart.models import CartItem
from catalog.models import Product
from core.tests.factories import add_to_cart, make_category, make_paid_order, make_product, make_seller, make_user


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


class StockControlTests(TestCase):
    def setUp(self):
        self.seller = make_seller(main_category=make_category())
        self.product = make_product(self.seller, stock=4)
        self.me = client_for(self.seller.owner)
        self.url = f"/api/seller/products/{self.product.id}/"

    def test_mark_out_of_stock_then_back_in_stock(self):
        self.assertEqual(self.me.patch(self.url, {"stock": 0}, format="json").status_code, 200)
        page = APIClient().get(f"/api/products/{self.product.id}/").json()
        self.assertEqual(page["stock"], 0)  # buyers see "Sold out"

        buyer = make_user()
        res = client_for(buyer).post("/api/cart/items/", {"product_id": self.product.id, "qty": 1}, format="json")
        self.assertEqual(res.status_code, 400)  # can't add a sold-out product

        self.assertEqual(self.me.patch(self.url, {"stock": 6}, format="json").json()["stock"], 6)

    def test_bag_items_are_flagged_when_it_goes_out_of_stock(self):
        buyer = make_user()
        add_to_cart(buyer, self.product)
        self.me.patch(self.url, {"stock": 0}, format="json")
        cart = client_for(buyer).get("/api/cart/").json()
        self.assertEqual(cart["groups"][0]["items"][0]["problem"], "sold_out")
        self.assertTrue(cart["has_problems"])

    def test_stock_cannot_be_negative(self):
        self.assertEqual(self.me.patch(self.url, {"stock": -1}, format="json").status_code, 400)

    def test_overview_counts_out_of_stock_products(self):
        make_product(self.seller, stock=0)
        make_product(self.seller, stock=0, is_active=False)  # hidden: not "listed", not counted
        data = self.me.get("/api/seller/overview/").json()
        self.assertEqual((data["products_listed"], data["out_of_stock"]), (2, 1))


class DeleteTests(TestCase):
    def setUp(self):
        self.seller = make_seller(main_category=make_category())
        self.me = client_for(self.seller.owner)

    def test_a_never_ordered_product_is_deleted_fully(self):
        product = make_product(self.seller)
        listed = self.me.get("/api/seller/products/").json()[0]
        self.assertEqual(listed["past_orders"], 0)
        res = self.me.delete(f"/api/seller/products/{product.id}/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"result": "deleted", "past_orders": 0})
        self.assertFalse(Product.objects.filter(pk=product.id).exists())

    def test_an_ordered_product_is_archived_and_order_history_keeps_it(self):
        product = make_product(self.seller, name="Plum cake", stock=5)
        part = make_paid_order(product)
        make_paid_order(product)
        other_buyer = make_user()
        add_to_cart(other_buyer, product)
        self.assertEqual(self.me.get("/api/seller/products/").json()[0]["past_orders"], 2)

        res = self.me.delete(f"/api/seller/products/{product.id}/")
        self.assertEqual(res.json(), {"result": "archived", "past_orders": 2})
        product.refresh_from_db()
        self.assertTrue(product.is_archived)
        self.assertFalse(product.is_active)
        # gone from the shop, search and the seller's own list…
        self.assertEqual(self.me.get("/api/seller/products/").json(), [])
        self.assertEqual(APIClient().get(f"/api/products/{product.id}/").status_code, 404)
        self.assertEqual(APIClient().get("/api/search/?q=plum").json()["count"], 0)
        # …and it can't be edited back to life
        self.assertEqual(
            self.me.patch(f"/api/seller/products/{product.id}/", {"is_active": True}, format="json").status_code, 404
        )
        # but the past order still shows it
        order = client_for(part.order.buyer).get(f"/api/orders/{part.order_id}/").json()
        self.assertEqual(order["seller_orders"][0]["items"][0]["name"], "Plum cake")
        # and it's taken out of other buyers' bags (it can never be bought again)
        cart = client_for(other_buyer).get("/api/cart/").json()
        self.assertEqual(cart["groups"], [])
        self.assertFalse(CartItem.objects.filter(product=product).exists())

    def test_overview_does_not_count_archived_products(self):
        product = make_product(self.seller)
        make_paid_order(product)
        self.me.delete(f"/api/seller/products/{product.id}/")
        self.assertEqual(self.me.get("/api/seller/overview/").json()["products_listed"], 0)


class OwnerOnlyTests(TestCase):
    """Only the owner can change their products or orders."""

    def setUp(self):
        self.seller = make_seller(main_category=make_category())
        self.product = make_product(self.seller, stock=3)
        self.part = make_paid_order(self.product)
        self.url = f"/api/seller/products/{self.product.id}/"

    def test_another_seller_cannot_change_stock_hide_or_delete(self):
        other = client_for(make_seller().owner)
        self.assertEqual(other.patch(self.url, {"stock": 0}, format="json").status_code, 404)
        self.assertEqual(other.patch(self.url, {"is_active": False}, format="json").status_code, 404)
        self.assertEqual(other.delete(self.url).status_code, 404)
        self.assertEqual(
            other.post(
                f"/api/seller/orders/{self.part.id}/status/", {"status": "preparing"}, format="json"
            ).status_code,
            404,
        )
        self.product.refresh_from_db()
        self.assertEqual((self.product.stock, self.product.is_active, self.product.is_archived), (2, True, False))

    def test_buyers_and_signed_out_visitors_cannot(self):
        buyer = client_for(make_user(role=User.Role.BUYER))
        self.assertEqual(buyer.patch(self.url, {"stock": 0}, format="json").status_code, 403)
        self.assertEqual(buyer.delete(self.url).status_code, 403)
        self.assertIn(APIClient().delete(self.url).status_code, (401, 403))
        self.assertTrue(Product.objects.filter(pk=self.product.id).exists())

    def test_custom_request_products_cannot_be_deleted_from_the_product_list(self):
        custom = make_product(self.seller, is_custom=True)
        res = client_for(self.seller.owner).delete(f"/api/seller/products/{custom.id}/")
        self.assertEqual(res.status_code, 404)


class AccountMenuTests(TestCase):
    def test_me_has_the_shop_name_and_open_orders_for_the_menu(self):
        seller = make_seller(name="Ammu's Kitchen", main_category=make_category())
        make_paid_order(make_product(seller))
        me = client_for(seller.owner).get("/api/auth/me/").json()["user"]
        self.assertEqual((me["shop_name"], me["open_orders"]), ("Ammu's Kitchen", 1))
        buyer = client_for(make_user()).get("/api/auth/me/").json()["user"]
        self.assertEqual((buyer["shop_name"], buyer["open_orders"]), (None, 0))
