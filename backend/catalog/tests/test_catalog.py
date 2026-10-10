from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from catalog.models import Category, Product
from core.tests.factories import make_category, make_product, make_seller, make_user


class SeedCategoriesTests(TestCase):
    def test_creates_eight_categories_and_is_safe_to_run_again(self):
        call_command("seed_categories", stdout=StringIO())
        call_command("seed_categories", stdout=StringIO())
        self.assertEqual(Category.objects.count(), 8)


class PublicProductTests(TestCase):
    def test_lists_only_active_products_from_open_stores(self):
        live = make_product(name="Live")
        make_product(name="Hidden", is_active=False)
        make_product(seller=make_seller(is_active=False), name="Paused shop")

        res = APIClient().get("/api/products/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual([p["id"] for p in res.data], [live.id])
        self.assertEqual(res.data[0]["price_paise"], live.price_paise)

    def test_hidden_product_page_is_not_found(self):
        hidden = make_product(is_active=False)
        self.assertEqual(APIClient().get(f"/api/products/{hidden.id}/").status_code, 404)


class OpenShopTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        make_category("cakes")

    def test_opening_a_shop_makes_you_a_seller(self):
        res = self.client.post(
            "/api/seller/store/",
            {
                "name": "Asha's Kitchen",
                "kind": "home_baker",
                "area": "Indiranagar",
                "delivery_days": 1,
                "delivery_fee_paise": 4000,
                "role": "admin",
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["slug"], "ashas-kitchen")
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, User.Role.SELLER)

    def test_slugs_stay_unique(self):
        other = make_user()
        other_client = APIClient()
        other_client.force_authenticate(other)
        other_client.post("/api/seller/store/", {"name": "Asha's Kitchen"}, format="json")
        res = self.client.post("/api/seller/store/", {"name": "Asha's Kitchen"}, format="json")
        self.assertEqual(res.data["slug"], "ashas-kitchen-2")

    def test_seller_adds_a_product_and_cannot_set_another_sellers_id(self):
        self.client.post("/api/seller/store/", {"name": "Mine"}, format="json")
        someone_else = make_seller()
        res = self.client.post(
            "/api/seller/products/",
            {"name": "Cake", "category": "cakes", "price_paise": 45000, "stock": 3, "seller": someone_else.id},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Product.objects.get(name="Cake").seller.owner, self.user)

    def test_seller_a_cannot_see_seller_b_products(self):
        self.client.post("/api/seller/store/", {"name": "Mine"}, format="json")
        make_product(name="Not mine")
        self.assertEqual(self.client.get("/api/seller/products/").data, [])

    def test_a_buyer_without_a_store_cannot_add_products(self):
        buyer = APIClient()
        buyer.force_authenticate(make_user())
        body = {"name": "x", "category": "cakes", "price_paise": 100, "stock": 1}
        self.assertEqual(buyer.post("/api/seller/products/", body, format="json").status_code, 403)
