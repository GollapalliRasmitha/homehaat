"""seed_showcase only creates the demo shops: twice is the same as once, and nothing existing is ever changed."""

import shutil
import tempfile
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from accounts.models import User
from catalog.management.commands.seed_categories import CATEGORIES
from catalog.models import Category, Product, ProductImage, Seller
from catalog.showcase_data import DEMO_NOTE, SHOPS, owner_email
from core.tests.factories import make_paid_order, make_product, make_seller, make_user
from orders.models import Order, Refund, SellerOrder

MEDIA = tempfile.mkdtemp(prefix="homehaat-test-media-")
N_SHOPS = len(SHOPS)
N_PRODUCTS = sum(len(shop[10]) for shop in SHOPS)


@override_settings(MEDIA_ROOT=MEDIA)
class SeedShowcaseTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA, ignore_errors=True)  # this test's own temporary folder
        super().tearDownClass()

    def setUp(self):
        call_command("seed_categories", stdout=StringIO())

    def seed(self):
        out = StringIO()
        call_command("seed_showcase", stdout=out)
        return out.getvalue()

    def test_creates_every_shop_and_product_with_a_photo(self):
        out = self.seed()
        self.assertIn(f"{N_SHOPS} shop(s) and {N_PRODUCTS} product(s) created", out)
        self.assertEqual(Seller.objects.count(), N_SHOPS)
        self.assertEqual(Product.objects.count(), N_PRODUCTS)
        self.assertEqual(ProductImage.objects.count(), N_PRODUCTS)
        # Exactly one product is sold out, on purpose.
        self.assertEqual(list(Product.objects.filter(stock=0).values_list("name", flat=True)), ["Banana walnut loaf"])
        for seller in Seller.objects.all():
            self.assertTrue(seller.bio.startswith(DEMO_NOTE))
            self.assertTrue(seller.is_active)

    def test_photos_are_cleaned_like_a_seller_upload(self):
        self.seed()
        image = ProductImage.objects.first().image
        self.assertRegex(image.name, r"^products/[0-9a-f]{32}\.jpg$")  # random name, as clean_image makes
        from PIL import Image

        with Image.open(image.path) as im:
            self.assertLessEqual(max(im.size), 1600)
            self.assertFalse(im.getexif())  # no EXIF (no location) kept

    def test_nobody_can_sign_in_as_a_demo_owner(self):
        self.seed()
        owners = User.objects.filter(seller__isnull=False)
        self.assertEqual(owners.count(), N_SHOPS)
        for owner in owners:
            self.assertTrue(owner.email.endswith("@example.test"))
            self.assertFalse(owner.has_usable_password())
            self.assertEqual(owner.phone, "")
            self.assertFalse(owner.addresses.exists())
            self.assertFalse(owner.is_staff)
        r = self.client.post(
            "/api/auth/signin/", {"email": owner_email("baker"), "password": ""}, content_type="application/json"
        )
        self.assertNotEqual(r.status_code, 200)

    def test_running_twice_creates_nothing_new(self):
        self.seed()
        before = (User.objects.count(), Seller.objects.count(), Product.objects.count(), ProductImage.objects.count())
        out = self.seed()
        self.assertIn("0 shop(s) and 0 product(s) created", out)
        after = (User.objects.count(), Seller.objects.count(), Product.objects.count(), ProductImage.objects.count())
        self.assertEqual(before, after)

    def test_a_half_finished_run_is_completed_without_touching_what_is_there(self):
        self.seed()
        baker = Seller.objects.get(slug="lakshmis-kitchen")
        cake = baker.products.get(name="Chocolate truffle cake (1 kg)")
        # Someone (an admin) changes one demo product, and another one is missing (as if the first run was cut off).
        Product.objects.filter(pk=cake.pk).update(stock=1, price_paise=99900)
        baker.products.get(name="Butter cookies, box of 12").delete()
        out = self.seed()
        self.assertIn("0 shop(s) and 1 product(s) created", out)
        cake.refresh_from_db()
        self.assertEqual((cake.stock, cake.price_paise), (1, 99900))  # left exactly as it was
        self.assertTrue(baker.products.filter(name="Butter cookies, box of 12").exists())

    def test_never_changes_existing_users_shops_products_orders_or_refunds(self):
        # A real seller already uses one of the demo links, and a real account uses a demo owner's email.
        real = make_seller(slug="ammas-pickles", name="The Real Amma's")
        real_product = make_product(real, name="Real pickle", stock=3)
        taken = make_user(owner_email("artist"))
        part = make_paid_order(real_product)
        Refund.objects.create(seller_order=part, amount=100)
        snapshot = (
            list(User.objects.values().order_by("pk")),
            list(Seller.objects.values().order_by("pk")),
            list(Product.objects.values().order_by("pk")),
            list(Order.objects.values().order_by("pk")),
            list(SellerOrder.objects.values().order_by("pk")),
            list(Refund.objects.values().order_by("pk")),
        )
        out = self.seed()
        self.assertIn("belongs to someone else", out)
        self.assertIn("already exists without its demo shop", out)
        self.assertEqual(Seller.objects.count(), 1 + N_SHOPS - 2)  # those two demo shops were skipped
        # Every row that existed before is exactly the same.
        before_ids = [u["id"] for u in snapshot[0]]
        self.assertEqual(snapshot[0], list(User.objects.filter(pk__in=before_ids).values().order_by("pk")))
        self.assertEqual(snapshot[1], list(Seller.objects.filter(pk=real.pk).values()))
        self.assertEqual(snapshot[2], list(Product.objects.filter(pk=real_product.pk).values()))
        self.assertEqual(snapshot[3], list(Order.objects.values().order_by("pk")))
        self.assertEqual(snapshot[4], list(SellerOrder.objects.values().order_by("pk")))
        self.assertEqual(snapshot[5], list(Refund.objects.values().order_by("pk")))
        self.assertTrue(taken.has_usable_password())
        self.assertFalse(Seller.objects.filter(owner=taken).exists())

    def test_needs_the_categories(self):
        Category.objects.all().delete()  # test database only
        with self.assertRaises(CommandError):
            self.seed()
        self.assertEqual(Product.objects.count(), 0)

    @override_settings(DEBUG=True)
    def test_refuses_on_real_local_data(self):
        with self.assertRaises(CommandError) as raised:
            self.seed()
        self.assertIn("never on your real local data", str(raised.exception))
        self.assertEqual(Seller.objects.count(), 0)

    @override_settings(DEBUG=True)
    def test_runs_on_the_throwaway_copy(self):
        with mock.patch("catalog.management.commands.seed_showcase.assert_throwaway"):  # it IS the throwaway copy
            self.seed()
        self.assertEqual(Seller.objects.count(), N_SHOPS)

    def test_showcase_categories_exist_in_the_fixed_list(self):
        slugs = {c[0] for c in CATEGORIES}
        self.assertTrue({shop[5] for shop in SHOPS} <= slugs)
