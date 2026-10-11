from django.db.models import Avg
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from catalog.views import IsSeller


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
