from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from core.tests.factories import make_address, make_user


class AuthTests(TestCase):
    def setUp(self):
        cache.clear()  # reset the sign-in rate limit between tests
        self.client = APIClient(enforce_csrf_checks=True)

    def csrf(self):
        self.client.get("/api/auth/csrf/")
        return {"HTTP_X_CSRFTOKEN": self.client.cookies[settings.CSRF_COOKIE_NAME].value}

    def test_sign_up_signs_you_in_as_a_buyer(self):
        res = self.client.post(
            "/api/auth/signup/",
            {"email": "Asha@Example.com", "password": "long-enough-pass", "name": "Asha"},
            format="json",
            **self.csrf(),
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["email"], "asha@example.com")
        self.assertEqual(res.data["role"], "buyer")
        self.assertEqual(self.client.get("/api/auth/me/").data["user"]["email"], "asha@example.com")

    def test_sign_up_cannot_choose_a_role(self):
        self.client.post(
            "/api/auth/signup/",
            {"email": "x@example.com", "password": "long-enough-pass", "role": "admin"},
            format="json",
            **self.csrf(),
        )
        self.assertEqual(User.objects.get(email="x@example.com").role, User.Role.BUYER)

    def test_sign_in_and_out(self):
        make_user("a@example.com", "long-enough-pass")
        headers = self.csrf()
        bad = self.client.post(
            "/api/auth/signin/", {"email": "a@example.com", "password": "nope"}, format="json", **headers
        )
        self.assertEqual(bad.status_code, 400)

        ok = self.client.post(
            "/api/auth/signin/", {"email": "a@example.com", "password": "long-enough-pass"}, format="json", **headers
        )
        self.assertEqual(ok.status_code, 200)
        # Django rotates the CSRF token at sign-in, so fetch a fresh one.
        self.client.post("/api/auth/signout/", **self.csrf())
        self.assertIsNone(self.client.get("/api/auth/me/").data["user"])

    def test_changes_without_csrf_token_are_refused(self):
        res = self.client.post(
            "/api/auth/signup/", {"email": "c@example.com", "password": "long-enough-pass"}, format="json"
        )
        self.assertEqual(res.status_code, 403)

    def test_nobody_can_change_their_own_role(self):
        user = make_user()
        client = APIClient()
        client.force_authenticate(user)
        res = client.patch("/api/auth/me/", {"role": "admin", "name": "New name"}, format="json")
        self.assertEqual(res.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.role, User.Role.BUYER)
        self.assertEqual(user.name, "New name")


class AddressTests(TestCase):
    def test_buyer_a_cannot_see_buyer_b_addresses(self):
        a, b = make_user(), make_user()
        make_address(b)
        client = APIClient()
        client.force_authenticate(a)
        self.assertEqual(client.get("/api/addresses/").data, [])

    def test_pincode_and_phone_are_validated(self):
        client = APIClient()
        client.force_authenticate(make_user())
        res = client.post(
            "/api/addresses/",
            {"name": "A", "phone": "12345", "line1": "x", "city": "y", "pincode": "56"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("pincode", res.data)
        self.assertIn("phone", res.data)
