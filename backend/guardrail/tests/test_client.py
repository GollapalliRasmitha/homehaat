"""
Tests for the GuardRail sender (guardrail/client.py). GuardRail itself is never called: requests.post is replaced.
The rule these prove: monitoring can never slow down or break HomeHaat.
"""

import json
from unittest import mock

import requests
from django.test import TestCase, override_settings

from guardrail import client
from guardrail.models import OutboxEvent

SECRET = "test-guardrail-secret-0123456789abcdefgh"
ON = dict(GUARDRAIL_ENABLED=True, GUARDRAIL_URL="http://guardrail.test", GUARDRAIL_SECRET=SECRET, GUARDRAIL_SYNC=True)


def answer(status: int) -> mock.Mock:
    return mock.Mock(status_code=status, text="")


class SigningTests(TestCase):
    def test_matches_guardrails_reference_vector(self):
        # The same value GuardRail's own test expects (lib/ingest/signature.test.ts), computed independently.
        self.assertEqual(
            client.sign("test-secret", 1700000000, "00ff", b'{"events":[]}'),
            "884ff67b8f561c7c4b1a8cd935409f9dd97be53755625abbb4e60bea4262e583",
        )

    def test_mask_email(self):
        self.assertEqual(client.mask_actor("Priya.Sharma@Gmail.com"), "pr****@gmail.com")
        self.assertEqual(client.mask_actor("9876543210"), "98****")
        self.assertEqual(client.mask_actor(""), None)


@override_settings(**ON)
class SendTests(TestCase):
    def event(self):
        return client.build_event("login_failed", actor="a@example.com", path="/api/auth/signin/?next=/x")

    def test_build_event_keeps_privacy(self):
        event = client.build_event(
            "login_failed",
            actor="priya@example.com",
            path="/reset/?token=SECRET",
            meta={"reason": "x", "password": "hunter2"},
        )
        self.assertEqual(event["actor"], "pr****@example.com")
        self.assertEqual(event["path"], "/reset/")  # the query string can hold tokens
        self.assertEqual(event["meta"], {"reason": "x"})  # only allow-listed keys
        self.assertNotIn("hunter2", json.dumps(event))

    def test_sends_signed_request_with_short_timeout(self):
        with mock.patch.object(client.requests, "post", return_value=answer(202)) as post:
            self.assertEqual(client.send_batch([self.event()]), "ok")
        url, kwargs = post.call_args.args[0], post.call_args.kwargs
        self.assertEqual(url, "http://guardrail.test/api/ingest")
        self.assertEqual(kwargs["timeout"], client.TIMEOUT_SECONDS)
        self.assertLessEqual(client.TIMEOUT_SECONDS, 2)
        headers = kwargs["headers"]
        self.assertEqual(headers["X-GuardRail-Source"], "homehaat")
        expected = client.sign(
            SECRET, int(headers["X-GuardRail-Timestamp"]), headers["X-GuardRail-Nonce"], kwargs["data"]
        )
        self.assertEqual(headers["X-GuardRail-Signature"], expected)
        self.assertEqual(json.loads(kwargs["data"])["events"][0]["type"], "login_failed")

    def test_guardrail_down_goes_to_outbox_and_never_raises(self):
        with mock.patch.object(client.requests, "post", side_effect=requests.ConnectionError("down")):
            client.report("login_failed", actor="a@example.com")
        self.assertEqual(OutboxEvent.objects.count(), 1)

    def test_server_error_and_rate_limit_are_retried_later(self):
        for status in (500, 503, 429):
            with mock.patch.object(client.requests, "post", return_value=answer(status)):
                client.report("login_failed")
        self.assertEqual(OutboxEvent.objects.count(), 3)

    def test_refused_request_is_dropped_not_retried_forever(self):
        with mock.patch.object(client.requests, "post", return_value=answer(400)):
            client.report("login_failed")
        self.assertEqual(OutboxEvent.objects.count(), 0)

    def test_outbox_is_flushed_when_guardrail_is_back(self):
        with mock.patch.object(client.requests, "post", side_effect=requests.Timeout("slow")):
            client.report("login_failed")
            client.report("suspicious_path", path="/.env")
        self.assertEqual(OutboxEvent.objects.count(), 2)

        with mock.patch.object(client.requests, "post", return_value=answer(202)) as post:
            self.assertEqual(client.flush_outbox(), {"sent": 2, "dropped": 0, "waiting": 0})
        self.assertEqual(OutboxEvent.objects.count(), 0)
        sent = json.loads(post.call_args.kwargs["data"])["events"]
        self.assertEqual([e["type"] for e in sent], ["login_failed", "suspicious_path"])

    def test_a_backlog_problem_after_a_good_send_is_contained(self):
        with (
            mock.patch.object(client.requests, "post", return_value=answer(202)),
            mock.patch.object(client, "flush_outbox", side_effect=RuntimeError("outbox table missing")),
        ):
            client.deliver([self.event()])  # must not raise: the event itself was delivered

    def test_failed_flush_keeps_rows_and_counts_attempts(self):
        OutboxEvent.objects.create(payload=self.event())
        with mock.patch.object(client.requests, "post", side_effect=requests.ConnectionError()):
            self.assertEqual(client.flush_outbox(), {"sent": 0, "dropped": 0, "waiting": 1})
        self.assertEqual(OutboxEvent.objects.get().attempts, 1)

    def test_outbox_has_a_size_cap(self):
        with (
            mock.patch.object(client, "MAX_OUTBOX", 3),
            mock.patch.object(client.requests, "post", side_effect=requests.ConnectionError()),
        ):
            for i in range(5):
                client.report("login_failed", actor=f"user{i}@example.com")
        actors = list(OutboxEvent.objects.order_by("id").values_list("payload__actor", flat=True))
        self.assertEqual(actors, ["us****@example.com"] * 3)  # oldest dropped first
        self.assertEqual(OutboxEvent.objects.count(), 3)


class SwitchedOffTests(TestCase):
    @override_settings(GUARDRAIL_ENABLED=False, GUARDRAIL_URL="http://guardrail.test", GUARDRAIL_SECRET=SECRET)
    def test_switched_off_does_nothing(self):
        with mock.patch.object(client.requests, "post") as post:
            client.report("login_failed")
        post.assert_not_called()
        self.assertEqual(OutboxEvent.objects.count(), 0)

    @override_settings(GUARDRAIL_ENABLED=True, GUARDRAIL_URL="", GUARDRAIL_SECRET=SECRET)
    def test_missing_url_or_short_secret_means_off(self):
        self.assertFalse(client.is_enabled())
        with override_settings(GUARDRAIL_URL="http://g.test", GUARDRAIL_SECRET="short"):
            self.assertFalse(client.is_enabled())

    @override_settings(**ON)
    def test_a_bug_inside_report_never_reaches_the_caller(self):
        with mock.patch.object(client, "build_event", side_effect=RuntimeError("boom")):
            client.report("login_failed")  # must not raise
