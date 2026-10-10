from django.contrib import admin

from orders.models import Order, OrderItem, SellerOrder


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "buyer", "grand_total", "payment_status", "created_at", "paid_at"]
    list_filter = ["payment_status"]


admin.site.register(SellerOrder)
admin.site.register(OrderItem)
