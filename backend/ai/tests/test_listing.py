"""The AI listing helper (Stage 6). Gemini is always faked here: tests never call the internet."""

import io
import json
from unittest import mock

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import User
from ai.gemini_client import GeminiError
from ai.listing import FAILED, ListingError, validate_listing
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


GOOD = {
    "title": "Chocolate drip cake",
    "description": "A round chocolate cake with a glossy drip.",
    "category": "cakes",
}


@override_settings(AI_ENABLED=True, GEMINI_API_KEY="test-key-not-real", GEMINI_MODEL="gemini-test")
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
            mock.Mock(side_effect=GeminiError("timeout")),
            mock.Mock(return_value=mock.Mock(status_code=429, json=mock.Mock(return_value={}))),  # free limit used up
            mock.Mock(return_value=gemini_reply({"title": "", "description": ""})),  # nothing usable
        ):
            post.side_effect, post.return_value = failure.side_effect, failure.return_value
            response = self.post()
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()["detail"], FAILED)

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
