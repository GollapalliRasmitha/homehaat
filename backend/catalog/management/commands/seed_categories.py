from django.core.management.base import BaseCommand

from catalog.models import Category

# The fixed category list. This is the ONLY thing HomeHaat seeds: no sellers, products or orders.
# photo_id = Unsplash photo used for category tiles (free licence, see UI-UX.md section 7).
CATEGORIES = [
    ("cakes", "Cakes & bakes", "blush", "cake", "1588195538326-c5b1e9f80a1b"),
    ("pickles", "Homemade pickles", "sand", "jar", "1618150615391-6d1acab1e561"),
    ("snacks", "Homemade snacks", "linen", "chakli", "1657196118354-f25f29fe636d"),
    ("art", "Art & paintings", "stone", "frame", "1638430323177-8cb2d1febb0c"),
    ("tailoring", "Tailoring", "sage", "spool", "1711318510657-e626bb0c8068"),
    ("crafts", "Crafts & gifts", "mist", "gift", "1707944145479-12755f0434d8"),
    ("jewellery", "Jewellery", "sand", "ring", "1608042314453-ae338d80c427"),
    ("decor", "Home décor", "mist", "pot", "1631125915902-d8abe9225ff2"),
]


class Command(BaseCommand):
    help = "Create or update the fixed list of categories. Safe to run again."

    def handle(self, *args, **options):
        for position, (slug, name, tint, art, photo_id) in enumerate(CATEGORIES):
            # update_or_create makes this safe to run many times: no duplicates.
            Category.objects.update_or_create(
                slug=slug,
                defaults={"name": name, "tint": tint, "art": art, "photo_id": photo_id, "position": position},
            )
        self.stdout.write(self.style.SUCCESS(f"{len(CATEGORIES)} categories ready."))
