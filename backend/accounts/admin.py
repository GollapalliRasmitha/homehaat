from django.contrib import admin

from accounts.models import Address, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["email", "name", "role", "is_staff", "date_joined"]
    list_filter = ["role"]
    search_fields = ["email", "name"]
    exclude = ["password"]


admin.site.register(Address)
