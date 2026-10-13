from django.contrib.auth import password_validation
from rest_framework import serializers

from accounts.address_rules import MESSAGES, address_problems, normalize_phone
from accounts.models import Address, User


class UserSerializer(serializers.ModelSerializer):
    store_slug = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "name", "phone", "role", "store_slug", "shop_name", "open_orders"]
        # role is read-only: users can never change their own role through the API.
        read_only_fields = ["id", "email", "role", "store_slug", "shop_name", "open_orders"]

    shop_name = serializers.SerializerMethodField()
    open_orders = serializers.SerializerMethodField()  # the badge on "Shop orders" in the account menu

    def get_store_slug(self, user):
        seller = getattr(user, "seller", None)
        return seller.slug if seller else None

    def get_shop_name(self, user):
        seller = getattr(user, "seller", None)
        return seller.name if seller else None

    def get_open_orders(self, user):
        seller = getattr(user, "seller", None)
        if not seller:
            return 0
        from orders.views import OPEN, paid_parts  # here: orders imports accounts

        return paid_parts(seller).filter(status__in=OPEN).count()


class SignUpSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8, max_length=128)
    name = serializers.CharField(max_length=120, required=False, allow_blank=True)

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists. Try signing in.")
        return value

    def validate(self, attrs):
        password_validation.validate_password(attrs["password"], User(email=attrs["email"]))
        return attrs

    def create(self, data):
        # Only these three fields are used: a "role" in the request is simply ignored.
        return User.objects.create_user(data["email"], data["password"], name=data.get("name", ""))


class SignInSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class AddressSerializer(serializers.ModelSerializer):
    # The rules live in accounts/address_rules.py. Each broken rule gets its own message next to its field.
    problems = serializers.SerializerMethodField()  # for addresses saved before the rules: what to update

    class Meta:
        model = Address
        fields = ["id", "label", "name", "phone", "line1", "line2", "city", "pincode", "problems"]
        extra_kwargs = {"phone": {"max_length": 20}}  # "+91 98765 43210" is accepted, then saved as 10 digits

    def get_problems(self, address):
        return address_problems(address.__dict__)

    def validate(self, attrs):
        if "phone" in attrs:
            attrs["phone"] = normalize_phone(attrs["phone"])
        for key in ("name", "line1", "line2", "city", "pincode"):
            if key in attrs:
                attrs[key] = attrs[key].strip()
        # When editing, check the whole address as it will be saved (old values + the changes).
        current = {f: getattr(self.instance, f) for f in MESSAGES} if self.instance else {}
        problems = address_problems(current | attrs)
        if problems:
            raise serializers.ValidationError({field: [message] for field, message in problems.items()})
        return attrs
