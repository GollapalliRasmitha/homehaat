from django.db.models import Avg
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from catalog.models import Seller
from catalog.views import IsSeller
from reviews.services import ReviewError, write_review


@api_view(["GET"])
@permission_classes([IsSeller])
def my_reviews(request):
    """The seller's reviews, read-only, with the average (None when there are none: no made-up rating)."""
    reviews = request.user.seller.reviews.select_related("buyer")
    average = reviews.aggregate(avg=Avg("rating"))["avg"]
    return Response(
        {
            "average": round(average, 1) if average is not None else None,
            "count": reviews.count(),
            "reviews": [
                {
                    "id": r.id,
                    "rating": r.rating,
                    "comment": r.comment,
                    "buyer_name": (r.buyer.name.split(" ")[0] if r.buyer.name else "A buyer"),  # first name only
                    "created_at": r.created_at,
                }
                for r in reviews
            ],
        }
    )


@api_view(["POST"])
def write(request):
    """POST {seller: slug, rating, comment}. The buyer is always the signed-in user."""
    seller = get_object_or_404(Seller, slug=str(request.data.get("seller", "")))
    try:
        review, created = write_review(request.user, seller, request.data.get("rating"), request.data.get("comment"))
    except ReviewError as exc:
        return Response({"detail": exc.message}, status=400)
    return Response(review_data(review), status=201 if created else 200)


def review_data(review):
    return {"id": review.id, "rating": review.rating, "comment": review.comment, "created_at": review.created_at}
