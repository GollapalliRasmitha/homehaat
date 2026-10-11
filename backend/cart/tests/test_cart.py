from django.test import TestCase
from rest_framework.test import APIClient

from cart.models import CartItem
from core.tests.factories import add_to_cart, make_product, make_seller, make_user


def lines(cart):
    """All items in the grouped bag, flattened."""
    return [item for group in cart["groups"] for item in group["items"]]


class CartApiTests(TestCase):
    def setUp(self):
        self.buyer = make_user()
        self.client = APIClient()
        self.client.force_authenticate(self.buyer)
        self.seller = make_seller(delivery_fee_paise=4000)

    def test_add_and_read_cart_with_totals_from_the_database(self):
        cake = make_product(self.seller, price_paise=45000, stock=5)
        res = self.client.post("/api/cart/items/", {"product_id": cake.id, "qty": 2, "price_paise": 1}, format="json")
        self.assertEqual(res.status_code, 201)

        cart = self.client.get("/api/cart/").data
        self.assertEqual(cart["items_total"], 90000)
        self.assertEqual(cart["delivery_total"], 4000)
        self.assertEqual(cart["grand_total"], 94000)

    def test_bag_is_grouped_by_seller_with_one_delivery_fee_each(self):
        pickler = make_seller(delivery_fee_paise=3000)
        add_to_cart(self.buyer, make_product(self.seller, price_paise=45000), qty=1)
        add_to_cart(self.buyer, make_product(self.seller, price_paise=5000), qty=2)
        add_to_cart(self.buyer, make_product(pickler, price_paise=12000), qty=1)

        cart = self.client.get("/api/cart/").data

        self.assertEqual(len(cart["groups"]), 2)
        baker_group, pickle_group = cart["groups"]
        self.assertEqual(baker_group["seller"]["slug"], self.seller.slug)
        self.assertEqual((baker_group["items_total"], baker_group["delivery_fee"]), (55000, 4000))
        self.assertEqual(baker_group["subtotal"], 59000)
        self.assertEqual((pickle_group["items_total"], pickle_group["delivery_fee"]), (12000, 3000))
        self.assertEqual(cart["delivery_total"], 7000)
        self.assertEqual(cart["grand_total"], 67000 + 7000)
        self.assertEqual(cart["count"], 4)

    def test_adding_the_same_product_again_increases_quantity(self):
        cake = make_product(self.seller, stock=5)
        self.client.post("/api/cart/items/", {"product_id": cake.id, "qty": 1}, format="json")
        self.client.post("/api/cart/items/", {"product_id": cake.id, "qty": 2}, format="json")
        self.assertEqual(lines(self.client.get("/api/cart/").data)[0]["qty"], 3)

    def test_cannot_add_more_than_stock(self):
        cake = make_product(self.seller, stock=2)
        res = self.client.post("/api/cart/items/", {"product_id": cake.id, "qty": 3}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_items_from_several_sellers_can_share_a_bag(self):
        self.client.post("/api/cart/items/", {"product_id": make_product(self.seller).id, "qty": 1}, format="json")
        res = self.client.post("/api/cart/items/", {"product_id": make_product().id, "qty": 1}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(len(res.data["groups"]), 2)

    def test_items_that_sold_out_are_flagged(self):
        gone = make_product(self.seller, stock=0, name="Gone")
        short = make_product(self.seller, stock=1, name="Short")
        hidden = make_product(self.seller, stock=5, is_active=False, name="Hidden")
        fine = make_product(self.seller, stock=5, name="Fine")
        for product, qty in [(gone, 1), (short, 3), (hidden, 1), (fine, 1)]:
            add_to_cart(self.buyer, product, qty=qty)

        cart = self.client.get("/api/cart/").data
        problems = {item["product"]["name"]: item["problem"] for item in lines(cart)}

        self.assertEqual(problems, {"Gone": "sold_out", "Short": "not_enough", "Hidden": "unavailable", "Fine": None})
        self.assertTrue(cart["has_problems"])

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
        self.assertEqual(self.client.get("/api/cart/").data["groups"], [])


class GuestBagTests(TestCase):
    """Guests keep their bag in the browser. The server prices it, and merges it on sign-in."""

    def setUp(self):
        self.seller = make_seller(delivery_fee_paise=4000)
        self.cake = make_product(self.seller, price_paise=45000, stock=5)

    def test_preview_prices_a_guest_bag_from_the_database(self):
        body = {"items": [{"product_id": self.cake.id, "qty": 2, "price_paise": 1}, {"product_id": 999999, "qty": 1}]}
        res = APIClient().post("/api/cart/preview/", body, format="json")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["grand_total"], 2 * 45000 + 4000)  # unknown product id is dropped
        self.assertEqual(lines(res.data)[0]["id"], None)  # nothing saved for guests

    def test_merge_on_sign_in_adds_quantities_and_caps_at_stock(self):
        buyer = make_user()
        add_to_cart(buyer, self.cake, qty=4)
        jar = make_product(make_seller(), stock=3, name="Jar")
        client = APIClient()
        client.force_authenticate(buyer)

        res = client.post(
            "/api/cart/merge/",
            {"items": [{"product_id": self.cake.id, "qty": 3}, {"product_id": jar.id, "qty": 1, "note": "Less oil"}]},
            format="json",
        )

        self.assertEqual(res.status_code, 200)
        qty = dict(CartItem.objects.filter(user=buyer).values_list("product__name", "qty"))
        self.assertEqual(qty[self.cake.name], 5)  # 4 + 3, capped at stock 5
        self.assertEqual(qty["Jar"], 1)
        self.assertEqual(CartItem.objects.get(user=buyer, product=jar).note, "Less oil")

    def test_merge_skips_your_own_products(self):
        client = APIClient()
        client.force_authenticate(self.seller.owner)
        res = client.post("/api/cart/merge/", {"items": [{"product_id": self.cake.id, "qty": 1}]}, format="json")
        self.assertEqual(res.data["skipped"], [self.cake.name])
        self.assertFalse(CartItem.objects.filter(user=self.seller.owner).exists())

    def test_merge_needs_sign_in(self):
        res = APIClient().post("/api/cart/merge/", {"items": []}, format="json")
        self.assertEqual(res.status_code, 403)
