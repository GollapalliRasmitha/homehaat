"""Seller dashboard API: orders, status changes, overview stats, and who may see what (PROMPT.md section 8)."""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from core.tests.factories import make_paid_order, make_product, make_seller, make_user
from orders.models import Order, SellerOrder
from orders.status import advance_status
from reviews.models import Review

S = SellerOrder.Status


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


class SellerOrdersApiTests(TestCase):
    def setUp(self):
        self.seller = make_seller(delivery_fee_paise=4000)
        self.cake = make_product(self.seller, price_paise=45000, stock=10)
        self.part = make_paid_order(self.cake, qty=1)
        self.client = client_for(self.seller.owner)

    def test_lists_only_my_paid_orders_with_a_status_filter(self):
        delivered = make_paid_order(self.cake)
        for step in [S.PREPARING, S.OUT_FOR_DELIVERY, S.DELIVERED]:
            advance_status(delivered, step, self.seller.owner)
        make_paid_order(make_product())  # someone else's order

        all_mine = self.client.get("/api/seller/orders/").data
        only_new = self.client.get("/api/seller/orders/?status=new").data

        self.assertEqual(len(all_mine), 2)
        self.assertEqual([o["id"] for o in only_new], [self.part.id])

    def test_moving_an_order_to_the_next_step(self):
        res = self.client.post(f"/api/seller/orders/{self.part.id}/status/", {"status": "preparing"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "preparing")

    def test_a_disallowed_move_gives_a_clear_error(self):
        res = self.client.post(f"/api/seller/orders/{self.part.id}/status/", {"status": "delivered"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("detail", res.data)

    def test_seller_can_change_only_the_status_never_the_amounts(self):
        body = {"status": "preparing", "subtotal": 1, "delivery_fee": 0, "grand_total": 1}
        self.client.post(f"/api/seller/orders/{self.part.id}/status/", body, format="json")
        self.part.refresh_from_db()
        self.assertEqual((self.part.subtotal, self.part.delivery_fee), (45000, 4000))
        self.assertEqual(self.part.order.grand_total, 49000)

    def test_seller_a_cannot_read_or_move_seller_b_orders(self):
        other = client_for(make_seller().owner)
        self.assertEqual(other.get("/api/seller/orders/").data, [])
        res = other.post(f"/api/seller/orders/{self.part.id}/status/", {"status": "preparing"}, format="json")
        self.assertEqual(res.status_code, 404)
        self.part.refresh_from_db()
        self.assertEqual(self.part.status, S.NEW)

    def test_buyers_cannot_use_seller_endpoints(self):
        buyer = client_for(self.part.order.buyer)
        res = buyer.post(f"/api/seller/orders/{self.part.id}/status/", {"status": "preparing"}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_the_buyer_sees_the_new_status(self):
        advance_status(self.part, S.PREPARING, self.seller.owner)
        res = client_for(self.part.order.buyer).get(f"/api/orders/{self.part.order_id}/")
        self.assertEqual(res.data["seller_orders"][0]["status"], "preparing")


class OverviewTests(TestCase):
    def setUp(self):
        self.seller = make_seller(delivery_fee_paise=4000)
        self.client = client_for(self.seller.owner)

    def test_stats_are_computed_from_real_data(self):
        cake = make_product(self.seller, price_paise=45000, stock=20)
        make_product(self.seller, is_active=False)  # hidden: not "listed"
        recent = make_paid_order(cake, qty=2)  # ₹900 + ₹40
        old = make_paid_order(cake, qty=1)
        Order.objects.filter(pk=old.order_id).update(paid_at=timezone.now() - timedelta(days=9))
        cancelled = make_paid_order(cake, qty=1)
        advance_status(cancelled, S.CANCELLED, self.seller.owner)
        advance_status(recent, S.PREPARING, self.seller.owner)

        stats = self.client.get("/api/seller/overview/").data

        self.assertEqual(stats["earnings_week"], 94000)  # only the recent one: old is >7 days, cancelled excluded
        self.assertEqual(stats["open_orders"], 2)  # recent (preparing) + old (new)
        self.assertEqual(stats["products_listed"], 1)
        self.assertIsNone(stats["rating"])  # no reviews yet: no made-up number
        self.assertEqual(stats["review_count"], 0)
        self.assertEqual({o["id"] for o in stats["incoming"]}, {recent.id, old.id})

    def test_rating_is_the_average_of_real_reviews(self):
        Review.objects.create(seller=self.seller, buyer=make_user(), rating=5)
        Review.objects.create(seller=self.seller, buyer=make_user(), rating=4)
        stats = self.client.get("/api/seller/overview/").data
        self.assertEqual(stats["rating"], 4.5)
        self.assertEqual(stats["review_count"], 2)

    def test_a_new_shop_shows_zeros_not_invented_numbers(self):
        stats = self.client.get("/api/seller/overview/").data
        self.assertEqual(
            (stats["earnings_week"], stats["open_orders"], stats["products_listed"], stats["rating"]), (0, 0, 0, None)
        )


class ReviewsTabTests(TestCase):
    def test_seller_sees_only_their_own_reviews(self):
        seller = make_seller()
        Review.objects.create(seller=seller, buyer=make_user(name="Asha"), rating=5, comment="Lovely")
        Review.objects.create(seller=make_seller(), buyer=make_user(), rating=1)

        data = client_for(seller.owner).get("/api/seller/reviews/").data
        self.assertEqual(data["average"], 5.0)
        self.assertEqual([r["comment"] for r in data["reviews"]], ["Lovely"])
        self.assertEqual(data["reviews"][0]["buyer_name"], "Asha")
