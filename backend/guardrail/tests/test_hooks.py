"""
The places in HomeHaat that report to GuardRail. requests.post is replaced, so nothing leaves the test.
Each test also checks the user-facing answer is exactly what it was before GuardRail existed.
"""

import json
from unittest import mock

import requests
from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.tests.factories import make_user
from guardrail import client

SECRET = "test-guardrail-secret-0123456789abcdefgh"
ON = dict(GUARDRAIL_ENABLED=True, GUARDRAIL_URL="http://guardrail.test", GUARDRAIL_SECRET=SECRET, GUARDRAIL_SYNC=True)


def sent_events(post: mock.Mock) -> list[dict]:
    return [e for call in post.call_args_list for e in json.loads(call.kwargs["data"])["events"]]


class Base(TestCase):
    def setUp(self):
        cache.clear()  # reset the sign-in rate limit
        self.client = APIClient(enforce_csrf_checks=True)
        patcher = mock.patch.object(client.requests, "post", return_value=mock.Mock(status_code=202, text=""))
        self.post = patcher.start()
        self.addCleanup(patcher.stop)

    def csrf(self):
        self.client.get("/api/auth/csrf/")
        return {"HTTP_X_CSRFTOKEN": self.client.cookies[settings.CSRF_COOKIE_NAME].value}

    def sign_in(self, email, password):
        return self.client.post(
            "/api/auth/signin/", {"email": email, "password": password}, format="json", **self.csrf()
        )


@override_settings(**ON)
class LoginHookTests(Base):
    def test_failed_sign_in_reports_masked_email_and_never_the_password(self):
        res = self.sign_in("Asha@Example.com", "my-secret-guess-123")
        self.assertEqual(res.status_code, 400)  # unchanged answer

        [event] = sent_events(self.post)
        self.assertEqual(event["type"], "login_failed")
        self.assertEqual(event["actor"], "as****@example.com")
        self.assertEqual(event["path"], "/api/auth/signin/")
        self.assertEqual(event["ip"], "127.0.0.1")
        everything = json.dumps([c.kwargs for c in self.post.call_args_list], default=str)
        self.assertNotIn("my-secret-guess-123", everything)
        self.assertNotIn("asha@example.com", everything.lower())

    def test_successful_sign_in(self):
        make_user("b@example.com", "long-enough-pass")
        self.assertEqual(self.sign_in("b@example.com", "long-enough-pass").status_code, 200)
        self.assertEqual([e["type"] for e in sent_events(self.post)], ["login_success"])

    def test_admin_sign_in_is_its_own_type(self):
        make_user("boss@example.com", "long-enough-pass", is_staff=True, role="admin")
        self.sign_in("boss@example.com", "long-enough-pass")
        [event] = sent_events(self.post)
        self.assertEqual(event["type"], "admin_login")
        self.assertEqual(event["meta"], {"role": "admin"})

    def test_sign_in_still_works_when_guardrail_is_down(self):
        make_user("c@example.com", "long-enough-pass")
        self.post.side_effect = requests.ConnectionError("GuardRail is down")
        self.assertEqual(self.sign_in("c@example.com", "long-enough-pass").status_code, 200)
        self.assertEqual(self.sign_in("c@example.com", "wrong").status_code, 400)


@override_settings(GUARDRAIL_ENABLED=False)
class SwitchedOffHookTests(Base):
    def test_sign_in_works_and_nothing_is_sent_when_switched_off(self):
        make_user("d@example.com", "long-enough-pass")
        self.assertEqual(self.sign_in("d@example.com", "long-enough-pass").status_code, 200)
        self.assertEqual(self.sign_in("d@example.com", "wrong").status_code, 400)
        self.post.assert_not_called()


@override_settings(**ON)
class MiddlewareHookTests(Base):
    def test_scanner_paths_are_reported(self):
        for path in ("/wp-admin/", "/.env", "/.git/config", "/phpmyadmin/index.php", "/xmlrpc.php"):
            self.assertEqual(self.client.get(path).status_code, 404)  # still a plain 404
        events = sent_events(self.post)
        self.assertEqual({e["type"] for e in events}, {"suspicious_path"})
        self.assertEqual(len(events), 5)
        self.assertEqual(events[0]["status_code"], 404)

    def test_normal_pages_are_not_reported(self):
        self.client.get("/api/health/")
        self.client.get("/api/categories/")
        self.client.get("/api/no-such-page/")
        self.post.assert_not_called()

    def test_rate_limit_hits_are_reported(self):
        for _ in range(12):  # the sign-in limit is 10 a minute
            last = self.sign_in("e@example.com", "wrong")
        self.assertEqual(last.status_code, 429)
        types = [e["type"] for e in sent_events(self.post)]
        self.assertEqual(types.count("rate_limited"), 2)
        self.assertEqual(types.count("login_failed"), 10)

    def test_permission_denied_for_a_signed_in_user(self):
        buyer = make_user("f@example.com")
        self.client.force_authenticate(buyer)
        res = self.client.get("/api/seller/overview/")  # buyers have no shop
        if res.status_code == 403:
            self.assertEqual([e["type"] for e in sent_events(self.post)], ["permission_denied"])
        else:
            self.post.assert_not_called()  # this endpoint answers differently; nothing to report

    def test_wrong_jobs_secret_is_reported(self):
        with self.settings(JOBS_SECRET="real-jobs-secret"):
            res = self.client.post("/api/jobs/run/", HTTP_X_HOMEHAAT_JOBS_SECRET="guess")
        self.assertEqual(res.status_code, 403)
        [event] = sent_events(self.post)
        self.assertEqual(event["type"], "permission_denied")
        self.assertEqual(event["meta"], {"reason": "jobs_secret"})
