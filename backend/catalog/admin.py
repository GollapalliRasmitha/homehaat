from django.contrib import admin

from catalog.models import Category, Product, ProductImage, Seller

admin.site.register(Category)
admin.site.register(Seller)
admin.site.register(ProductImage)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "seller", "price_paise", "stock", "is_active"]
