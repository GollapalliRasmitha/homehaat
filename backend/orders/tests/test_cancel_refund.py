"""Buyer cancellation, seller cancellation and Razorpay partial refunds (Razorpay is always faked here)."""

import hashlib
import hmac
import json
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from catalog.models import Product
from core.tests.factories import add_to_cart, make_address, make_category, make_product, make_seller, make_user
from orders.models import Refund, SellerOrder
from orders.services import create_order_from_cart
from orders.status import advance_status
from payments.razorpay_client import RazorpayError
from payments.webhook import mark_order_paid

RZP = "payments.refunds.razorpay_client"


def client_for(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


def rzp_refund(refund_id="rfnd_1", status="processed", part_id=None):
    return {"id": refund_id, "entity": "refund", "status": status, "notes": {"homehaat_part": str(part_id or "")}}


class CancelSetup(TestCase):
    """One paid order from two makers: a cake (₹700 + ₹40 delivery) and a jar (₹300 + ₹30)."""

    def setUp(self):
        self.baker = make_seller(main_category=make_category("cakes"), delivery_fee_paise=4000)
        self.pickler = make_seller(main_category=make_category("pickles"), delivery_fee_paise=3000)
        self.cake = make_product(self.baker, price_paise=70000, stock=5)
        self.jar = make_product(self.pickler, price_paise=30000, stock=5)
        self.buyer = make_user()
        add_to_cart(self.buyer, self.cake)
        add_to_cart(self.buyer, self.jar)
        self.order = create_order_from_cart(self.buyer, make_address(self.buyer))
        mark_order_paid(self.order, "pay_test_1", self.order.grand_total)
        self.cake_part = self.order.seller_orders.get(seller=self.baker)
        self.jar_part = self.order.seller_orders.get(seller=self.pickler)
        self.me = client_for(self.buyer)

    def cancel(self, part, client=None):
        with self.captureOnCommitCallbacks(execute=True):  # the refund is sent once the cancel is saved
            return (client or self.me).post(f"/api/orders/parts/{part.id}/cancel/")


@mock.patch(f"{RZP}.list_refunds", return_value=[])
@mock.patch(f"{RZP}.create_refund")
class BuyerCancelTests(CancelSetup):
    def test_buyer_cancels_a_new_part_and_gets_exactly_that_part_refunded(self, create, _list):
        create.return_value = rzp_refund(status="pending")
        r = self.cancel(self.cake_part)
        self.assertEqual(r.status_code, 200, r.content)
        self.cake_part.refresh_from_db()
        self.assertEqual((self.cake_part.status, self.cake_part.cancelled_by), ("cancelled", "buyer"))
        refund = Refund.objects.get(seller_order=self.cake_part)
        self.assertEqual(refund.amount, 70000 + 4000)  # the cake + THAT maker's delivery fee, nothing else
        self.assertEqual((refund.status, refund.razorpay_refund_id), ("pending", "rfnd_1"))
        kwargs = create.call_args.kwargs
        self.assertEqual((kwargs["payment_id"], kwargs["amount_paise"]), ("pay_test_1", 74000))
        self.cake.refresh_from_db()
        self.assertEqual(self.cake.stock, 5)  # back on the shelf
        self.jar_part.refresh_from_db()
        self.assertEqual(self.jar_part.status, "new")  # the other maker's part is untouched
        block = next(p for p in r.json()["seller_orders"] if p["id"] == self.cake_part.id)
        self.assertEqual(block["refund"], {"amount": 74000, "status": "pending"})

    def test_double_click_or_retry_makes_one_refund_only(self, create, _list):
        create.return_value = rzp_refund()
        self.cancel(self.cake_part)
        second = self.cancel(self.cake_part)
        self.assertEqual(second.status_code, 200)  # already cancelled: nothing more to do, not an error
        self.assertEqual(Refund.objects.count(), 1)
        self.assertEqual(create.call_count, 1)

    def test_an_amount_in_the_request_is_ignored(self, create, _list):
        create.return_value = rzp_refund()
        with self.captureOnCommitCallbacks(execute=True):
            self.me.post(f"/api/orders/parts/{self.cake_part.id}/cancel/", {"amount": 100}, format="json")
        self.assertEqual(Refund.objects.get().amount, 74000)

    def test_preparing_needs_a_request_and_the_seller_decides(self, create, _list):
        create.return_value = rzp_refund()
        advance_status(self.cake_part, "preparing", self.baker.owner)
        self.assertEqual(self.cancel(self.cake_part).status_code, 400)  # not instantly
        r = self.me.post(f"/api/orders/parts/{self.cake_part.id}/request-cancel/")
        self.assertEqual(r.status_code, 200)
        seller = client_for(self.baker.owner)
        incoming = next(o for o in seller.get("/api/seller/orders/").json() if o["id"] == self.cake_part.id)
        self.assertTrue(incoming["cancel_requested"])
        with self.captureOnCommitCallbacks(execute=True):
            r = seller.post(f"/api/seller/orders/{self.cake_part.id}/cancel-request/", {"accept": True}, format="json")
        self.assertEqual(r.status_code, 200)
        self.cake_part.refresh_from_db()
        self.assertEqual((self.cake_part.status, self.cake_part.cancelled_by), ("cancelled", "buyer"))
        self.assertEqual(Refund.objects.get().amount, 74000)

    def test_seller_can_decline_a_cancellation_request(self, create, _list):
        advance_status(self.cake_part, "preparing", self.baker.owner)
        self.me.post(f"/api/orders/parts/{self.cake_part.id}/request-cancel/")
        seller = client_for(self.baker.owner)
        r = seller.post(f"/api/seller/orders/{self.cake_part.id}/cancel-request/", {"accept": False}, format="json")
        self.assertEqual(r.status_code, 200)
        self.cake_part.refresh_from_db()
        self.assertEqual(self.cake_part.status, "preparing")
        block = next(
            p
            for p in self.me.get(f"/api/orders/{self.order.id}/").json()["seller_orders"]
            if p["id"] == self.cake_part.id
        )
        self.assertEqual(
            (block["cancel_requested"], block["cancel_declined"], block["can_request_cancel"]), (False, True, False)
        )
        self.assertFalse(Refund.objects.exists())
        create.assert_not_called()

    def test_no_cancel_after_out_for_delivery(self, create, _list):
        for step in ("preparing", "out_for_delivery"):
            advance_status(self.cake_part, step, self.baker.owner)
        self.assertEqual(self.cancel(self.cake_part).status_code, 400)
        self.assertEqual(self.me.post(f"/api/orders/parts/{self.cake_part.id}/request-cancel/").status_code, 400)
        block = next(
            p
            for p in self.me.get(f"/api/orders/{self.order.id}/").json()["seller_orders"]
            if p["id"] == self.cake_part.id
        )
        self.assertEqual((block["can_cancel"], block["can_request_cancel"]), (False, False))
        create.assert_not_called()

    def test_custom_items_can_be_cancelled_only_while_new(self, create, _list):
        create.return_value = rzp_refund()
        Product.objects.filter(pk=self.cake.pk).update(is_custom=True)
        block = next(
            p
            for p in self.me.get(f"/api/orders/{self.order.id}/").json()["seller_orders"]
            if p["id"] == self.cake_part.id
        )
        self.assertTrue(block["can_cancel"])
        advance_status(self.cake_part, "preparing", self.baker.owner)
        r = self.me.post(f"/api/orders/parts/{self.cake_part.id}/request-cancel/")
        self.assertEqual(r.status_code, 400)
        self.assertIn("custom", r.json()["detail"].lower())

    def test_only_the_buyer_of_that_order_can_cancel(self, create, _list):
        for other in (make_user(), self.pickler.owner, self.baker.owner):
            self.assertEqual(self.cancel(self.cake_part, client_for(other)).status_code, 404)
        self.assertEqual(APIClient().post(f"/api/orders/parts/{self.cake_part.id}/cancel/").status_code, 403)
        self.cake_part.refresh_from_db()
        self.assertEqual(self.cake_part.status, "new")

    def test_an_unpaid_order_cannot_be_cancelled_this_way(self, create, _list):
        buyer = make_user()
        add_to_cart(buyer, self.cake)
        pending = create_order_from_cart(buyer, make_address(buyer)).seller_orders.get()
        self.assertEqual(self.cancel(pending, client_for(buyer)).status_code, 400)


@mock.patch(f"{RZP}.list_refunds", return_value=[])
@mock.patch(f"{RZP}.create_refund")
class SellerCancelAndRetryTests(CancelSetup):
    def test_a_seller_cancel_refunds_that_part_too(self, create, _list):
        create.return_value = rzp_refund(status="processed")
        with self.captureOnCommitCallbacks(execute=True):
            r = client_for(self.pickler.owner).post(
                f"/api/seller/orders/{self.jar_part.id}/status/", {"status": "cancelled"}, format="json"
            )
        self.assertEqual(r.status_code, 200)
        refund = Refund.objects.get()
        self.assertEqual((refund.seller_order_id, refund.amount, refund.status), (self.jar_part.id, 33000, "processed"))
        self.assertEqual(r.json()["refund"]["amount"], 33000)  # the seller's card shows the refund right away
        self.jar_part.refresh_from_db()
        self.assertEqual(self.jar_part.cancelled_by, "seller")

    def test_a_failed_refund_is_kept_listed_and_retried(self, create, _list):
        create.side_effect = RazorpayError("Razorpay said 500")
        self.cancel(self.cake_part)
        refund = Refund.objects.get()
        self.assertEqual((refund.status, refund.attempts), ("failed", 1))
        self.assertIn("500", refund.last_error)
        overview = client_for(self.baker.owner).get("/api/seller/overview/").json()
        self.assertEqual(
            overview["refund_problems"],
            [{"order_id": self.order.id, "seller_order_id": self.cake_part.id, "amount": 74000}],
        )
        create.side_effect, create.return_value = None, rzp_refund(status="processed")
        call_command("retry_refunds", stdout=StringIO())
        refund.refresh_from_db()
        self.assertEqual((refund.status, refund.razorpay_refund_id, refund.attempts), ("processed", "rfnd_1", 2))
        self.assertEqual(client_for(self.baker.owner).get("/api/seller/overview/").json()["refund_problems"], [])

    def test_a_refund_razorpay_already_made_is_reused_not_sent_again(self, create, list_refunds):
        # Razorpay made the refund but we didn't hear back (timeout): the retry finds it instead of refunding twice.
        create.side_effect = RazorpayError("Couldn't reach Razorpay: timeout")
        self.cancel(self.cake_part)
        list_refunds.return_value = [
            rzp_refund("rfnd_other", part_id=999),
            rzp_refund("rfnd_mine", "pending", self.cake_part.id),
        ]
        create.reset_mock()
        call_command("retry_refunds", stdout=StringIO())
        refund = Refund.objects.get()
        self.assertEqual((refund.razorpay_refund_id, refund.status), ("rfnd_mine", "pending"))
        create.assert_not_called()

    @mock.patch(f"{RZP}.fetch_refund")
    def test_retry_also_updates_pending_refunds(self, fetch, create, _list):
        create.return_value = rzp_refund(status="pending")
        self.cancel(self.cake_part)
        fetch.return_value = rzp_refund(status="processed")
        call_command("retry_refunds", stdout=StringIO())
        self.assertEqual(Refund.objects.get().status, "processed")

    def test_late_payment_sold_out_also_refunds(self, create, _list):
        create.return_value = rzp_refund()
        buyer = make_user()
        last = make_product(self.baker, stock=1)
        add_to_cart(buyer, last)
        order = create_order_from_cart(buyer, make_address(buyer))
        from orders.services import release_hold

        release_hold(order)  # the 15 minutes ran out...
        Product.objects.filter(pk=last.pk).update(stock=0)  # ...and someone else bought the last one
        with self.captureOnCommitCallbacks(execute=True):
            mark_order_paid(order, "pay_late", order.grand_total)
        part = order.seller_orders.get()
        self.assertEqual((part.status, part.cancelled_by), ("cancelled", "system"))
        self.assertEqual(Refund.objects.get(seller_order=part).amount, part.subtotal + part.delivery_fee)

    def test_refunds_are_in_django_admin(self, create, _list):
        from django.contrib import admin

        self.assertIn(Refund, admin.site._registry)


@override_settings(RAZORPAY_WEBHOOK_SECRET="whsec_test")
class RefundWebhookTests(CancelSetup):
    def setUp(self):
        super().setUp()
        self.refund = Refund.objects.create(
            seller_order=self.cake_part, amount=74000, status="pending", razorpay_refund_id="rfnd_9"
        )

    def send(self, event, entity, secret="whsec_test"):
        body = json.dumps({"event": event, "payload": {"refund": {"entity": entity}}}).encode()
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return APIClient().post(
            "/api/payments/webhook/", body, content_type="application/json", HTTP_X_RAZORPAY_SIGNATURE=sig
        )

    def test_refund_processed(self):
        r = self.send("refund.processed", {"id": "rfnd_9", "status": "processed"})
        self.assertEqual(r.status_code, 200)
        self.refund.refresh_from_db()
        self.assertEqual(self.refund.status, "processed")
        self.assertIsNotNone(self.refund.processed_at)

    def test_refund_failed_is_marked_for_a_retry(self):
        self.send("refund.failed", {"id": "rfnd_9", "status": "failed"})
        self.refund.refresh_from_db()
        self.assertEqual((self.refund.status, self.refund.razorpay_refund_id), ("failed", None))
        self.assertIn("rfnd_9", self.refund.last_error)

    def test_a_bad_signature_changes_nothing(self):
        r = self.send("refund.processed", {"id": "rfnd_9", "status": "processed"}, secret="wrong")
        self.assertEqual(r.status_code, 400)
        self.refund.refresh_from_db()
        self.assertEqual(self.refund.status, "pending")

    def test_an_unknown_refund_is_ignored(self):
        self.assertEqual(self.send("refund.processed", {"id": "rfnd_unknown", "status": "processed"}).status_code, 200)
        self.assertEqual(SellerOrder.objects.get(pk=self.cake_part.pk).status, "new")
