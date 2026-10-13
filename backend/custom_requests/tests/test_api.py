"""Custom requests over HTTP: create, photos, lists, quote / accept / decline, permissions."""

import io
import shutil
import tempfile
from datetime import date, timedelta

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from cart.models import CartItem
from core.tests.factories import make_category, make_seller, make_user
from custom_requests.models import CustomRequest

MEDIA = tempfile.mkdtemp(prefix="homehaat-test-requests-")


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def jpeg() -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new("RGB", (300, 300), (120, 80, 60)).save(buffer, "JPEG")
    return SimpleUploadedFile("ref.jpg", buffer.getvalue(), content_type="image/jpeg")


@override_settings(MEDIA_ROOT=MEDIA)
class CustomRequestApiTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        cache.clear()  # reset the request rate limit
        self.seller = make_seller(name="Asha Bakes", main_category=make_category("cakes"))
        self.buyer = make_user(name="Ravi Kumar")
        self.client = client_for(self.buyer)
        self.body = {
            "seller": self.seller.slug,
            "description": "A two-tier cake for my parents' 25th anniversary, white and gold.",
            "needed_by": str(date.today() + timedelta(days=5)),
            "budget_paise": 200000,
        }

    def create(self, **changes):
        return self.client.post("/api/requests/", {**self.body, **changes}, format="json")

    def test_create_a_request(self):
        res = self.create()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["status"], "open")
        self.assertEqual(res.data["seller"]["slug"], self.seller.slug)

    def test_validation(self):
        self.assertIn("description", self.create(description="cake").data)  # too short to quote on
        self.assertIn("needed_by", self.create(needed_by=str(date.today() - timedelta(days=1))).data)
        self.assertEqual(self.create(budget_paise=None).status_code, 201)  # budget is optional
        self.assertEqual(self.create(seller="no-such-shop").status_code, 400)

    def test_cannot_ask_your_own_shop_or_a_paused_one(self):
        own = client_for(self.seller.owner).post("/api/requests/", self.body, format="json")
        self.assertEqual(own.status_code, 400)
        paused = make_seller(is_active=False)
        self.assertEqual(self.create(seller=paused.slug).status_code, 400)

    def test_up_to_three_reference_photos_while_open(self):
        rid = self.create().data["id"]
        for _ in range(3):
            res = self.client.post(f"/api/requests/{rid}/images/", {"image": jpeg()}, format="multipart")
            self.assertEqual(res.status_code, 201)
        self.assertEqual(
            self.client.post(f"/api/requests/{rid}/images/", {"image": jpeg()}, format="multipart").status_code, 400
        )
        data = self.client.get(f"/api/requests/{rid}/").data
        self.assertEqual(len(data["images"]), 3)

    def test_buyers_and_sellers_see_only_their_own(self):
        rid = self.create().data["id"]
        stranger = client_for(make_user())
        self.assertEqual(stranger.get("/api/requests/").data, [])
        self.assertEqual(stranger.get(f"/api/requests/{rid}/").status_code, 404)
        other_seller = client_for(make_seller().owner)
        self.assertEqual(other_seller.get("/api/seller/requests/").data, [])
        mine = client_for(self.seller.owner).get("/api/seller/requests/").data
        self.assertEqual([r["id"] for r in mine], [rid])
        self.assertEqual(mine[0]["buyer_name"], "Ravi")  # first name only
        self.assertNotIn("buyer", mine[0])

    def test_quote_accept_flow_over_http(self):
        rid = self.create().data["id"]
        seller = client_for(self.seller.owner)
        res = seller.post(
            f"/api/seller/requests/{rid}/quote/", {"quote_paise": 180000, "note": "Gold leaf included"}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "quoted")

        res = self.client.post(f"/api/requests/{rid}/accept/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "accepted")
        self.assertTrue(res.data["in_bag"])
        line = self.client.get("/api/cart/").data["groups"][0]["items"][0]
        self.assertEqual((line["product"]["price_paise"], line["qty"]), (180000, 1))

    def test_a_price_in_the_accept_request_is_ignored(self):
        rid = self.create().data["id"]
        client_for(self.seller.owner).post(f"/api/seller/requests/{rid}/quote/", {"quote_paise": 180000}, format="json")
        self.client.post(f"/api/requests/{rid}/accept/", {"quote_paise": 100, "price_paise": 100}, format="json")
        self.assertEqual(CartItem.objects.get(user=self.buyer).product.price_paise, 180000)

    def test_wrong_side_and_wrong_step_give_clear_errors(self):
        rid = self.create().data["id"]
        res = self.client.post(f"/api/requests/{rid}/accept/")  # no quote yet
        self.assertEqual(res.status_code, 400)
        self.assertIn("detail", res.data)
        buyer_quoting = self.client.post(f"/api/seller/requests/{rid}/quote/", {"quote_paise": 100}, format="json")
        self.assertEqual(buyer_quoting.status_code, 403)  # not a seller at all
        other_shop = client_for(make_seller().owner).post(
            f"/api/seller/requests/{rid}/quote/", {"quote_paise": 9000}, format="json"
        )
        self.assertEqual(other_shop.status_code, 404)
        self.assertEqual(CustomRequest.objects.get(pk=rid).status, "open")

    def test_buyer_declines_a_quote_and_seller_declines_an_open_request(self):
        rid = self.create().data["id"]
        client_for(self.seller.owner).post(f"/api/seller/requests/{rid}/quote/", {"quote_paise": 9000}, format="json")
        self.assertEqual(self.client.post(f"/api/requests/{rid}/decline/").data["status"], "declined")
        rid2 = self.create().data["id"]
        self.assertEqual(
            client_for(self.seller.owner).post(f"/api/seller/requests/{rid2}/decline/").data["status"], "declined"
        )

    def test_requests_are_rate_limited(self):
        statuses = [self.create().status_code for _ in range(12)]
        self.assertIn(429, statuses)

    def test_overview_counts_open_requests(self):
        self.create()
        self.assertEqual(client_for(self.seller.owner).get("/api/seller/overview/").data["open_requests"], 1)
