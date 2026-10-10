from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class CartItem(models.Model):
    """The server-side bag. One row per product per user."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart_items")
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="cart_items")
    qty = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(50)])
    note = models.CharField(max_length=300, blank=True)
    # Set when the item comes from an accepted custom request (Stage 5).
    custom_request = models.ForeignKey(
        "custom_requests.CustomRequest", null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [models.UniqueConstraint(fields=["user", "product"], name="unique_cart_product")]
