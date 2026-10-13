"""Full search (Stage 6): word forms, area, ranking, pages and "Did you mean…?"."""

from django.test import TestCase
from rest_framework.test import APIClient

from catalog.browse import PAGE_SIZE, suggest_query
from core.tests.factories import make_category, make_product, make_seller


def search(query=""):
    return APIClient().get(f"/api/search/{query}").json()


def names(data):
    return [p["name"] for p in data["results"]]


class SearchMatchingTests(TestCase):
    def setUp(self):
        self.cakes, self.pickles = make_category("cakes"), make_category("pickles")
        self.baker = make_seller(name="Asha Bakes", area="Kondapur, Hyderabad")
        self.pickler = make_seller(name="Grandma's Jars", area="Jayanagar, Bengaluru")
        make_product(self.baker, name="Chocolate cake", category=self.cakes)
        make_product(
            self.baker, name="Birthday box", description="A small chocolate cake and candles", category=self.cakes
        )
        make_product(self.pickler, name="Mango pickle", category=self.pickles)

    def test_plural_and_singular_find_the_same_products(self):
        self.assertIn("Chocolate cake", names(search("?q=cakes")))
        self.assertEqual(names(search("?q=pickles")), ["Mango pickle"])

    def test_part_of_a_word_still_matches(self):
        self.assertIn("Chocolate cake", names(search("?q=choco")))

    def test_the_makers_area_is_searched(self):
        self.assertEqual(set(names(search("?q=kondapur"))), {"Chocolate cake", "Birthday box"})
        self.assertEqual(names(search("?q=mango+jayanagar")), ["Mango pickle"])  # every word must match

    def test_name_matches_rank_above_description_matches(self):
        self.assertEqual(names(search("?q=chocolate+cake")), ["Chocolate cake", "Birthday box"])

    def test_filters_and_privacy_still_apply(self):
        make_product(self.baker, name="Hidden cake", is_active=False, category=self.cakes)
        make_product(self.baker, name="Custom: cake for Meera", is_custom=True, category=self.cakes)
        self.assertNotIn("Hidden cake", names(search("?q=cake")))
        self.assertNotIn("Custom: cake for Meera", names(search("?q=cake")))
        self.assertEqual(names(search("?q=cake&category=pickles")), [])


class SearchPageTests(TestCase):
    def setUp(self):
        seller = make_seller()
        for i in range(PAGE_SIZE + 6):
            make_product(seller, name=f"Candle {i}")

    def test_results_come_in_pages_with_a_real_total(self):
        first = search("?q=candle")
        self.assertEqual((first["count"], first["page"], first["pages"]), (PAGE_SIZE + 6, 1, 2))
        self.assertEqual(len(first["results"]), PAGE_SIZE)
        second = search("?q=candle&page=2")
        self.assertEqual(len(second["results"]), 6)
        self.assertFalse(set(names(first)) & set(names(second)))  # no product on both pages

    def test_bad_or_too_big_page_numbers_are_safe(self):
        self.assertEqual(search("?q=candle&page=abc")["page"], 1)
        self.assertEqual(search("?q=candle&page=-3")["page"], 1)
        self.assertEqual(search("?q=candle&page=99")["page"], 2)

    def test_nothing_found(self):
        data = search("?q=sofa")
        self.assertEqual((data["count"], data["pages"], data["results"]), (0, 1, []))


class DidYouMeanTests(TestCase):
    def setUp(self):
        seller = make_seller(name="Asha Bakes")
        make_product(seller, name="Chocolate cake", category=make_category("cakes"))
        make_product(seller, name="Lemon pickle", category=make_category("pickles"))

    def test_a_typo_gets_a_suggestion_that_has_results(self):
        data = search("?q=chocolte")
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["suggestion"], "chocolate")
        self.assertEqual(suggest_query("chocolte cak"), "chocolate cake")

    def test_no_suggestion_when_results_exist_or_nothing_is_close(self):
        self.assertIsNone(search("?q=chocolate")["suggestion"])
        self.assertIsNone(search("?q=sofa")["suggestion"])

    def test_a_suggestion_must_have_results_with_the_same_filters(self):
        # "pickel" -> "pickle" exists, but not in the cakes category, so no suggestion there.
        self.assertEqual(search("?q=pickel")["suggestion"], "pickle")
        self.assertIsNone(search("?q=pickel&category=cakes")["suggestion"])
