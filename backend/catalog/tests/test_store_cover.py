"""Store cover fallback: no cover photo -> the category the shop sells most in, then its main category."""

from django.test import TestCase
from rest_framework.test import APIClient

from core.tests.factories import make_category, make_product, make_seller, make_user


def store(slug):
    return APIClient().get(f"/api/stores/{slug}/").json()


class OpenShopNeedsAMainCategoryTests(TestCase):
    def test_main_category_is_required_when_opening_a_shop(self):
        make_category("cakes")
        client = APIClient()
        client.force_authenticate(make_user())
        res = client.post("/api/seller/store/", {"name": "Meera Paints"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(str(res.json()["main_category"][0]), "Please choose your main category.")
        res = client.post("/api/seller/store/", {"name": "Meera Paints", "main_category": "cakes"}, format="json")
        self.assertEqual(res.status_code, 201)


class CoverCategoryTests(TestCase):
    def setUp(self):
        self.cakes, self.art, self.crafts = make_category("cakes"), make_category("art"), make_category("crafts")
        self.shop = make_seller(main_category=self.cakes, slug="meera-paints")  # the old default: cakes

    def test_the_category_with_most_live_products_wins(self):
        # The art shop that showed a cake photo: it really sells art.
        for _ in range(3):
            make_product(self.shop, category=self.art)
        make_product(self.shop, category=self.crafts)
        self.assertEqual(store("meera-paints")["cover_category"]["slug"], "art")

    def test_hidden_archived_and_custom_products_dont_count(self):
        make_product(self.shop, category=self.crafts)
        for extra in ({"is_active": False}, {"is_archived": True, "is_active": False}, {"is_custom": True}):
            make_product(self.shop, category=self.art, **extra)
            make_product(self.shop, category=self.art, **extra)
        self.assertEqual(store("meera-paints")["cover_category"]["slug"], "crafts")

    def test_no_live_products_falls_back_to_the_main_category(self):
        self.assertEqual(store("meera-paints")["cover_category"]["slug"], "cakes")
        self.shop.main_category = None
        self.shop.save()
        self.assertIsNone(store("meera-paints")["cover_category"])

    def test_the_makers_list_has_it_too_without_extra_queries_per_shop(self):
        make_product(self.shop, category=self.art)
        for i in range(5):
            other = make_seller(main_category=self.cakes, slug=f"shop-x{i}")
            make_product(other, category=self.crafts)
        with self.assertNumQueries(2):  # the stores, plus one for the categories
            stores = APIClient().get("/api/stores/").json()
        covers = {s["slug"]: s["cover_category"]["slug"] for s in stores}
        self.assertEqual(covers["meera-paints"], "art")
        self.assertEqual(covers["shop-x0"], "crafts")
