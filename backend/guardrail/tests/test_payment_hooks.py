"""Payment-side reports: forged webhooks, failed payments, refunds. Razorpay and GuardRail are both faked."""

import json
from unittest import mock

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from guardrail import client
from orders.models import Order
from orders.tests.test_cancel_refund import RZP, CancelSetup, rzp_refund
from payments.tests.test_payments import WEBHOOK_SECRET, PaidOrderMixin, sign

SECRET = "test-guardrail-secret-0123456789abcdefgh"
ON = dict(GUARDRAIL_ENABLED=True, GUARDRAIL_URL="http://guardrail.test", GUARDRAIL_SECRET=SECRET, GUARDRAIL_SYNC=True)


def sent_events(post: mock.Mock) -> list[dict]:
    return [e for call in post.call_args_list for e in json.loads(call.kwargs["data"])["events"]]


@override_settings(RAZORPAY_WEBHOOK_SECRET=WEBHOOK_SECRET, **ON)
class WebhookHookTests(PaidOrderMixin, TestCase):
    url = "/api/payments/webhook/"

    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(client.requests, "post", return_value=mock.Mock(status_code=202, text=""))
        self.post = patcher.start()
        self.addCleanup(patcher.stop)

    def send(self, payload: dict, secret=WEBHOOK_SECRET):
        body = json.dumps(payload).encode()
        return APIClient().post(
            self.url, body, content_type="application/json", HTTP_X_RAZORPAY_SIGNATURE=sign(body, secret)
        )

    def captured(self, amount):
        entity = {"id": "pay_1", "order_id": "order_TEST123", "amount": amount, "status": "captured"}
        return {"event": "payment.captured", "payload": {"payment": {"entity": entity}}}

    def test_forged_webhook_is_reported(self):
        res = self.send(self.captured(49000), secret="attacker-guess")
        self.assertEqual(res.status_code, 400)  # unchanged answer
        [event] = sent_events(self.post)
        self.assertEqual(event["type"], "webhook_signature_failed")
        self.assertEqual(event["meta"], {"gateway": "razorpay", "reason": "bad_signature"})
        self.assertEqual(event["path"], self.url)

    def test_genuine_webhook_reports_nothing(self):
        self.assertEqual(self.send(self.captured(49000)).status_code, 200)
        self.post.assert_not_called()

    def test_amount_mismatch_is_reported_as_payment_failed(self):
        self.assertEqual(self.send(self.captured(100)).status_code, 400)
        [event] = sent_events(self.post)
        self.assertEqual(event["type"], "payment_failed")
        self.assertEqual(event["meta"]["reason"], "amount_mismatch")
        self.assertEqual(event["meta"]["order_ref"], str(self.order.pk))

    def test_payment_failed_event_is_reported(self):
        entity = {"id": "pay_2", "order_id": "order_TEST123", "error_reason": "payment_declined"}
        res = self.send({"event": "payment.failed", "payload": {"payment": {"entity": entity}}})
        self.assertEqual(res.status_code, 200)
        [event] = sent_events(self.post)
        self.assertEqual(event["type"], "payment_failed")
        self.assertEqual(
            event["meta"], {"gateway": "razorpay", "reason": "payment_declined", "order_ref": str(self.order.pk)}
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.PENDING)  # nothing else changes

    def test_payment_failed_with_missing_details_still_answers_200(self):
        self.assertEqual(self.send({"event": "payment.failed", "payload": {}}).status_code, 200)


@override_settings(**ON)
@mock.patch(f"{RZP}.list_refunds", return_value=[])
@mock.patch(f"{RZP}.create_refund")
class RefundHookTests(CancelSetup):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(client.requests, "post", return_value=mock.Mock(status_code=202, text=""))
        self.post = patcher.start()
        self.addCleanup(patcher.stop)

    def test_refund_sent_to_razorpay_is_reported_once(self, create, _list):
        create.return_value = rzp_refund(status="pending")
        self.assertEqual(self.cancel(self.cake_part).status_code, 200)
        self.cancel(self.cake_part)  # a double click doesn't refund (or report) twice
        refunds = [e for e in sent_events(self.post) if e["type"] == "refund_issued"]
        self.assertEqual(len(refunds), 1)
        self.assertEqual(
            refunds[0]["meta"], {"gateway": "razorpay", "amount_paise": 74000, "order_ref": str(self.order.pk)}
        )
