"""Stage 8: production settings helpers, scheduled jobs, health check, Cloudinary storage, admin account."""

import os
from datetime import timedelta
from io import StringIO
from unittest import mock

from django.core.cache import cache
from django.core.checks import run_checks
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from accounts.models import User
from config.database import database_from_url
from core import storage as cloud
from core.jobs import LAZY_KEY
from core.tests.factories import add_to_cart, make_address, make_product, make_seller, make_user
from orders.models import Order
from orders.services import create_order_from_cart


class DatabaseUrlTests(SimpleTestCase):
    def test_neon_url(self):
        db = database_from_url("postgresql://hh_user:p%40ss%2Fword@ep-cool-1.ap-southeast-1.aws.neon.tech/neondb")
        self.assertEqual(db["NAME"], "neondb")
        self.assertEqual(db["USER"], "hh_user")
        self.assertEqual(db["PASSWORD"], "p@ss/word")  # %-encoded characters decoded
        self.assertEqual(db["HOST"], "ep-cool-1.ap-southeast-1.aws.neon.tech")
        self.assertEqual(db["PORT"], "5432")
        self.assertEqual(db["OPTIONS"], {"sslmode": "require"})  # encrypted by default
        self.assertFalse(db["DISABLE_SERVER_SIDE_CURSORS"])

    def test_query_options_kept_and_weak_ssl_refused(self):
        db = database_from_url("postgres://u:p@ep-x-pooler.neon.tech:6543/db?sslmode=disable&channel_binding=require")
        self.assertEqual(db["OPTIONS"], {"sslmode": "require", "channel_binding": "require"})
        self.assertEqual(db["PORT"], "6543")
        self.assertTrue(db["DISABLE_SERVER_SIDE_CURSORS"])  # PgBouncer pooler
        strict = database_from_url("postgresql://u:p@ep-x.neon.tech/db?sslmode=verify-full")
        self.assertEqual(strict["OPTIONS"]["sslmode"], "verify-full")

    def test_not_a_postgres_url(self):
        with self.assertRaises(RuntimeError):
            database_from_url("mysql://u:p@host/db")


class HealthTests(SimpleTestCase):
    def test_health_answers_without_the_database(self):
        r = self.client.get("/api/health/")  # SimpleTestCase: any database query would fail the test
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"ok": True})
        self.assertEqual(r["Cache-Control"], "no-store")


@override_settings(JOBS_SECRET="jobs-test-secret")
class JobsEndpointTests(TestCase):
    url = "/api/jobs/run/"

    def expired_checkout(self):
        cake = make_product(make_seller(), stock=5)
        buyer = make_user()
        add_to_cart(buyer, cake, qty=2)
        order = create_order_from_cart(buyer, make_address(buyer))
        Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - timedelta(minutes=20))
        return order, cake

    def run_jobs(self, secret="jobs-test-secret", jobs=None):
        url = self.url + (f"?jobs={jobs}" if jobs else "")
        return self.client.post(url, headers={"X-HomeHaat-Jobs-Secret": secret} if secret is not None else {})

    def test_right_secret_runs_both_jobs(self):
        order, cake = self.expired_checkout()
        r = self.run_jobs()
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["expire"], {"released": 1})
        self.assertEqual(body["refunds"], {"sent": 0, "still_failing": 0, "checked": 0})
        order.refresh_from_db()
        cake.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.FAILED)
        self.assertEqual(cake.stock, 5)

    def test_wrong_or_missing_secret_runs_nothing(self):
        order, _ = self.expired_checkout()
        self.assertEqual(self.run_jobs(secret="guess").status_code, 403)
        self.assertEqual(self.run_jobs(secret=None).status_code, 403)
        self.assertEqual(self.run_jobs(secret="").status_code, 403)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.PENDING)

    @override_settings(JOBS_SECRET="")
    def test_no_secret_configured_means_switched_off(self):
        r = self.run_jobs(secret="")
        self.assertEqual(r.status_code, 503)

    def test_one_job_only_and_unknown_jobs(self):
        self.assertEqual(set(self.run_jobs(jobs="expire").json()), {"ok", "expire"})
        self.assertEqual(self.run_jobs(jobs="expire,delete_everything").status_code, 400)

    def test_get_is_refused(self):
        self.assertEqual(
            self.client.get(self.url, headers={"X-HomeHaat-Jobs-Secret": "jobs-test-secret"}).status_code, 405
        )

    def test_a_failing_job_is_reported_and_the_other_still_runs(self):
        order, _ = self.expired_checkout()
        with mock.patch("payments.refunds.retry_refunds", side_effect=RuntimeError("Razorpay down")):
            with self.assertLogs("homehaat", "ERROR"):
                r = self.run_jobs()
        self.assertEqual(r.status_code, 500)  # the scheduler shows a red run
        self.assertEqual(r.json()["refunds"], "failed")
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.FAILED)


@override_settings(LAZY_JOBS=True)
class LazyExpiryTests(TestCase):
    def setUp(self):
        cache.delete(LAZY_KEY)
        self.addCleanup(cache.delete, LAZY_KEY)

    def test_page_load_releases_expired_holds_at_most_once_a_minute(self):
        with mock.patch("core.jobs.run_jobs") as run:
            self.client.get("/api/categories/")
            self.client.get("/api/products/")
        run.assert_called_once_with(["expire"])

    def test_really_releases_a_hold(self):
        cake = make_product(make_seller(), stock=3)
        buyer = make_user()
        add_to_cart(buyer, cake)
        order = create_order_from_cart(buyer, make_address(buyer))
        Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - timedelta(minutes=16))
        self.client.get("/api/products/")
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.FAILED)

    def test_health_and_webhook_never_run_it(self):
        with mock.patch("core.jobs.run_jobs") as run:
            self.client.get("/api/health/")
            self.client.post("/api/payments/webhook/", data="{}", content_type="application/json")
        run.assert_not_called()

    def test_a_failure_never_breaks_the_page(self):
        with mock.patch("orders.services.expire_unpaid_orders", side_effect=RuntimeError("db hiccup")):
            with self.assertLogs("homehaat", "ERROR"):
                r = self.client.get("/api/categories/")
        self.assertEqual(r.status_code, 200)


class CloudinaryStorageTests(SimpleTestCase):
    """Cloudinary is faked: these check WHAT we ask it for, never the network."""

    def setUp(self):
        patcher = mock.patch.dict(os.environ, {"CLOUDINARY_URL": "cloudinary://123:abc@demo"})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.storage = cloud.CloudinaryStorage()

    def test_product_photo_is_public(self):
        with mock.patch("cloudinary.uploader.upload") as upload:
            name = self.storage.save("products/ab12.jpg", ContentFile(b"jpeg-bytes"))
        self.assertEqual(name, "products/ab12.jpg")  # same name as on disk
        args, kwargs = upload.call_args
        self.assertEqual(args[0], b"jpeg-bytes")
        self.assertEqual(kwargs["public_id"], "homehaat/products/ab12")
        self.assertEqual(kwargs["type"], "upload")
        url = self.storage.url(name)
        self.assertTrue(url.startswith("https://res.cloudinary.com/demo/image/upload/"), url)
        self.assertIn("f_auto,q_auto", url)
        self.assertTrue(url.endswith("homehaat/products/ab12.jpg"), url)

    def test_request_photo_is_private(self):
        with mock.patch("cloudinary.uploader.upload") as upload:
            self.storage.save("requests/cd34.png", ContentFile(b"png-bytes"))
        self.assertEqual(upload.call_args.kwargs["type"], "authenticated")  # unsigned links refused by Cloudinary
        # Its URL is never a Cloudinary link: only Django's checked route.
        self.assertEqual(self.storage.url("requests/cd34.png"), "/api/private-media/requests/cd34.png")

    def test_reading_a_private_photo_uses_a_signed_link_server_side(self):
        reply = mock.Mock(status_code=200, content=b"png-bytes")
        with mock.patch("core.storage.requests.get", return_value=reply) as get:
            f = self.storage.open("requests/cd34.png")
        self.assertEqual(f.read(), b"png-bytes")
        url = get.call_args.args[0]
        self.assertIn("/image/authenticated/s--", url)  # s--…-- is Cloudinary's signature
        self.assertTrue(url.endswith("homehaat/requests/cd34.png"), url)

    def test_missing_photo(self):
        with mock.patch("core.storage.requests.get", return_value=mock.Mock(status_code=404)):
            with self.assertRaises(FileNotFoundError):
                self.storage.open("requests/gone.jpg")

    def test_delete_uses_the_right_type(self):
        with mock.patch("cloudinary.uploader.destroy") as destroy:
            self.storage.delete("requests/cd34.png")
            self.storage.delete("covers/ef56.webp")
        self.assertEqual(destroy.call_args_list[0].args[0], "homehaat/requests/cd34")
        self.assertEqual(destroy.call_args_list[0].kwargs["type"], "authenticated")
        self.assertEqual(destroy.call_args_list[1].kwargs["type"], "upload")


class EnsureAdminTests(TestCase):
    def run_command(self, **env):
        out = StringIO()
        with mock.patch.dict(os.environ, env):
            call_command("ensure_admin", stdout=out)
        return out.getvalue()

    def test_nothing_set_does_nothing(self):
        with mock.patch.dict(os.environ, {"DJANGO_ADMIN_EMAIL": "", "DJANGO_ADMIN_PASSWORD": ""}):
            out = StringIO()
            call_command("ensure_admin", stdout=out)
        self.assertIn("nothing to do", out.getvalue())
        self.assertFalse(User.objects.filter(is_superuser=True).exists())

    def test_creates_admin_once_and_never_changes_the_password(self):
        pw = "Long-admin-pass-2026"
        out = self.run_command(DJANGO_ADMIN_EMAIL="Owner@Example.test", DJANGO_ADMIN_PASSWORD=pw)
        self.assertNotIn(pw, out)  # never printed
        admin = User.objects.get(email="owner@example.test")
        self.assertTrue(admin.is_superuser and admin.is_staff)
        self.run_command(DJANGO_ADMIN_EMAIL="owner@example.test", DJANGO_ADMIN_PASSWORD="Another-pass-2026")
        admin.refresh_from_db()
        self.assertTrue(admin.check_password(pw))
        self.assertEqual(User.objects.filter(is_superuser=True).count(), 1)

    def test_an_ordinary_account_is_not_made_admin(self):
        make_user("taken@example.test")  # a stranger could sign up with that email first
        out = self.run_command(DJANGO_ADMIN_EMAIL="taken@example.test", DJANGO_ADMIN_PASSWORD="Long-admin-pass-2026")
        self.assertIn("NOT made an admin", out)
        self.assertFalse(User.objects.get(email="taken@example.test").is_staff)

    def test_weak_password_stops_the_build(self):
        with self.assertRaises(CommandError):
            self.run_command(DJANGO_ADMIN_EMAIL="owner@example.test", DJANGO_ADMIN_PASSWORD="12345678")
        self.assertFalse(User.objects.filter(email="owner@example.test").exists())


class ProductionCheckTests(SimpleTestCase):
    def ids(self):
        return [m.id for m in run_checks()]

    @override_settings(DEBUG=False, TESTING=False, USE_CLOUDINARY=False)
    def test_warns_when_photos_would_be_lost(self):
        self.assertIn("homehaat.W001", self.ids())

    @override_settings(DEBUG=False, TESTING=False, USE_CLOUDINARY=True)
    def test_quiet_with_cloudinary(self):
        self.assertNotIn("homehaat.W001", self.ids())
