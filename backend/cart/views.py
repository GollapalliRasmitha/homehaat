from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from cart.models import CartItem
from catalog.serializers import ProductSerializer
from catalog.views import public_products

MAX_QTY = 50


def cart_summary(user) -> dict:
    """The bag with totals computed here, from database prices (integer paise)."""
    items = (
        CartItem.objects.filter(user=user)
        .select_related("product__seller", "product__category")
        .prefetch_related("product__images")
    )
    items_total = sum(item.product.price_paise * item.qty for item in items)
    sellers = {item.product.seller_id: item.product.seller for item in items}
    delivery_total = sum(seller.delivery_fee_paise for seller in sellers.values())  # one fee per maker
    return {
        "items": [
            {
                "id": item.id,
                "qty": item.qty,
                "note": item.note,
                "line_total": item.product.price_paise * item.qty,
                "product": ProductSerializer(item.product).data,
            }
            for item in items
        ],
        "count": sum(item.qty for item in items),
        "items_total": items_total,
        "delivery_total": delivery_total,
        "grand_total": items_total + delivery_total,
    }


class AddItemSerializer(serializers.Serializer):
    # Only these fields are read. A price in the request is ignored.
    product_id = serializers.IntegerField()
    qty = serializers.IntegerField(min_value=1, max_value=MAX_QTY, default=1)
    note = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")


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
    product = get_object_or_404(public_products(), pk=data.validated_data["product_id"])

    if product.seller.owner_id == request.user.id:
        return Response({"detail": "You can't buy from your own shop."}, status=status.HTTP_400_BAD_REQUEST)

    # Stage 1 limit: one maker per bag. Stage 2 removes this.
    other_seller = CartItem.objects.filter(user=request.user).exclude(product__seller=product.seller).exists()
    if other_seller:
        return Response(
            {"detail": "Your bag has items from another maker. For now, check out one maker at a time."},
            status=status.HTTP_409_CONFLICT,
        )

    item = CartItem.objects.filter(user=request.user, product=product).first()
    new_qty = (item.qty if item else 0) + data.validated_data["qty"]
    if new_qty > min(product.stock, MAX_QTY):
        return Response({"detail": f"Only {product.stock} available."}, status=status.HTTP_400_BAD_REQUEST)

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
            return Response({"detail": f"Only {item.product.stock} available."}, status=status.HTTP_400_BAD_REQUEST)
        item.qty = data.validated_data["qty"]
    if "note" in data.validated_data:
        item.note = data.validated_data["note"]
    item.save(update_fields=["qty", "note"])
    return Response(cart_summary(request.user))
