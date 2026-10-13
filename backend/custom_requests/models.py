from django.conf import settings
from django.db import models


class CustomRequest(models.Model):
    """'Photo cake for Saturday' -> the seller quotes -> the buyer accepts (Stage 5)."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        QUOTED = "quoted", "Quoted"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"

    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="custom_requests")
    seller = models.ForeignKey("catalog.Seller", on_delete=models.CASCADE, related_name="custom_requests")
    description = models.TextField()
    needed_by = models.DateField(null=True, blank=True)
    budget_paise = models.PositiveIntegerField(null=True, blank=True)
    quote_paise = models.PositiveIntegerField(null=True, blank=True)
    seller_note = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN, db_index=True)
    # Made when the buyer accepts the quote: the one-off product (price = quote) that goes into their bag.
    product = models.OneToOneField(
        "catalog.Product", null=True, blank=True, on_delete=models.SET_NULL, related_name="custom_request"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)  # last quote / accept / decline

    class Meta:
        ordering = ["-created_at"]


class CustomRequestImage(models.Model):
    """Up to 3 reference photos per request."""

    request = models.ForeignKey(CustomRequest, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="requests/")
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position"]
