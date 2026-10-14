"""
[KEY LOGIC] Custom requests: who may do what, and accepting a quote -> a bag item at the quoted price.
Written before the code, as the brief asks.

    open --seller quotes--> quoted --buyer accepts--> accepted (one-off product in the buyer's bag)
    open --seller declines--> declined
    quoted --buyer declines--> declined
"""

from django.test import TestCase
from rest_framework.test import APIClient

from cart.models import CartItem
from catalog.models import Product
from core.media import public_url
from core.tests.factories import add_to_cart, make_address, make_category, make_product, make_seller, make_user
from custom_requests.models import CustomRequest
from custom_requests.services import NotYourRequestError, RequestError, add_quote_to_bag, apply_action
from orders.services import create_order_from_cart

R = CustomRequest.Status


class CustomRequestRuleTests(TestCase):
    def setUp(self):
        self.seller = make_seller(delivery_fee_paise=4000, main_category=make_category("cakes"))
        self.buyer = make_user()
        self.req = CustomRequest.objects.create(
            buyer=self.buyer, seller=self.seller, description="Photo cake with my dog on it, 1 kg, for Saturday"
        )

    def quote(self, paise=120000, note="Includes the edible photo"):
        return apply_action(self.req, self.seller.owner, "quote", quote_paise=paise, note=note)

    # --- quoting ---

    def test_seller_sends_a_quote(self):
        self.quote()
        self.req.refresh_from_db()
        self.assertEqual(
            (self.req.status, self.req.quote_paise, self.req.seller_note),
            (R.QUOTED, 120000, "Includes the edible photo"),
        )
        self.assertIsNotNone(self.req.responded_at)

    def test_a_quote_must_be_at_least_one_rupee(self):
        for bad in (None, 0, 99):
            with self.assertRaises(RequestError):
                self.quote(paise=bad)
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, R.OPEN)

    def test_only_the_shops_seller_can_quote(self):
        with self.assertRaises(RequestError):
            apply_action(self.req, self.buyer, "quote", quote_paise=50000)  # the buyer can't quote themselves
        with self.assertRaises(NotYourRequestError):
            apply_action(self.req, make_seller().owner, "quote", quote_paise=50000)  # another shop
        with self.assertRaises(NotYourRequestError):
            apply_action(self.req, make_user(), "decline")  # a stranger

    def test_a_quote_cannot_be_changed_once_sent(self):
        self.quote()
        with self.assertRaises(RequestError):
            self.quote(paise=1)

    # --- declining ---

    def test_seller_can_decline_an_open_request(self):
        apply_action(self.req, self.seller.owner, "decline")
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, R.DECLINED)

    def test_buyer_can_decline_a_quote(self):
        self.quote()
        apply_action(self.req, self.buyer, "decline")
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, R.DECLINED)

    def test_buyer_cannot_decline_before_a_quote_and_seller_cannot_decline_after_quoting(self):
        with self.assertRaises(RequestError):
            apply_action(self.req, self.buyer, "decline")  # buyers wait for a quote
        self.quote()
        with self.assertRaises(RequestError):
            apply_action(self.req, self.seller.owner, "decline")  # the quote is the seller's answer

    # --- accepting ---

    def test_accepting_puts_a_one_off_product_at_the_quoted_price_in_the_buyers_bag(self):
        self.quote(paise=120000)
        apply_action(self.req, self.buyer, "accept")

        self.req.refresh_from_db()
        self.assertEqual(self.req.status, R.ACCEPTED)
        product = self.req.product
        self.assertTrue(product.is_custom)
        self.assertEqual((product.seller, product.price_paise, product.stock), (self.seller, 120000, 1))
        self.assertTrue(product.name.startswith("Custom: "))
        item = CartItem.objects.get(user=self.buyer)
        self.assertEqual((item.product, item.qty, item.custom_request), (product, 1, self.req))

    def test_the_custom_item_checks_out_at_the_quoted_price(self):
        self.quote(paise=120000)
        apply_action(self.req, self.buyer, "accept")
        order = create_order_from_cart(self.buyer, make_address(self.buyer))
        self.assertEqual(order.grand_total, 120000 + 4000)  # quote + the shop's delivery fee
        self.assertEqual(order.seller_orders.get().items.get().unit_price, 120000)

    def test_only_the_buyer_can_accept_and_only_a_quoted_request(self):
        with self.assertRaises(RequestError):
            apply_action(self.req, self.buyer, "accept")  # nothing to accept yet
        self.quote()
        with self.assertRaises(RequestError):
            apply_action(self.req, self.seller.owner, "accept")  # a seller can't accept their own quote
        with self.assertRaises(NotYourRequestError):
            apply_action(self.req, make_user(), "accept")

    def test_accepted_and_declined_are_final(self):
        self.quote()
        apply_action(self.req, self.buyer, "accept")
        for user, action in [(self.buyer, "accept"), (self.buyer, "decline"), (self.seller.owner, "decline")]:
            with self.assertRaises(RequestError):
                apply_action(self.req, user, action)
        self.assertEqual(Product.objects.filter(is_custom=True).count(), 1)  # no second product

    def test_cannot_accept_while_the_shop_is_paused(self):
        self.quote()
        self.seller.is_active = False
        self.seller.save()
        with self.assertRaises(RequestError):
            apply_action(self.req, self.buyer, "accept")
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, R.QUOTED)

    def test_unknown_action_is_rejected(self):
        with self.assertRaises(RequestError):
            apply_action(self.req, self.seller.owner, "delete")

    # --- the one-off product stays private ---

    def test_nobody_else_can_find_or_buy_the_custom_product(self):
        self.quote()
        apply_action(self.req, self.buyer, "accept")
        self.req.refresh_from_db()
        product = self.req.product
        public = APIClient()
        self.assertEqual(public.get(f"/api/products/{product.id}/").status_code, 404)
        self.assertNotIn(product.id, [p["id"] for p in public.get("/api/products/").data])
        other = APIClient()
        other.force_authenticate(make_user())
        self.assertEqual(other.post("/api/cart/items/", {"product_id": product.id}, format="json").status_code, 404)
        seller = APIClient()
        seller.force_authenticate(self.seller.owner)
        self.assertNotIn(product.id, [p["id"] for p in seller.get("/api/seller/products/").data])

    # --- back into the bag ---

    def test_add_to_bag_again_after_removing_it_without_duplicates(self):
        self.quote()
        apply_action(self.req, self.buyer, "accept")
        CartItem.objects.filter(user=self.buyer).delete()  # the buyer removed it

        add_quote_to_bag(self.req, self.buyer)
        add_quote_to_bag(self.req, self.buyer)  # twice: still one line
        self.assertEqual(CartItem.objects.filter(user=self.buyer).count(), 1)

    def test_cannot_add_again_once_it_is_bought(self):
        self.quote()
        apply_action(self.req, self.buyer, "accept")
        add_to_cart(self.buyer, make_product(self.seller))  # something else too
        create_order_from_cart(self.buyer, make_address(self.buyer))  # holds the one custom item: stock 1 -> 0
        CartItem.objects.filter(user=self.buyer).delete()
        with self.assertRaises(RequestError):
            add_quote_to_bag(self.req, self.buyer)


class ReferencePhotoAsItemImageTests(TestCase):
    """The buyer's first reference photo becomes the one-off item's picture (bag, checkout, orders)."""

    def setUp(self):
        import tempfile

        self.media = tempfile.mkdtemp(prefix="homehaat-test-refphoto-")
        self.override = self.settings(MEDIA_ROOT=self.media)
        self.override.enable()
        self.seller = make_seller(main_category=make_category("cakes"))
        self.buyer = make_user()
        self.req = CustomRequest.objects.create(
            buyer=self.buyer, seller=self.seller, description="A cake shaped like our house, for Sunday lunch"
        )

    def tearDown(self):
        import shutil

        self.override.disable()
        shutil.rmtree(self.media, ignore_errors=True)

    def add_photo(self, position):
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        from catalog.images import clean_image
        from custom_requests.models import CustomRequestImage

        buf = io.BytesIO()
        Image.new("RGB", (200, 200), (10 * position, 80, 60)).save(buf, "JPEG")
        upload = SimpleUploadedFile("ref.jpg", buf.getvalue(), content_type="image/jpeg")
        return CustomRequestImage.objects.create(request=self.req, image=clean_image(upload), position=position)

    def accept(self):
        apply_action(self.req, self.seller.owner, "quote", quote_paise=150000)
        apply_action(self.req, self.buyer, "accept")
        self.req.refresh_from_db()

    def test_first_reference_photo_becomes_the_items_image(self):
        second = self.add_photo(1)
        first = self.add_photo(0)
        self.accept()

        self.assertEqual(self.req.product.images.count(), 1)
        self.assertEqual(self.req.product.images.get().image.name, first.image.name)  # position 0, not upload order
        self.assertNotEqual(first.image.name, second.image.name)

        client = APIClient()
        client.force_authenticate(self.buyer)
        line = client.get("/api/cart/").data["groups"][0]["items"][0]
        self.assertEqual(line["product"]["image"], public_url(first.image))  # bag (and checkout): the private route

    def test_no_reference_photo_means_no_image_so_the_drawing_shows(self):
        self.accept()
        self.assertEqual(self.req.product.images.count(), 0)

    def test_orders_show_it_to_that_buyer_and_that_seller_only(self):
        first = self.add_photo(0)
        self.accept()
        order = create_order_from_cart(self.buyer, make_address(self.buyer))
        from payments.webhook import mark_order_paid

        mark_order_paid(order, "pay_ref", order.grand_total)

        buyer = APIClient()
        buyer.force_authenticate(self.buyer)
        item = buyer.get(f"/api/orders/{order.id}/").data["seller_orders"][0]["items"][0]
        self.assertEqual(item["image"], public_url(first.image))
        self.assertEqual((item["tint"], item["art"]), ("blush", "cake"))  # fallback drawing info

        seller = APIClient()
        seller.force_authenticate(self.seller.owner)
        self.assertEqual(seller.get("/api/seller/orders/").data[0]["items"][0]["image"], public_url(first.image))

        stranger = APIClient()
        stranger.force_authenticate(make_user())
        self.assertEqual(stranger.get(f"/api/orders/{order.id}/").status_code, 404)
        other_seller = APIClient()
        other_seller.force_authenticate(make_seller().owner)
        self.assertEqual(other_seller.get("/api/seller/orders/").data, [])
        self.assertEqual(APIClient().get(f"/api/products/{self.req.product.id}/").status_code, 404)
