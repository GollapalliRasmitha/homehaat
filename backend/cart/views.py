from dataclasses import dataclass

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from cart.models import CartItem
from catalog.browse import public_products, shop_products
from catalog.models import Product
from catalog.serializers import ProductSerializer, SellerSummarySerializer

MAX_QTY = 50
MAX_LINES = 50  # most different products one bag may hold


@dataclass
class Line:
    """One bag line: a saved CartItem (id set) or a guest's line from the browser (id None)."""

    product: Product
    qty: int
    note: str = ""
    id: int | None = None


def stock_message(stock: int) -> str:
    return "This is sold out." if stock <= 0 else f"Only {stock} available."


def problem_with(line: Line) -> str | None:
    """Why this line can't be bought right now, or None if it's fine."""
    product = line.product
    if not product.is_active or not product.seller.is_active:
        return "unavailable"
    if product.stock == 0:
        return "sold_out"
    if line.qty > product.stock:
        return "not_enough"
    return None


def summarise(lines: list[Line]) -> dict:
    """The bag grouped by seller, with every total computed here from database prices (integer paise)."""
    groups: dict[int, dict] = {}
    for line in lines:
        seller = line.product.seller
        group = groups.setdefault(
            seller.id,
            {
                "seller": SellerSummarySerializer(seller).data,
                "items": [],
                "items_total": 0,
                "delivery_fee": seller.delivery_fee_paise,
            },
        )
        line_total = line.product.price_paise * line.qty
        group["items"].append(
            {
                "id": line.id,
                "qty": line.qty,
                "note": line.note,
                "line_total": line_total,
                "problem": problem_with(line),
                "product": ProductSerializer(line.product).data,
            }
        )
        group["items_total"] += line_total

    for group in groups.values():
        group["subtotal"] = group["items_total"] + group["delivery_fee"]

    items_total = sum(g["items_total"] for g in groups.values())
    delivery_total = sum(g["delivery_fee"] for g in groups.values())  # one fee per seller
    return {
        "groups": list(groups.values()),
        "count": sum(line.qty for line in lines),
        "items_total": items_total,
        "delivery_total": delivery_total,
        "grand_total": items_total + delivery_total,
        "has_problems": any(item["problem"] for g in groups.values() for item in g["items"]),
    }


def cart_summary(user) -> dict:
    items = (
        CartItem.objects.filter(user=user)
        .select_related("product__seller", "product__category")
        .prefetch_related("product__images")
        .order_by("created_at")
    )
    return summarise([Line(item.product, item.qty, item.note, item.id) for item in items])


class AddItemSerializer(serializers.Serializer):
    # Only these fields are read. A price in the request is ignored.
    product_id = serializers.IntegerField()
    qty = serializers.IntegerField(min_value=1, max_value=MAX_QTY, default=1)
    note = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")


class GuestBagSerializer(serializers.Serializer):
    items = AddItemSerializer(many=True, max_length=MAX_LINES)


class UpdateItemSerializer(serializers.Serializer):
    qty = serializers.IntegerField(min_value=1, max_value=MAX_QTY, required=False)
    note = serializers.CharField(max_length=300, required=False, allow_blank=True)


@api_view(["GET"])
def cart(request):
    return Response(cart_summary(request.user))


@api_view(["POST"])
def add_item(request):
    data = AddItemSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    product = get_object_or_404(shop_products(), pk=data.validated_data["product_id"])
    if not product.seller.is_active:
        return Response(
            {"detail": "This maker isn't taking orders right now. Please check back soon."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if product.seller.owner_id == request.user.id:
        return Response({"detail": "You can't buy from your own shop."}, status=status.HTTP_400_BAD_REQUEST)

    item = CartItem.objects.filter(user=request.user, product=product).first()
    new_qty = (item.qty if item else 0) + data.validated_data["qty"]
    if new_qty > min(product.stock, MAX_QTY):
        return Response({"detail": stock_message(product.stock)}, status=status.HTTP_400_BAD_REQUEST)

    if item:
        item.qty = new_qty
        item.note = data.validated_data["note"] or item.note
        item.save(update_fields=["qty", "note"])
    else:
        CartItem.objects.create(user=request.user, product=product, qty=new_qty, note=data.validated_data["note"])
    return Response(cart_summary(request.user), status=status.HTTP_201_CREATED)


@api_view(["PATCH", "DELETE"])
def change_item(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, user=request.user)  # only your own cart
    if request.method == "DELETE":
        item.delete()
        return Response(cart_summary(request.user))

    data = UpdateItemSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    if "qty" in data.validated_data:
        if data.validated_data["qty"] > item.product.stock:
            return Response({"detail": stock_message(item.product.stock)}, status=status.HTTP_400_BAD_REQUEST)
        item.qty = data.validated_data["qty"]
    if "note" in data.validated_data:
        item.note = data.validated_data["note"]
    item.save(update_fields=["qty", "note"])
    return Response(cart_summary(request.user))


def _guest_lines(request) -> list[Line]:
    """The guest's bag as sent by the browser, matched to real products. Unknown ids are dropped."""
    data = GuestBagSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    wanted = data.validated_data["items"]
    products = public_products().in_bulk([w["product_id"] for w in wanted])
    return [Line(products[w["product_id"]], w["qty"], w["note"]) for w in wanted if w["product_id"] in products]


@api_view(["POST"])
@permission_classes([AllowAny])
def preview(request):
    """Prices a guest's bag (kept in their browser) without saving anything."""
    return Response(summarise(_guest_lines(request)))


@api_view(["POST"])
@transaction.atomic
def merge(request):
    """On sign-in: add the guest bag to the account's bag, capped at stock and 50."""
    skipped = []
    for line in _guest_lines(request):
        if line.product.seller.owner_id == request.user.id:
            skipped.append(line.product.name)  # can't buy from your own shop
            continue
        existing = CartItem.objects.filter(user=request.user, product=line.product).first()
        current = existing.qty if existing else 0
        target = min(current + line.qty, line.product.stock, MAX_QTY)
        if target < 1:  # sold out since the guest added it
            skipped.append(line.product.name)
        elif existing is None:
            CartItem.objects.create(user=request.user, product=line.product, qty=target, note=line.note)
        elif target > current:
            existing.qty = target
            existing.note = existing.note or line.note
            existing.save(update_fields=["qty", "note"])
    return Response({**cart_summary(request.user), "skipped": skipped})
