"""The AI listing helper (Stage 6). Gemini is always faked here: tests never call the internet."""

import io
import json
from unittest import mock

import requests
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import User
from ai.listing import BLOCKED, BUSY, DAILY_LIMIT, FAILED, ListingError, validate_listing
from catalog.models import ProductImage
from core.tests.factories import make_category, make_product, make_seller, make_user

SLUGS = {"cakes", "pickles", "art"}


class ValidateListingTests(TestCase):
    """The model's answer is never trusted: it is checked and cleaned before the seller sees it."""

    def test_a_good_answer_passes_cleaned(self):
        out = validate_listing(
            {
                "title": "  Chocolate   drip cake ",
                "description": "A round cake with a glossy drip on top.",
                "category": "cakes",
            },
            SLUGS,
        )
        self.assertEqual(
            out,
            {
                "title": "Chocolate drip cake",
                "description": "A round cake with a glossy drip on top.",
                "category": "cakes",
            },
        )

    def test_an_unknown_category_becomes_none_so_the_seller_picks(self):
        out = validate_listing(
            {"title": "Clay lamp", "description": "A small clay lamp painted by hand.", "category": "lamps"}, SLUGS
        )
        self.assertIsNone(out["category"])

    def test_prices_are_never_suggested(self):
        out = validate_listing(
            {
                "title": "Mango pickle ₹250",
                "description": (
                    "Tangy mango pickle in a glass jar. Only ₹250! Rs. 99 for a small jar. Great value at this price."
                ),
                "category": "pickles",
            },
            SLUGS,
        )
        self.assertEqual(out["title"], "Mango pickle")
        self.assertEqual(out["description"], "Tangy mango pickle in a glass jar.")

    def test_sizes_and_weights_are_dropped_unless_the_seller_wrote_them(self):
        answer = {
            "title": "Chocolate cake",
            "description": "A rich chocolate cake. It weighs 1 kg and serves 10 pieces.",
            "category": "cakes",
        }
        self.assertEqual(validate_listing(answer, SLUGS)["description"], "A rich chocolate cake.")
        kept = validate_listing(
            answer | {"description": "A rich chocolate cake. It weighs 1 kg."}, SLUGS, hint="Chocolate cake (1 kg)"
        )
        self.assertEqual(kept["description"], "A rich chocolate cake. It weighs 1 kg.")

    def test_ingredient_and_material_claims_are_dropped_unless_the_seller_wrote_them(self):
        answer = {
            "title": "Floral saree",
            "description": "A saree with a printed floral border. Made from pure silk. Eggless and organic.",
            "category": "art",
        }
        self.assertEqual(validate_listing(answer, SLUGS)["description"], "A saree with a printed floral border.")
        out = validate_listing(
            answer | {"description": "A saree with a floral border. Made from pure silk."},
            SLUGS,
            hint="Pure silk saree",
        )
        self.assertIn("silk", out["description"])

    def test_links_hashtags_and_emoji_are_removed(self):
        out = validate_listing(
            {
                "title": "Clay lamp 🪔",
                "description": "A hand-painted clay lamp. #diwali Visit https://x.y for more.",
                "category": "art",
            },
            SLUGS,
        )
        self.assertEqual(out["title"], "Clay lamp")
        self.assertEqual(out["description"], "A hand-painted clay lamp.")

    def test_long_text_is_cut_at_a_word(self):
        out = validate_listing({"title": "Lovely " * 30, "description": "A lamp. " * 300, "category": "art"}, SLUGS)
        self.assertLessEqual(len(out["title"]), 80)
        self.assertLessEqual(len(out["description"]), 1000)
        self.assertFalse(out["title"].endswith(" "))

    def test_nothing_usable_is_an_error(self):
        for bad in (None, "text", [], {}, {"title": "", "description": ""}, {"title": 5, "description": ["x"]}):
            with self.assertRaises(ListingError, msg=repr(bad)):
                validate_listing(bad, SLUGS)


def jpeg(size=(300, 300)) -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new("RGB", size, "brown").save(buffer, "JPEG")
    return SimpleUploadedFile("cake.jpg", buffer.getvalue(), content_type="image/jpeg")


def gemini_reply(payload, status=200):
    """A fake HTTP response shaped like Gemini's generateContent answer."""
    response = mock.Mock(status_code=status)
    response.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}, "finishReason": "STOP"}]
    }
    return response


def google_error(status, message):
    """A fake error answer shaped like Google's: {"error": {"code", "message", "status"}}."""
    response = mock.Mock(status_code=status)
    response.json.return_value = {"error": {"code": status, "message": message, "status": "ERROR"}}
    return response


def quota_error(quota_id):
    """Google's 429, which names the quota that ran out, e.g. ...PerDay... or ...PerMinute..."""
    response = mock.Mock(status_code=429)
    response.json.return_value = {
        "error": {
            "code": 429,
            "message": "You exceeded your current quota, please check your plan and billing details.",
            "status": "RESOURCE_EXHAUSTED",
            "details": [
                {
                    "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                    "violations": [{"quotaMetric": "generate_content_free_tier_requests", "quotaId": quota_id}],
                }
            ],
        }
    }
    return response


PER_DAY = "GenerateRequestsPerDayPerProjectPerModel-FreeTier"
PER_MINUTE = "GenerateRequestsPerMinutePerProjectPerModel-FreeTier"

GOOD = {
    "title": "Chocolate drip cake",
    "description": "A round chocolate cake with a glossy drip.",
    "category": "cakes",
}


@override_settings(AI_ENABLED=True, GEMINI_API_KEY="test-key-not-real", GEMINI_MODELS=["gemini-test", "gemini-backup"])
class ListingApiTests(TestCase):
    url = "/api/seller/ai/listing/"

    def setUp(self):
        cache.clear()  # rate limits are counted in the cache
        make_category("cakes")
        self.seller = make_seller()
        self.client = APIClient()
        self.client.force_authenticate(self.seller.owner)

    def post(self, **data):
        return self.client.post(self.url, {"image": jpeg(), **data}, format="multipart")

    @mock.patch("ai.gemini_client.requests.post")
    def test_happy_path_returns_a_checked_suggestion(self, post):
        post.return_value = gemini_reply(GOOD | {"description": GOOD["description"] + " Only ₹450."})
        response = self.post(name="Drip cake")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), GOOD)  # the price sentence was removed
        sent = post.call_args
        self.assertEqual(sent.kwargs["headers"]["x-goog-api-key"], "test-key-not-real")
        self.assertNotIn("test-key-not-real", sent.args[0])  # the key never goes in the URL
        body = sent.kwargs["json"]
        schema = body["generationConfig"]["responseSchema"]
        self.assertEqual(set(schema["properties"]), {"title", "description", "category"})  # no price field
        self.assertIn("cakes", schema["properties"]["category"]["enum"])
        self.assertIn("Drip cake", body["contents"][0]["parts"][-1]["text"])  # the seller's own name is a hint

    @mock.patch("ai.gemini_client.requests.post")
    def test_it_can_use_a_photo_already_saved_on_my_product(self, post):
        post.return_value = gemini_reply(GOOD)
        product = make_product(self.seller)
        image = ProductImage.objects.create(product=product, image=jpeg(), position=0)
        response = self.client.post(self.url, {"image_id": image.id}, format="multipart")
        self.assertEqual(response.status_code, 200)

    @mock.patch("ai.gemini_client.requests.post")
    def test_another_sellers_photo_is_not_found(self, post):
        other = make_product(make_seller())
        image = ProductImage.objects.create(product=other, image=jpeg(), position=0)
        response = self.client.post(self.url, {"image_id": image.id}, format="multipart")
        self.assertEqual(response.status_code, 404)
        post.assert_not_called()

    @mock.patch("ai.gemini_client.requests.post")
    def test_a_file_that_is_not_a_photo_is_refused_before_calling_ai(self, post):
        fake = SimpleUploadedFile("x.jpg", b"not an image", content_type="image/jpeg")
        response = self.client.post(self.url, {"image": fake}, format="multipart")
        self.assertEqual(response.status_code, 400)
        post.assert_not_called()

    @mock.patch("ai.gemini_client.requests.post")
    def test_when_gemini_fails_the_seller_gets_the_plain_message(self, post):
        for failure in (
            mock.Mock(return_value=google_error(401, "API key not valid")),  # a key problem: no other model tried
            mock.Mock(return_value=google_error(400, "Bad request")),
            mock.Mock(return_value=gemini_reply({"title": "", "description": ""})),  # nothing usable
        ):
            post.reset_mock()
            post.side_effect, post.return_value = failure.side_effect, failure.return_value
            response = self.post()
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()["detail"], FAILED)
            self.assertEqual(post.call_count, 1)

    @mock.patch("ai.gemini_client.requests.post")
    def test_a_retired_or_busy_model_falls_back_to_the_next_one(self, post):
        for first in (
            google_error(404, "This model is no longer available to new users."),
            google_error(503, "This model is currently experiencing high demand."),
            google_error(429, "Quota exceeded for this model."),
            requests.Timeout("read timed out"),
        ):
            post.reset_mock()
            post.side_effect = [first, gemini_reply(GOOD)]
            response = self.post()
            self.assertEqual(response.status_code, 200, repr(first))
            self.assertEqual(response.json(), GOOD)
            models = [c.args[0].split("/models/")[1].split(":")[0] for c in post.call_args_list]
            self.assertEqual(models, ["gemini-test", "gemini-backup"])

    @mock.patch("ai.gemini_client.time.sleep")
    @mock.patch("ai.gemini_client.requests.post")
    def test_every_model_busy_twice_says_try_again_in_a_minute(self, post, sleep):
        busy = [google_error(503, "high demand"), requests.ConnectionError("down")]
        post.side_effect = busy + busy  # the first round, then the automatic retry
        response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], BUSY)
        self.assertEqual(post.call_count, 4)
        sleep.assert_called_once_with(2)

    @mock.patch("ai.gemini_client.time.sleep")
    @mock.patch("ai.gemini_client.requests.post")
    def test_busy_then_one_automatic_retry_after_2_seconds_succeeds(self, post, sleep):
        post.side_effect = [requests.Timeout("read"), google_error(503, "high demand"), gemini_reply(GOOD)]
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), GOOD)
        sleep.assert_called_once_with(2)
        models = [c.args[0].split("/models/")[1].split(":")[0] for c in post.call_args_list]
        self.assertEqual(models, ["gemini-test", "gemini-backup", "gemini-test"])

    @mock.patch("ai.gemini_client.time.sleep")
    @mock.patch("ai.gemini_client.requests.post")
    def test_daily_free_limit_used_up_says_try_tomorrow_and_does_not_retry(self, post, sleep):
        post.side_effect = [quota_error(PER_DAY), quota_error(PER_DAY)]
        response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], DAILY_LIMIT)
        self.assertEqual(post.call_count, 2)  # each model once; retrying today can't help
        sleep.assert_not_called()

    @mock.patch("ai.gemini_client.time.sleep")
    @mock.patch("ai.gemini_client.requests.post")
    def test_a_per_minute_limit_counts_as_busy_and_is_retried(self, post, sleep):
        post.side_effect = [quota_error(PER_MINUTE), google_error(503, "high demand"), gemini_reply(GOOD)]
        self.assertEqual(self.post().status_code, 200)
        sleep.assert_called_once_with(2)

    @mock.patch("ai.gemini_client.time.sleep")
    @mock.patch("ai.gemini_client.requests.post")
    def test_one_model_out_for_today_and_one_busy_retries_only_the_busy_one(self, post, sleep):
        post.side_effect = [quota_error(PER_DAY), google_error(503, "high demand"), google_error(503, "still busy")]
        response = self.post()
        self.assertEqual(response.json()["detail"], BUSY)  # trying again in a minute may still work
        models = [c.args[0].split("/models/")[1].split(":")[0] for c in post.call_args_list]
        self.assertEqual(models, ["gemini-test", "gemini-backup", "gemini-backup"])

    @mock.patch("ai.gemini_client.time.sleep")
    @mock.patch("ai.gemini_client.requests.post")
    def test_flash_lite_gets_a_longer_timeout(self, post, sleep):
        post.side_effect = [requests.Timeout("read"), gemini_reply(GOOD)]
        with override_settings(GEMINI_MODELS=["gemini-flash-lite-latest", "gemini-flash-latest"]):
            self.assertEqual(self.post().status_code, 200)
        lite, flash = (c.kwargs["timeout"] for c in post.call_args_list)
        self.assertEqual(lite, (5, 20))
        self.assertEqual(flash, (5, 15))

    @mock.patch("ai.gemini_client.time.monotonic")
    @mock.patch("ai.gemini_client.time.sleep")
    @mock.patch("ai.gemini_client.requests.post")
    def test_no_retry_when_the_time_budget_is_used_up(self, post, sleep, monotonic):
        # The clock: 0 s when we start, and 45 s gone once the first model has answered (too late to retry).
        clock = iter([0.0, 0.0, 0.0])
        monotonic.side_effect = lambda: next(clock, 45.0)
        post.side_effect = [requests.Timeout("read"), requests.Timeout("read")]
        response = self.post()
        self.assertEqual(response.json()["detail"], BUSY)
        self.assertEqual(post.call_count, 2)
        sleep.assert_not_called()

    @mock.patch("ai.gemini_client.requests.post")
    def test_a_photo_google_wont_describe_gets_a_clear_message(self, post):
        blocked_prompt = mock.Mock(status_code=200)
        blocked_prompt.json.return_value = {"promptFeedback": {"blockReason": "PROHIBITED_CONTENT"}}
        blocked_answer = mock.Mock(status_code=200)
        blocked_answer.json.return_value = {"candidates": [{"finishReason": "IMAGE_SAFETY"}]}
        for reply in (blocked_prompt, blocked_answer):
            post.reset_mock()
            post.side_effect, post.return_value = None, reply
            response = self.post()
            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json()["detail"], BLOCKED)
            self.assertEqual(post.call_count, 1)  # the same photo isn't sent to another model

    @mock.patch("ai.gemini_client.requests.post")
    def test_the_key_is_never_logged(self, post):
        post.return_value = google_error(400, "API key test-key-not-real is not valid")
        with self.assertLogs("homehaat.ai", level="WARNING") as logs:
            self.post()
        self.assertNotIn("test-key-not-real", str(logs.output))
        self.assertIn("400", str(logs.output))

    @mock.patch("ai.gemini_client.requests.post")
    def test_rate_limited_per_seller(self, post):
        post.return_value = gemini_reply(GOOD)
        for _ in range(10):
            self.assertEqual(self.post().status_code, 200)
        self.assertEqual(self.post().status_code, 429)
        other = APIClient()
        other.force_authenticate(make_seller().owner)
        self.assertEqual(other.post(self.url, {"image": jpeg()}, format="multipart").status_code, 200)

    def test_buyers_and_signed_out_visitors_cannot_use_it(self):
        buyer = APIClient()
        buyer.force_authenticate(make_user(role=User.Role.BUYER))
        self.assertEqual(buyer.post(self.url, {"image": jpeg()}, format="multipart").status_code, 403)
        self.assertIn(APIClient().post(self.url, {"image": jpeg()}, format="multipart").status_code, (401, 403))

    def test_status_says_whether_the_button_should_show(self):
        self.assertEqual(self.client.get(self.url).json(), {"enabled": True})
        with override_settings(AI_ENABLED=False):
            self.assertEqual(self.client.get(self.url).json(), {"enabled": False})
        with override_settings(GEMINI_API_KEY=""):
            self.assertEqual(self.client.get(self.url).json(), {"enabled": False})

    @mock.patch("ai.gemini_client.requests.post")
    def test_switched_off_means_gemini_is_never_called(self, post):
        with override_settings(AI_ENABLED=False):
            response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], FAILED)
        post.assert_not_called()
