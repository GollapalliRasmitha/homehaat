from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes, throttle_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from catalog.browse import public_stores
from catalog.images import ImageError, clean_image
from catalog.views import IsSeller
from custom_requests.models import CustomRequest, CustomRequestImage
from custom_requests.serializers import CustomRequestSerializer, NewRequestSerializer, QuoteSerializer
from custom_requests.services import NotYourRequestError, RequestError, add_quote_to_bag, apply_action

MAX_PHOTOS = 3


class RequestThrottle(UserRateThrottle):
    scope = "custom_requests"  # 10 new requests per hour per buyer (settings)


def _with_details(qs):
    return qs.select_related("seller", "buyer", "product").prefetch_related("images")


def _answer(req):
    return Response(CustomRequestSerializer(_with_details(CustomRequest.objects).get(pk=req.pk)).data)


def _run(req, user, action, **extra):
    """Apply an action and turn rule errors into clear HTTP answers."""
    try:
        return _answer(apply_action(req, user, action, **extra))
    except NotYourRequestError:
        return Response({"detail": "Request not found."}, status=status.HTTP_404_NOT_FOUND)
    except RequestError as exc:
        return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)


# --- buyer ---


@api_view(["GET", "POST"])
@throttle_classes([])
def my_requests(request):
    if request.method == "GET":
        mine = _with_details(CustomRequest.objects.filter(buyer=request.user))  # only your own
        return Response(CustomRequestSerializer(mine, many=True).data)

    # POST: the throttle applies to creating requests only, not to reading them.
    throttle = RequestThrottle()
    if not throttle.allow_request(request, None):
        return Response({"detail": "Too many requests. Please wait a while and try again."}, status=429)

    data = NewRequestSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    store = public_stores().filter(slug=data.validated_data["seller"]).first()  # paused shops aren't found
    if store is None:
        return Response({"seller": ["This maker isn't taking requests right now."]}, status=400)
    if store.owner_id == request.user.id:
        return Response({"detail": "You can't send a request to your own shop."}, status=400)
    req = CustomRequest.objects.create(
        buyer=request.user,
        seller=store,
        description=data.validated_data["description"],
        needed_by=data.validated_data.get("needed_by"),
        budget_paise=data.validated_data.get("budget_paise"),
    )
    return Response(CustomRequestSerializer(_with_details(CustomRequest.objects).get(pk=req.pk)).data, status=201)


def _mine(request, pk):
    return get_object_or_404(CustomRequest, pk=pk, buyer=request.user)  # someone else's -> 404


@api_view(["GET"])
def my_request(request, pk):
    return _answer(_mine(request, pk))


@api_view(["POST"])
@parser_classes([MultiPartParser])
def request_images(request, pk):
    """Add one reference photo (field "image"), up to 3, while the request is still open."""
    req = _mine(request, pk)
    if req.status != CustomRequest.Status.OPEN:
        return Response({"detail": "Photos can only be added before the maker replies."}, status=400)
    count = req.images.count()
    if count >= MAX_PHOTOS:
        return Response({"detail": f"A request can have up to {MAX_PHOTOS} photos."}, status=400)
    try:
        cleaned = clean_image(request.FILES.get("image"))  # same checks as product photos: no EXIF/GPS kept
    except ImageError as exc:
        return Response({"detail": exc.message}, status=400)
    CustomRequestImage.objects.create(request=req, image=cleaned, position=count)
    return Response({"ok": True}, status=201)


@api_view(["POST"])
def accept(request, pk):
    # Only the request id is used: the price comes from the saved quote, never from the body.
    return _run(_mine(request, pk), request.user, "accept")


@api_view(["POST"])
def decline(request, pk):
    return _run(_mine(request, pk), request.user, "decline")


@api_view(["POST"])
def add_to_bag(request, pk):
    req = _mine(request, pk)
    try:
        add_quote_to_bag(req, request.user)
    except RequestError as exc:
        return Response({"detail": exc.message}, status=400)
    return _answer(req)


# --- seller ---


@api_view(["GET"])
@permission_classes([IsSeller])
def shop_requests(request):
    mine = _with_details(CustomRequest.objects.filter(seller=request.user.seller))  # only your shop's
    return Response(CustomRequestSerializer(mine, many=True).data)


def _for_my_shop(request, pk):
    return get_object_or_404(CustomRequest, pk=pk, seller=request.user.seller)  # another shop's -> 404


@api_view(["POST"])
@permission_classes([IsSeller])
def send_quote(request, pk):
    data = QuoteSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    return _run(
        _for_my_shop(request, pk),
        request.user,
        "quote",
        quote_paise=data.validated_data["quote_paise"],
        note=data.validated_data["note"],
    )


@api_view(["POST"])
@permission_classes([IsSeller])
def seller_decline(request, pk):
    return _run(_for_my_shop(request, pk), request.user, "decline")
