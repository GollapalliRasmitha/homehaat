"""Delivery address rules: Indian pincode and mobile number, and real words in the address and city."""

from unittest import mock

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.address_rules import address_problems, normalize_phone
from accounts.models import Address
from core.tests.factories import add_to_cart, make_address, make_product, make_user

GOOD = {
    "name": "Asha Rao",
    "phone": "9876543210",
    "line1": "12 MG Road",
    "line2": "",
    "city": "Bengaluru",
    "pincode": "560001",
}


class RuleTests(TestCase):
    def test_a_good_address_has_no_problems(self):
        self.assertEqual(address_problems(GOOD), {})

    def test_pincode_is_6_digits_not_starting_with_0(self):
        for bad in ("56000", "5600011", "060001", "000000", "56 0001x", "abcdef", ""):
            self.assertIn("pincode", address_problems(GOOD | {"pincode": bad}), bad)
        self.assertEqual(address_problems(GOOD | {"pincode": "110001"}), {})

    def test_phone_is_an_indian_mobile_starting_6_to_9(self):
        for bad in (
            "5876543210",
            "0876543210",
            "987654321",
            "98765432100",
            "98765abcde",
            "1111111111",
            "9999999999",
            "",
        ):
            self.assertIn("phone", address_problems(GOOD | {"phone": bad}), bad)
        for good in ("6000000000", "7012345678", "8123456789", "9876543210"):
            self.assertEqual(address_problems(GOOD | {"phone": good}), {}, good)

    def test_common_ways_of_typing_a_number_are_accepted_and_cleaned(self):
        for typed in ("+91 98765 43210", "+919876543210", "91-98765-43210", "098765 43210", "98765-43210"):
            self.assertEqual(normalize_phone(typed), "9876543210", typed)
        self.assertEqual(normalize_phone("+1 415 555 0100"), "+1 415 555 0100")  # not Indian: left as is, then refused

    def test_address_and_city_need_real_letters(self):
        for bad in ("!!!", "---", "12/34", "#@*&", ".", "  ", "ab"):
            self.assertIn("line1", address_problems(GOOD | {"line1": bad}), bad)
        for bad in ("???", "123", "--", "x"):
            self.assertIn("city", address_problems(GOOD | {"city": bad}), bad)
        self.assertEqual(address_problems(GOOD | {"line1": "Flat 4B, 2nd Cross", "city": "Ooty"}), {})
        self.assertEqual(address_problems(GOOD | {"city": "बेंगलुरु"}), {})  # letters in any script count

    def test_name_and_optional_second_line(self):
        self.assertIn("name", address_problems(GOOD | {"name": "@@"}))
        self.assertIn("line2", address_problems(GOOD | {"line2": "%%%"}))  # optional, but not only symbols
        self.assertEqual(address_problems(GOOD | {"line2": "Near the temple"}), {})


class AddressApiTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_each_bad_field_gets_its_own_message(self):
        bad = {"name": "A R", "phone": "5876543210", "line1": "!!!", "city": "123", "pincode": "012345"}
        res = self.client.post("/api/addresses/", bad, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(set(res.data), {"phone", "line1", "city", "pincode"})
        self.assertIn("6, 7, 8 or 9", str(res.data["phone"]))
        self.assertFalse(Address.objects.exists())

    def test_phone_is_saved_as_10_digits(self):
        res = self.client.post("/api/addresses/", GOOD | {"phone": "+91 98765 43210"}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Address.objects.get().phone, "9876543210")
        self.assertEqual(res.data["problems"], {})

    def test_an_old_address_that_breaks_the_rules_is_flagged_and_can_be_fixed(self):
        old = make_address(self.user, phone="1234567890", pincode="012345")  # saved before the rules
        listed = self.client.get("/api/addresses/").data[0]
        self.assertEqual(set(listed["problems"]), {"phone", "pincode"})
        res = self.client.patch(f"/api/addresses/{old.id}/", {"phone": "9876543210"}, format="json")
        self.assertEqual(res.status_code, 400)  # the pincode is still wrong, so nothing is saved
        res = self.client.patch(
            f"/api/addresses/{old.id}/", {"phone": "9876543210", "pincode": "560001"}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["problems"], {})

    def test_you_cannot_edit_someone_elses_address(self):
        other = make_address(make_user())
        res = self.client.patch(f"/api/addresses/{other.id}/", {"city": "Mysuru"}, format="json")
        self.assertEqual(res.status_code, 404)
        other.refresh_from_db()
        self.assertEqual(other.city, "Bengaluru")


@mock.patch("orders.views.razorpay_client.create_order", return_value={"id": "order_test_1"})
class CheckoutAddressTests(TestCase):
    def setUp(self):
        self.buyer = make_user(name="Asha Rao")
        add_to_cart(self.buyer, make_product())
        self.client = APIClient()
        self.client.force_authenticate(self.buyer)

    def test_checkout_refuses_an_address_that_needs_updating(self, create_order):
        old = make_address(self.buyer, phone="1234567890")
        res = self.client.post("/api/checkout/", {"address_id": old.id}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("phone", res.data["address_problems"])
        create_order.assert_not_called()  # no order, no stock held, no Razorpay order

    def test_the_delivery_phone_is_always_the_razorpay_contact(self, create_order):
        address = make_address(self.buyer, phone="7012345678")
        self.buyer.phone = "9999999999"  # the profile phone is NOT used
        self.buyer.save()
        res = self.client.post("/api/checkout/", {"address_id": address.id}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["prefill"]["contact"], "+917012345678")
        self.assertEqual(res.data["prefill"]["email"], self.buyer.email)
