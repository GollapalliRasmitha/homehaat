from django.contrib import admin, messages

from orders.models import Order, OrderItem, Refund, SellerOrder


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "buyer", "grand_total", "payment_status", "created_at", "paid_at"]
    list_filter = ["payment_status"]


@admin.register(SellerOrder)
class SellerOrderAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "seller", "status", "cancelled_by", "refund_needed"]
    list_filter = ["status", "cancelled_by"]


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    """Every refund, with failed ones easy to find (filter: Failed) and a button to retry them."""

    list_display = [
        "id",
        "seller_order",
        "amount",
        "status",
        "razorpay_refund_id",
        "attempts",
        "last_error",
        "created_at",
    ]
    list_filter = ["status"]
    readonly_fields = ["seller_order", "amount", "razorpay_refund_id", "attempts", "last_error", "processed_at"]
    actions = ["retry"]

    @admin.action(description="Retry the selected refunds")
    def retry(self, request, queryset):
        from payments.refunds import send_refund

        for refund in queryset.exclude(status=Refund.Status.PROCESSED):
            send_refund(refund.pk)
        self.message_user(request, "Retried. Check the status column.", messages.INFO)


admin.site.register(OrderItem)
