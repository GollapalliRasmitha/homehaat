"""Small fixes from the QA pass: plain messages, and the real client IP for the sign-in rate limit."""

from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings
from rest_framework.test import APIClient

from core.client_ip import client_ip
from core.tests.factories import add_to_cart, make_category, make_product, make_seller, make_user


class MessageTests(TestCase):
    def test_a_sold_out_product_says_so(self):
        buyer = APIClient()
        buyer.force_authenticate(make_user())
        product = make_product(stock=0)
        r = buyer.post("/api/cart/items/", {"product_id": product.id, "qty": 1}, format="json")
        self.assertEqual((r.status_code, r.json()["detail"]), (400, "This is sold out."))
        two = make_product(stock=2)
        r = buyer.post("/api/cart/items/", {"product_id": two.id, "qty": 3}, format="json")
        self.assertEqual(r.json()["detail"], "Only 2 available.")

    def test_changing_a_bag_line_past_stock_says_so_too(self):
        user = make_user()
        product = make_product(stock=1)
        line = add_to_cart(user, product)
        product.stock = 0
        product.save()
        buyer = APIClient()
        buyer.force_authenticate(user)
        r = buyer.patch(f"/api/cart/items/{line.id}/", {"qty": 1}, format="json")
        self.assertEqual(r.json()["detail"], "This is sold out.")

    def test_a_quote_under_one_rupee_gets_a_plain_rupees_message(self):
        shop = make_seller(main_category=make_category("cakes"), slug="ammus-kitchen")
        buyer = APIClient()
        buyer.force_authenticate(make_user())
        rid = buyer.post(
            "/api/requests/",
            {"seller": "ammus-kitchen", "description": "A small cake for a birthday, please."},
            format="json",
        ).json()["id"]
        seller = APIClient()
        seller.force_authenticate(shop.owner)
        for bad in (50, 0, -100):
            r = seller.post(f"/api/seller/requests/{rid}/quote/", {"quote_paise": bad}, format="json")
            self.assertEqual(r.status_code, 400)
            self.assertEqual(str(r.json()["quote_paise"][0]), "Enter a price of ₹1 or more.")
        r = seller.post(f"/api/seller/requests/{rid}/quote/", {"quote_paise": "lots"}, format="json")
        self.assertEqual(str(r.json()["quote_paise"][0]), "Enter a price in rupees, like 450.")


@override_settings(PROXY_SECRET="proxy-test-secret")
class ClientIpTests(TestCase):
    """Behind the Next.js proxy every request comes from the proxy's address, so the proxy passes on the visitor's
    IP with a shared secret. Without the right secret, a header claiming an IP is ignored (it could be faked)."""

    def setUp(self):
        cache.clear()
        self.rf = RequestFactory()

    def req(self, **headers):
        return self.rf.get("/", REMOTE_ADDR="127.0.0.1", **headers)

    def test_the_proxy_with_the_secret_passes_the_real_visitor_ip(self):
        r = self.req(HTTP_X_HOMEHAAT_CLIENT_IP="203.0.113.7", HTTP_X_HOMEHAAT_PROXY_SECRET="proxy-test-secret")
        self.assertEqual(client_ip(r), "203.0.113.7")

    def test_a_faked_header_without_the_secret_is_ignored(self):
        self.assertEqual(client_ip(self.req(HTTP_X_HOMEHAAT_CLIENT_IP="203.0.113.7")), "127.0.0.1")
        r = self.req(HTTP_X_HOMEHAAT_CLIENT_IP="203.0.113.7", HTTP_X_HOMEHAAT_PROXY_SECRET="guess")
        self.assertEqual(client_ip(r), "127.0.0.1")
        self.assertEqual(client_ip(self.req(HTTP_X_FORWARDED_FOR="198.51.100.1")), "127.0.0.1")  # not trusted

    def test_a_bad_ip_value_is_ignored(self):
        r = self.req(HTTP_X_HOMEHAAT_CLIENT_IP="not-an-ip", HTTP_X_HOMEHAAT_PROXY_SECRET="proxy-test-secret")
        self.assertEqual(client_ip(r), "127.0.0.1")

    @override_settings(PROXY_SECRET="")
    def test_no_secret_configured_means_nothing_is_trusted(self):
        r = self.req(HTTP_X_HOMEHAAT_CLIENT_IP="203.0.113.7", HTTP_X_HOMEHAAT_PROXY_SECRET="")
        self.assertEqual(client_ip(r), "127.0.0.1")

    def test_the_sign_in_limit_counts_each_visitor_separately(self):
        def sign_in(ip):
            c = APIClient(enforce_csrf_checks=False)
            c.get("/api/auth/csrf/")
            return c.post(
                "/api/auth/signin/",
                {"email": "nobody@example.test", "password": "wrong-password"},
                format="json",
                HTTP_X_CSRFTOKEN=c.cookies["homehaat_csrftoken"].value,
                HTTP_X_HOMEHAAT_CLIENT_IP=ip,
                HTTP_X_HOMEHAAT_PROXY_SECRET="proxy-test-secret",
            )

        for _ in range(10):
            sign_in("203.0.113.7")
        self.assertEqual(sign_in("203.0.113.7").status_code, 429)  # this visitor hit the limit...
        self.assertNotEqual(sign_in("198.51.100.20").status_code, 429)  # ...but another visitor isn't blocked
