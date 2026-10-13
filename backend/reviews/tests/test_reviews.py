from django.test import TestCase
from rest_framework.test import APIClient

from core.tests.factories import make_category, make_paid_order, make_product, make_seller, make_user
from orders.models import SellerOrder
from orders.status import advance_status
from reviews.models import Review
from reviews.services import ReviewError, write_review


def deliver(part):
    owner = part.seller.owner
    for step in ("preparing", "out_for_delivery", "delivered"):
        advance_status(part, step, owner)
    part.refresh_from_db()
    return part


class WriteReviewRuleTests(TestCase):
    """Section 8: a buyer can't review a seller without a delivered order."""

    def setUp(self):
        self.seller = make_seller(main_category=make_category())
        self.buyer = make_user(name="Meera Iyer")
        self.part = make_paid_order(make_product(self.seller), buyer=self.buyer)

    def test_no_order_at_all_is_refused(self):
        with self.assertRaises(ReviewError):
            write_review(make_user(), self.seller, 5, "Lovely")
        self.assertFalse(Review.objects.exists())

    def test_paid_but_not_yet_delivered_is_refused(self):
        for step in ("preparing", "out_for_delivery"):
            with self.assertRaises(ReviewError):
                write_review(self.buyer, self.seller, 5, "")
            advance_status(self.part, step, self.seller.owner)
        with self.assertRaises(ReviewError):
            write_review(self.buyer, self.seller, 5, "")

    def test_cancelled_order_is_refused(self):
        advance_status(self.part, "cancelled", self.seller.owner)
        with self.assertRaises(ReviewError):
            write_review(self.buyer, self.seller, 4, "")

    def test_a_delivered_order_from_another_seller_does_not_count(self):
        other = make_seller(main_category=make_category())
        deliver(make_paid_order(make_product(other), buyer=self.buyer))
        with self.assertRaises(ReviewError):
            write_review(self.buyer, self.seller, 5, "")

    def test_after_delivery_the_buyer_can_review_once_and_then_edit(self):
        deliver(self.part)
        review, created = write_review(self.buyer, self.seller, 4, "  Soft and fresh.  ")
        self.assertTrue(created)
        self.assertEqual((review.rating, review.comment), (4, "Soft and fresh."))
        review, created = write_review(self.buyer, self.seller, 5, "Even better the second time.")
        self.assertFalse(created)
        self.assertEqual(Review.objects.count(), 1)  # one review per buyer per seller: edited, not added
        self.assertEqual(Review.objects.get().rating, 5)

    def test_rating_must_be_a_whole_number_from_1_to_5(self):
        deliver(self.part)
        for bad in (0, 6, -1, 4.5, "5", None, True):
            with self.assertRaises(ReviewError, msg=repr(bad)):
                write_review(self.buyer, self.seller, bad, "")
        self.assertFalse(Review.objects.exists())

    def test_comment_has_a_length_limit(self):
        deliver(self.part)
        with self.assertRaises(ReviewError):
            write_review(self.buyer, self.seller, 5, "x" * 1001)

    def test_a_seller_cannot_review_their_own_shop(self):
        with self.assertRaises(ReviewError):
            write_review(self.seller.owner, self.seller, 5, "Best shop ever")


class ReviewApiTests(TestCase):
    def setUp(self):
        self.seller = make_seller(main_category=make_category(), slug="ammus-kitchen", name="Ammu's Kitchen")
        self.buyer = make_user(name="Meera Iyer")
        self.part = make_paid_order(make_product(self.seller), buyer=self.buyer)
        self.client = APIClient()
        self.client.force_authenticate(self.buyer)

    def post(self, **data):
        return self.client.post("/api/reviews/", {"seller": "ammus-kitchen", **data}, format="json")

    def test_signed_out_cannot_review(self):
        response = APIClient().post("/api/reviews/", {"seller": "ammus-kitchen", "rating": 5}, format="json")
        self.assertIn(response.status_code, (401, 403))

    def test_before_delivery_the_api_refuses_with_a_reason(self):
        response = self.post(rating=5)
        self.assertEqual(response.status_code, 400)
        self.assertIn("delivered", response.json()["detail"])

    def test_review_then_edit_then_it_shows_on_the_store(self):
        deliver(self.part)
        self.assertEqual(self.post(rating=4, comment="Lovely cake").status_code, 201)
        self.assertEqual(self.post(rating=5, comment="Lovely cake!").status_code, 200)
        store = self.client.get("/api/stores/ammus-kitchen/").json()
        self.assertEqual((store["rating"], store["review_count"]), (5.0, 1))
        reviews = self.client.get("/api/stores/ammus-kitchen/reviews/").json()
        self.assertEqual([(r["rating"], r["buyer_name"]) for r in reviews], [(5, "Meera")])  # first name only

    def test_the_buyer_cannot_choose_who_the_review_is_from(self):
        deliver(self.part)
        stranger = make_user()
        self.post(rating=1, buyer=stranger.id, comment="")
        self.assertEqual(Review.objects.get().buyer, self.buyer)

    def test_unknown_shop_is_404(self):
        response = self.client.post("/api/reviews/", {"seller": "nope", "rating": 5}, format="json")
        self.assertEqual(response.status_code, 404)

    def test_order_page_says_when_a_review_can_be_written_and_shows_mine(self):
        order_id = self.part.order_id
        block = self.client.get(f"/api/orders/{order_id}/").json()["seller_orders"][0]
        self.assertEqual((block["can_review"], block["my_review"]), (False, None))
        deliver(self.part)
        self.post(rating=4, comment="Lovely")
        block = self.client.get(f"/api/orders/{order_id}/").json()["seller_orders"][0]
        self.assertTrue(block["can_review"])
        self.assertEqual(block["my_review"]["rating"], 4)
        self.assertEqual(block["my_review"]["comment"], "Lovely")

    def test_average_is_computed_from_all_reviews(self):
        deliver(self.part)
        self.post(rating=5)
        other = make_user(name="Ravi")
        deliver(make_paid_order(make_product(self.seller), buyer=other))
        write_review(other, self.seller, 2, "")
        mine = APIClient()
        mine.force_authenticate(self.seller.owner)
        data = mine.get("/api/seller/reviews/").json()
        self.assertEqual((data["average"], data["count"]), (3.5, 2))
        self.assertEqual(SellerOrder.objects.filter(status="delivered").count(), 2)
