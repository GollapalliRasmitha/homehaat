from django.test import TestCase
from rest_framework.test import APIClient

from core.tests.factories import add_to_cart, make_product, make_seller, make_user


class CartApiTests(TestCase):
    def setUp(self):
        self.buyer = make_user()
        self.client = APIClient()
        self.client.force_authenticate(self.buyer)
        self.seller = make_seller()

    def test_add_and_read_cart_with_totals_from_the_database(self):
        cake = make_product(self.seller, price_paise=45000, stock=5)
        res = self.client.post("/api/cart/items/", {"product_id": cake.id, "qty": 2, "price_paise": 1}, format="json")
        self.assertEqual(res.status_code, 201)

        cart = self.client.get("/api/cart/").data
        self.assertEqual(cart["items_total"], 90000)
        self.assertEqual(cart["delivery_total"], self.seller.delivery_fee_paise)
        self.assertEqual(cart["grand_total"], 90000 + self.seller.delivery_fee_paise)

    def test_adding_the_same_product_again_increases_quantity(self):
        cake = make_product(self.seller, stock=5)
        self.client.post("/api/cart/items/", {"product_id": cake.id, "qty": 1}, format="json")
        self.client.post("/api/cart/items/", {"product_id": cake.id, "qty": 2}, format="json")
        self.assertEqual(self.client.get("/api/cart/").data["items"][0]["qty"], 3)

    def test_cannot_add_more_than_stock(self):
        cake = make_product(self.seller, stock=2)
        res = self.client.post("/api/cart/items/", {"product_id": cake.id, "qty": 3}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_stage_1_bag_holds_one_seller_only(self):
        self.client.post("/api/cart/items/", {"product_id": make_product(self.seller).id, "qty": 1}, format="json")
        res = self.client.post("/api/cart/items/", {"product_id": make_product().id, "qty": 1}, format="json")
        self.assertEqual(res.status_code, 409)

    def test_sellers_cannot_buy_their_own_products(self):
        own = make_product(self.seller)
        client = APIClient()
        client.force_authenticate(self.seller.owner)
        res = client.post("/api/cart/items/", {"product_id": own.id, "qty": 1}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_buyer_a_cannot_change_buyer_b_cart(self):
        other = make_user()
        item = add_to_cart(other, make_product(self.seller))
        self.assertEqual(self.client.patch(f"/api/cart/items/{item.id}/", {"qty": 5}, format="json").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/cart/items/{item.id}/").status_code, 404)
        self.assertEqual(self.client.get("/api/cart/").data["items"], [])
