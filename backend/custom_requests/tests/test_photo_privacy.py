"""Custom request photos: only that buyer and that seller can ever see them (Stage 7)."""

import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from core.tests.factories import make_category, make_seller, make_user

MEDIA = tempfile.mkdtemp(prefix="e2e-media-test-")  # never the real uploads folder


def jpeg():
    buffer = io.BytesIO()
    Image.new("RGB", (200, 200), "navy").save(buffer, "JPEG")
    return SimpleUploadedFile("dog.jpg", buffer.getvalue(), content_type="image/jpeg")


def client_for(user=None):
    c = APIClient()
    if user:
        c.force_login(user)  # a real session cookie, like the browser sends (the photo view is a plain Django view)
    return c


def fetch(client, url):
    """The browser asks Next.js for the URL; Next.js adds the trailing slash Django needs (next.config.ts)."""
    return client.get(url + "/" if url.startswith("/api/") else url)


@override_settings(MEDIA_ROOT=MEDIA)
class RequestPhotoPrivacyTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.shop = make_seller(main_category=make_category("cakes"), slug="ammus-kitchen")
        self.buyer = make_user()
        self.mine = client_for(self.buyer)
        r = self.mine.post(
            "/api/requests/",
            {"seller": "ammus-kitchen", "description": "A cake with a photo of our dog on top, please."},
            format="json",
        )
        self.request_id = r.json()["id"]
        self.mine.post(f"/api/requests/{self.request_id}/images/", {"image": jpeg()}, format="multipart")
        self.url = self.mine.get(f"/api/requests/{self.request_id}/").json()["images"][0]

    def test_photo_urls_go_through_the_private_route(self):
        self.assertTrue(self.url.startswith("/api/private-media/requests/"), self.url)

    def test_the_buyer_and_that_seller_can_see_it(self):
        for who in (self.buyer, self.shop.owner):
            r = fetch(client_for(who), self.url)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r["Content-Type"], "image/jpeg")
            self.assertIn("private", r["Cache-Control"])  # never stored by shared caches

    def test_everyone_else_gets_404(self):
        for who in (None, make_user(), make_seller().owner):
            self.assertEqual(fetch(client_for(who), self.url).status_code, 404, who)

    def test_the_old_public_media_path_is_closed(self):
        name = self.url.removeprefix("/api/private-media/")
        for who in (None, self.buyer, self.shop.owner):
            self.assertEqual(client_for(who).get(f"/media/{name}").status_code, 404)

    def test_tricks_in_the_file_name_are_refused(self):
        for bad in ("..%2F..%2Fconfig%2Fsettings.py", "nope.jpg", "x.exe"):
            self.assertEqual(client_for(self.buyer).get(f"/api/private-media/requests/{bad}/").status_code, 404)

    def test_the_accepted_custom_item_picture_follows_the_same_rule(self):
        seller = client_for(self.shop.owner)
        seller.post(f"/api/seller/requests/{self.request_id}/quote/", {"quote_paise": 150000}, format="json")
        self.mine.post(f"/api/requests/{self.request_id}/accept/")
        line = self.mine.get("/api/cart/").json()["groups"][0]["items"][0]
        image = line["product"]["image"]
        self.assertTrue(image.startswith("/api/private-media/requests/"), image)
        self.assertEqual(fetch(self.mine, image).status_code, 200)
        self.assertEqual(fetch(client_for(make_user()), image).status_code, 404)

    def test_ordinary_product_photos_stay_public(self):
        from catalog.models import Product, ProductImage

        product = Product.objects.create(
            seller=self.shop, category=self.shop.main_category, name="Plum cake", price_paise=30000, stock=2
        )
        ProductImage.objects.create(product=product, image=jpeg(), position=0)
        image = client_for().get(f"/api/products/{product.id}/").json()["image"]
        self.assertTrue(image.startswith("/media/products/"), image)
        self.assertEqual(client_for().get(image).status_code, 200)
