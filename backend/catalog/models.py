from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Category(models.Model):
    """A fixed list, created by `python manage.py seed_categories`."""

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=60)
    tint = models.CharField(max_length=20)  # design token name, e.g. "blush"
    art = models.CharField(max_length=20)  # line-drawing key, e.g. "cake"
    photo_id = models.CharField(max_length=60)  # Unsplash photo id for category tiles
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Seller(models.Model):
    class Kind(models.TextChoices):
        HOME_BAKER = "home_baker", "Home baker"
        HOME_COOK = "home_cook", "Home cook"
        ARTIST = "artist", "Artist"
        TAILOR = "tailor", "Tailor"
        CRAFTER = "crafter", "Crafter"
        JEWELLERY_MAKER = "jewellery_maker", "Jewellery maker"
        OTHER = "other", "Other"

    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="seller")
    slug = models.SlugField(unique=True, max_length=60)
    name = models.CharField(max_length=80)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.OTHER)
    # Used as the cover-photo fallback and default product category.
    main_category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)
    bio = models.TextField(blank=True)
    area = models.CharField(max_length=120, blank=True)
    cover = models.ImageField(upload_to="covers/", blank=True)
    delivery_days = models.PositiveSmallIntegerField(default=2, validators=[MaxValueValidator(30)])
    delivery_fee_paise = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)  # False = paused store
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name="products")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    price_paise = models.PositiveIntegerField(validators=[MinValueValidator(100)])  # at least ₹1
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position"]
