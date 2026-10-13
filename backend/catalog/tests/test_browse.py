"""Search, filters, sort, trending, and the public shop pages (Stage 4)."""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from catalog.models import Category
from core.tests.factories import make_category, make_paid_order, make_product, make_seller, make_user
from orders.models import Order, SellerOrder
from orders.status import advance_status
from reviews.models import Review


def get(url):
    return APIClient().get(url).data


def names(products):
    return [p["name"] for p in products]


class SearchAndFilterTests(TestCase):
    def setUp(self):
        self.cakes, self.pickles = make_category("cakes"), make_category("pickles")
        self.baker = make_seller(name="Asha Bakes")
        self.pickler = make_seller(name="Grandma's Jars")
        self.choc = make_product(self.baker, name="Chocolate cake", price_paise=65000, stock=3, category=self.cakes)
        self.carrot = make_product(
            self.baker, name="Carrot cake", description="with walnuts", price_paise=45000, stock=0, category=self.cakes
        )
        self.mango = make_product(self.pickler, name="Mango pickle", price_paise=12000, stock=9, category=self.pickles)

    def test_search_matches_name_description_and_shop_name(self):
        self.assertEqual(set(names(get("/api/products/?q=cake"))), {"Chocolate cake", "Carrot cake"})
        self.assertEqual(names(get("/api/products/?q=walnut")), ["Carrot cake"])
        self.assertEqual(set(names(get("/api/products/?q=asha"))), {"Chocolate cake", "Carrot cake"})
        self.assertEqual(names(get("/api/products/?q=chocolate cake")), ["Chocolate cake"])  # every word must match
        self.assertEqual(get("/api/products/?q=biryani"), [])

    def test_name_matches_come_before_description_matches(self):
        make_product(self.pickler, name="Lemon pickle", description="goes well with cake", category=self.pickles)
        self.assertEqual(names(get("/api/products/?q=cake"))[-1], "Lemon pickle")

    def test_filters(self):
        self.assertEqual(set(names(get("/api/products/?category=pickles"))), {"Mango pickle"})
        self.assertEqual(set(names(get("/api/products/?seller=" + self.baker.slug))), {"Chocolate cake", "Carrot cake"})
        self.assertEqual(set(names(get("/api/products/?in_stock=1"))), {"Chocolate cake", "Mango pickle"})
        self.assertEqual(set(names(get("/api/products/?min_price=20000&max_price=50000"))), {"Carrot cake"})

    def test_sorts(self):
        self.assertEqual(names(get("/api/products/?sort=price_asc")), ["Mango pickle", "Carrot cake", "Chocolate cake"])
        self.assertEqual(names(get("/api/products/?sort=price_desc"))[0], "Chocolate cake")
        self.assertEqual(names(get("/api/products/?sort=newest"))[0], "Mango pickle")

    def test_sort_by_rating_uses_real_reviews_and_puts_unrated_last(self):
        Review.objects.create(seller=self.pickler, buyer=make_user(), rating=5)
        Review.objects.create(seller=self.baker, buyer=make_user(), rating=3)
        unrated = make_seller()
        make_product(unrated, name="Unrated thing")
        self.assertEqual(names(get("/api/products/?sort=rating"))[0], "Mango pickle")
        self.assertEqual(names(get("/api/products/?sort=rating"))[-1], "Unrated thing")

    def test_bad_filter_values_are_ignored_not_errors(self):
        res = APIClient().get("/api/products/?min_price=abc&sort=nonsense&limit=-4")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 3)

    def test_ids_returns_just_those_products(self):  # used by the wishlist
        data = get(f"/api/products/?ids={self.mango.id},{self.choc.id},999999")
        self.assertEqual(set(names(data)), {"Mango pickle", "Chocolate cake"})

    def test_limit(self):
        self.assertEqual(len(get("/api/products/?limit=2")), 2)

    def test_hidden_and_paused_products_never_appear(self):
        make_product(self.baker, name="Secret cake", is_active=False, category=self.cakes)
        make_product(make_seller(is_active=False), name="Paused cake", category=self.cakes)
        self.assertNotIn("Secret cake", names(get("/api/products/?q=cake")))
        self.assertNotIn("Paused cake", names(get("/api/products/?q=cake")))


class TrendingTests(TestCase):
    def test_trending_uses_real_recent_orders_only(self):
        seller = make_seller()
        hot = make_product(seller, name="Hot", stock=20)
        warm = make_product(seller, name="Warm", stock=20)
        old = make_product(seller, name="Old favourite", stock=20)
        make_product(seller, name="Never ordered")
        make_paid_order(hot, qty=3)
        make_paid_order(warm, qty=1)
        stale = make_paid_order(old, qty=5)
        Order.objects.filter(pk=stale.order_id).update(paid_at=timezone.now() - timedelta(days=40))
        cancelled = make_paid_order(warm, qty=9)
        advance_status(cancelled, SellerOrder.Status.CANCELLED, seller.owner)

        self.assertEqual(names(get("/api/products/?sort=trending")), ["Hot", "Warm"])

    def test_no_orders_means_no_trending_section(self):
        make_product()
        self.assertEqual(get("/api/products/?sort=trending"), [])


class CategoryCountTests(TestCase):
    def test_categories_have_live_product_counts(self):
        cakes = make_category("cakes")
        make_category("pickles")
        make_product(category=cakes)
        make_product(category=cakes, is_active=False)  # hidden: not counted
        counts = {c["slug"]: c["product_count"] for c in get("/api/categories/")}
        self.assertEqual(counts, {"cakes": 1, "pickles": 0})


class CategoryOrderTests(TestCase):
    def test_categories_keep_their_fixed_order(self):
        from io import StringIO

        from django.core.management import call_command

        call_command("seed_categories", stdout=StringIO())
        make_product(category=Category.objects.get(slug="decor"))  # counting must not reshuffle them
        self.assertEqual(
            [c["slug"] for c in get("/api/categories/")],
            ["cakes", "pickles", "snacks", "art", "tailoring", "crafts", "jewellery", "decor"],
        )


class PublicStoreTests(TestCase):
    def setUp(self):
        self.store = make_seller(name="Asha Bakes", area="Indiranagar", bio="Home baker")
        make_product(self.store)
        make_product(self.store, is_active=False)

    def test_store_page_data_is_computed(self):
        Review.objects.create(seller=self.store, buyer=make_user(name="Ravi K"), rating=4, comment="Lovely")
        Review.objects.create(seller=self.store, buyer=make_user(), rating=5)
        data = get(f"/api/stores/{self.store.slug}/")
        self.assertEqual(data["name"], "Asha Bakes")
        self.assertEqual(data["product_count"], 1)  # only live products
        self.assertEqual((data["rating"], data["review_count"]), (4.5, 2))
        self.assertNotIn("owner", data)  # no private details

    def test_store_reviews_show_first_names_only(self):
        Review.objects.create(seller=self.store, buyer=make_user(name="Ravi Kumar"), rating=4, comment="Lovely")
        reviews = get(f"/api/stores/{self.store.slug}/reviews/")
        self.assertEqual(reviews[0]["buyer_name"], "Ravi")
        self.assertNotIn("buyer", reviews[0])

    def test_a_new_store_has_no_rating_not_a_made_up_one(self):
        data = get(f"/api/stores/{self.store.slug}/")
        self.assertIsNone(data["rating"])
        self.assertEqual(data["review_count"], 0)

    def test_a_paused_store_is_still_visible_but_not_listed_or_orderable(self):
        # "Pause for holidays or busy weeks. Buyers can still see your shop."
        paused = make_seller(is_active=False, main_category=make_category())
        cake = make_product(paused, name="Paused cake")
        store = APIClient().get(f"/api/stores/{paused.slug}/")
        self.assertEqual(store.status_code, 200)
        self.assertFalse(store.json()["taking_orders"])
        self.assertEqual([p["name"] for p in get(f"/api/products/?seller={paused.slug}")], ["Paused cake"])
        product = APIClient().get(f"/api/products/{cake.id}/").json()
        self.assertFalse(product["seller"]["taking_orders"])
        # not in lists or search, and it can't be bought
        self.assertNotIn(paused.slug, [s["slug"] for s in get("/api/stores/")])
        self.assertNotIn("Paused cake", names(get("/api/products/?q=cake")))
        buyer = APIClient()
        buyer.force_authenticate(make_user())
        res = buyer.post("/api/cart/items/", {"product_id": cake.id, "qty": 1}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("isn't taking orders", res.json()["detail"])
        self.assertTrue(get(f"/api/stores/{self.store.slug}/")["taking_orders"])

    def test_makers_list_and_search(self):
        make_seller(name="Grandma's Jars", area="Jayanagar")
        self.assertEqual(len(get("/api/stores/")), 2)
        self.assertEqual([s["name"] for s in get("/api/stores/?q=jars")], ["Grandma's Jars"])
        self.assertEqual([s["name"] for s in get("/api/stores/?q=jayanagar")], ["Grandma's Jars"])

    def test_cover_falls_back_to_main_category_photo_info(self):
        self.store.main_category = Category.objects.get_or_create(
            slug="cakes", defaults={"name": "Cakes", "tint": "blush", "art": "cake", "photo_id": "abc"}
        )[0]
        self.store.save()
        data = get(f"/api/stores/{self.store.slug}/")
        self.assertIsNone(data["cover"])
        self.assertEqual(data["main_category"]["photo_id"], self.store.main_category.photo_id)
