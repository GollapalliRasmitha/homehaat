"""Store settings, products (edit, active toggle) and product photos."""

import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import User
from catalog.models import Product, ProductImage, Seller
from core.tests.factories import make_category, make_product, make_seller, make_user

MEDIA = tempfile.mkdtemp(prefix="homehaat-test-media-")


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def jpeg(name="photo.jpg", size=(400, 300), with_gps=False) -> SimpleUploadedFile:
    """A real JPEG. with_gps adds an EXIF location tag, like a phone photo."""
    buffer = io.BytesIO()
    image = Image.new("RGB", size, (200, 120, 80))
    exif = Image.Exif()
    if with_gps:
        exif[0x8825] = {1: "N", 2: (12.0, 58.0, 0.0)}  # GPSInfo: latitude of Bengaluru
    image.save(buffer, "JPEG", exif=exif)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


class StoreSettingsTests(TestCase):
    def setUp(self):
        make_category("cakes")
        self.user = make_user()
        self.client = client_for(self.user)

    def test_open_shop_with_my_own_shop_link(self):
        res = self.client.post("/api/seller/store/", {"name": "Asha's Kitchen", "slug": "asha-bakes"}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["slug"], "asha-bakes")

    def test_shop_link_must_be_unique_and_well_formed(self):
        make_seller(slug="taken")
        taken = self.client.post("/api/seller/store/", {"name": "X", "slug": "taken"}, format="json")
        self.assertEqual(taken.status_code, 400)
        self.assertIn("slug", taken.data)
        bad = self.client.post("/api/seller/store/", {"name": "X", "slug": "Has Spaces!"}, format="json")
        self.assertEqual(bad.status_code, 400)

    def test_edit_settings_and_pause_the_store(self):
        self.client.post("/api/seller/store/", {"name": "Mine"}, format="json")
        res = self.client.patch(
            "/api/seller/store/",
            {"name": "Mine renamed", "slug": "mine-renamed", "delivery_fee_paise": 5000, "is_active": False},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        store = Seller.objects.get(owner=self.user)
        self.assertEqual((store.name, store.slug, store.delivery_fee_paise), ("Mine renamed", "mine-renamed", 5000))
        self.assertFalse(store.is_active)

    def test_keeping_my_own_slug_is_fine(self):
        self.client.post("/api/seller/store/", {"name": "Mine", "slug": "mine"}, format="json")
        res = self.client.patch("/api/seller/store/", {"slug": "mine", "bio": "Hello"}, format="json")
        self.assertEqual(res.status_code, 200)

    def test_a_paused_store_disappears_for_buyers(self):
        self.client.post("/api/seller/store/", {"name": "Mine"}, format="json")
        product = make_product(self.user.seller)
        self.client.patch("/api/seller/store/", {"is_active": False}, format="json")
        self.assertEqual(APIClient().get(f"/api/products/{product.id}/").status_code, 404)

    def test_settings_cannot_change_my_role_or_owner(self):
        self.client.post("/api/seller/store/", {"name": "Mine"}, format="json")
        other = make_user()
        self.client.patch("/api/seller/store/", {"owner": other.id, "role": "admin"}, format="json")
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, User.Role.SELLER)
        self.assertEqual(Seller.objects.get(slug=self.user.seller.slug).owner, self.user)


@override_settings(MEDIA_ROOT=MEDIA)
class ProductPhotoTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.seller = make_seller()
        self.product = make_product(self.seller)
        self.client = client_for(self.seller.owner)
        self.url = f"/api/seller/products/{self.product.id}/images/"

    def upload(self, file, client=None):
        return (client or self.client).post(self.url, {"image": file}, format="multipart")

    def test_upload_a_photo_and_it_shows_on_the_product(self):
        res = self.upload(jpeg())
        self.assertEqual(res.status_code, 201)
        public = APIClient().get(f"/api/products/{self.product.id}/").data
        self.assertTrue(public["image"].startswith("/media/products/"))
        self.assertEqual(len(public["images"]), 1)

    def test_location_data_is_removed_from_photos(self):
        self.upload(jpeg(with_gps=True))
        saved = ProductImage.objects.get(product=self.product)
        with Image.open(saved.image.path) as image:
            self.assertNotIn(0x8825, image.getexif())  # no GPS tag left

    def test_large_photos_are_resized(self):
        self.upload(jpeg(size=(4000, 3000)))
        with Image.open(ProductImage.objects.get().image.path) as image:
            self.assertLessEqual(max(image.size), 1600)

    def test_only_real_images_are_accepted(self):
        fake = SimpleUploadedFile("evil.jpg", b"<script>alert(1)</script>", content_type="image/jpeg")
        self.assertEqual(self.upload(fake).status_code, 400)
        gif = io.BytesIO()
        Image.new("RGB", (10, 10)).save(gif, "GIF")
        self.assertEqual(self.upload(SimpleUploadedFile("a.gif", gif.getvalue(), "image/gif")).status_code, 400)

    def test_photos_over_5_mb_are_refused(self):
        big = SimpleUploadedFile("big.jpg", b"0" * (5 * 1024 * 1024 + 1), content_type="image/jpeg")
        res = self.upload(big)
        self.assertEqual(res.status_code, 400)

    def test_at_most_five_photos(self):
        for _ in range(5):
            self.assertEqual(self.upload(jpeg()).status_code, 201)
        self.assertEqual(self.upload(jpeg()).status_code, 400)

    def test_reorder_and_delete(self):
        ids = [self.upload(jpeg()).data["id"] for _ in range(3)]
        res = self.client.post(f"{self.url}order/", {"ids": list(reversed(ids))}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual([img["id"] for img in res.data], list(reversed(ids)))

        self.assertEqual(self.client.delete(f"{self.url}{ids[0]}/").status_code, 204)
        self.assertEqual(ProductImage.objects.filter(product=self.product).count(), 2)

    def test_seller_a_cannot_touch_seller_b_photos_or_products(self):
        intruder = client_for(make_seller().owner)
        self.assertEqual(self.upload(jpeg(), client=intruder).status_code, 404)
        own = self.upload(jpeg()).data["id"]
        self.assertEqual(intruder.delete(f"{self.url}{own}/").status_code, 404)
        res = intruder.patch(f"/api/seller/products/{self.product.id}/", {"price_paise": 100}, format="json")
        self.assertEqual(res.status_code, 404)
        self.product.refresh_from_db()
        self.assertNotEqual(self.product.price_paise, 100)


class ProductEditTests(TestCase):
    def setUp(self):
        self.seller = make_seller()
        self.product = make_product(self.seller, price_paise=45000, stock=3)
        self.client = client_for(self.seller.owner)

    def test_edit_price_stock_and_hide(self):
        res = self.client.patch(
            f"/api/seller/products/{self.product.id}/",
            {"price_paise": 50000, "stock": 7, "is_active": False},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual((self.product.price_paise, self.product.stock, self.product.is_active), (50000, 7, False))

    def test_seller_product_list_includes_the_first_photo_and_sold_count(self):
        data = self.client.get("/api/seller/products/").data
        self.assertIn("image", data[0])
        self.assertEqual(data[0]["sold"], 0)

    def test_cannot_move_a_product_to_another_seller(self):
        other = make_seller()
        self.client.patch(f"/api/seller/products/{self.product.id}/", {"seller": other.id}, format="json")
        self.assertEqual(Product.objects.get(pk=self.product.pk).seller, self.seller)
