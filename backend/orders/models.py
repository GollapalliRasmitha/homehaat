from django.conf import settings
from django.db import models


class Order(models.Model):
    """One per checkout: the single payment the buyer makes. All money is integer paise."""

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    # SET_NULL so "delete my account" can anonymise orders instead of deleting a seller's history.
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="orders")
    items_total = models.PositiveIntegerField()
    delivery_total = models.PositiveIntegerField()
    grand_total = models.PositiveIntegerField()
    payment_status = models.CharField(
        max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.PENDING, db_index=True
    )
    # null (not "") so many unpaid orders can exist while the value stays unique once set.
    razorpay_order_id = models.CharField(max_length=40, unique=True, null=True, blank=True)
    razorpay_payment_id = models.CharField(max_length=40, unique=True, null=True, blank=True)
    ship_to = models.JSONField()  # frozen copy of the address at checkout time
    # True while this order has taken stock off the shelf (from checkout until it's
    # paid, or until the hold is released). Releasing gives stock back only if True.
    stock_held = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        # expire_unpaid_orders looks for "pending and older than 15 minutes"
        indexes = [models.Index(fields=["payment_status", "created_at"], name="order_status_created")]

    def __str__(self):
        return f"Order #{self.pk}"


class SellerOrder(models.Model):
    """Each seller's share of an Order. The seller prepares and delivers only this part."""

    class Status(models.TextChoices):
        NEW = "new", "New"
        PREPARING = "preparing", "Preparing"
        OUT_FOR_DELIVERY = "out_for_delivery", "Out for delivery"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="seller_orders")
    seller = models.ForeignKey("catalog.Seller", on_delete=models.PROTECT, related_name="seller_orders")
    subtotal = models.PositiveIntegerField()  # items only, in paise
    delivery_fee = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW, db_index=True)
    preparing_at = models.DateTimeField(null=True, blank=True)
    out_for_delivery_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    refund_needed = models.BooleanField(default=False)  # cancelled after payment: see the Refund row
    # The buyer asked to cancel while it was being prepared; the seller accepts or declines.
    cancel_requested_at = models.DateTimeField(null=True, blank=True)
    cancel_declined_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.CharField(max_length=10, blank=True)  # "buyer", "seller" or "system" (late payment)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["order", "seller"], name="unique_order_seller")]


class OrderItem(models.Model):
    seller_order = models.ForeignKey(SellerOrder, on_delete=models.CASCADE, related_name="items")
    # Nullable: the seller may delete the product later, but the order must keep its record.
    product = models.ForeignKey("catalog.Product", null=True, on_delete=models.SET_NULL, related_name="+")
    # Snapshots: what the buyer actually paid for, even if the seller edits the product afterwards.
    name = models.CharField(max_length=120)
    unit_price = models.PositiveIntegerField()
    qty = models.PositiveSmallIntegerField()
    note = models.CharField(max_length=300, blank=True)

    @property
    def line_total(self) -> int:
        return self.unit_price * self.qty


class Refund(models.Model):
    """
    The money back for ONE cancelled seller order (its items + that maker's delivery fee), through Razorpay.
    One-to-one with SellerOrder: the database itself makes a second refund for the same part impossible.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"  # started (or about to be sent); Razorpay usually takes 5-7 days
        PROCESSED = "processed", "Processed"  # the money is on its way back
        FAILED = "failed", "Failed"  # Razorpay refused or couldn't be reached: retry_refunds tries again

    seller_order = models.OneToOneField(SellerOrder, on_delete=models.PROTECT, related_name="refund")
    amount = models.PositiveIntegerField()  # paise, computed on the server: subtotal + delivery_fee
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    razorpay_refund_id = models.CharField(max_length=40, unique=True, null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Refund of {self.amount} paise for seller order {self.seller_order_id} ({self.status})"
