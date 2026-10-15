"""
`manage.py seed_showcase`: add the demo shops and products (catalog/showcase_data.py) to the live site [KEY LOGIC].

It only ever CREATES. It never deletes or changes an existing user, shop, product, order or refund:
- a shop whose link (slug) already exists is left alone; if a real seller owns that link, the demo shop is skipped;
- an owner email that already exists without its demo shop is left alone (that shop is skipped);
- a product is created only if that demo shop doesn't already have a product with that name.
So running it twice creates nothing new, and a run cut off halfway is finished by the next run.

Demo owners get an @example.test email and an UNUSABLE password (Django's "!" + random marker: no password can ever
match it), so nobody can sign in as them. No phone, no address. Photos go through clean_image, the same checks as a
seller's upload (real image, resized, EXIF removed), and are stored by the configured storage (Cloudinary online).

Where it may run: production (DEBUG off), or the throwaway copy. Never on the real local data, which is real data only.
On Render, backend/build.sh runs it only when the environment variable SEED_SHOWCASE=true is set.
"""

from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.images import clean_image
from catalog.models import Category, Product, ProductImage, Seller
from catalog.showcase_data import DEMO_NOTE, SHOPS, owner_email
from core.safety import NotThrowawayError, assert_throwaway

PHOTOS = Path(__file__).resolve().parents[2] / "showcase"


def allowed_here() -> bool:
    if not settings.DEBUG:
        return True  # production
    try:
        assert_throwaway()
        return True
    except NotThrowawayError:
        return False


class Command(BaseCommand):
    help = "Create the demo shops and products if they don't exist yet. Never changes or deletes anything."

    def handle(self, *args, **options):
        if not allowed_here():
            raise CommandError(
                "Refusing: seed_showcase adds demo shops. It runs only online (DJANGO_DEBUG off) or on the throwaway "
                "copy, never on your real local data."
            )
        categories = {c.slug: c for c in Category.objects.all()}
        missing = {shop[5] for shop in SHOPS} - set(categories)
        if missing:
            raise CommandError(f"Run seed_categories first (missing: {', '.join(sorted(missing))}).")

        counts = {"shops": 0, "products": 0, "skipped": []}
        for key, owner_name, slug, name, kind, cat_slug, area, fee, days, bio, items in SHOPS:
            seller = self._shop(key, owner_name, slug, name, kind, categories[cat_slug], area, fee, days, bio, counts)
            if seller is None:
                continue
            for product_name, description, price, stock, photo in items:
                if seller.products.filter(name=product_name).exists():
                    continue  # already there (whatever its state now): never touched
                self._product(seller, categories[cat_slug], product_name, description, price, stock, photo)
                counts["products"] += 1

        self.stdout.write(
            self.style.SUCCESS(f"Showcase: {counts['shops']} shop(s) and {counts['products']} product(s) created.")
        )
        for reason in counts["skipped"]:
            self.stdout.write(self.style.WARNING(f"Skipped: {reason}"))

    def _shop(self, key, owner_name, slug, name, kind, category, area, fee, days, bio, counts):
        email = owner_email(key)
        seller = Seller.objects.select_related("owner").filter(slug=slug).first()
        if seller:
            if seller.owner.email != email:
                counts["skipped"].append(f"the shop link '{slug}' belongs to someone else, so {name} wasn't added.")
                return None
            return seller  # our demo shop from an earlier run: only missing products are added
        User = get_user_model()
        if User.objects.filter(email=email).exists():
            counts["skipped"].append(f"{email} already exists without its demo shop; it was left as it is.")
            return None
        with transaction.atomic():  # owner and shop together, or neither
            owner = User.objects.create_user(email, None, name=owner_name, role=User.Role.SELLER)  # unusable password
            seller = Seller.objects.create(
                owner=owner, slug=slug, name=name, kind=kind, main_category=category, area=area,
                delivery_fee_paise=fee, delivery_days=days, bio=f"{DEMO_NOTE} {bio}",
            )  # fmt: skip
        counts["shops"] += 1
        return seller

    def _product(self, seller, category, name, description, price, stock, photo):
        data = (PHOTOS / f"{photo}.jpg").read_bytes()
        with transaction.atomic():  # the product and its photo together; a failed upload leaves no product behind
            product = Product.objects.create(
                seller=seller, category=category, name=name, description=description, price_paise=price, stock=stock
            )
            # Exactly what a seller's upload goes through: decoded, resized, re-saved without EXIF, random file name.
            image = clean_image(SimpleUploadedFile(f"{photo}.jpg", data, content_type="image/jpeg"))
            ProductImage.objects.create(product=product, image=image, position=0)
