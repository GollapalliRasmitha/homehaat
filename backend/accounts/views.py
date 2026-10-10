from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import generics, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from accounts.serializers import AddressSerializer, SignInSerializer, SignUpSerializer, UserSerializer


class AuthThrottle(SimpleRateThrottle):
    """At most 10 sign-in/sign-up attempts per minute per IP address (rate set in settings)."""

    scope = "auth"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class CsrfRequired(BasePermission):
    """
    DRF checks CSRF only for signed-in users. Sign-up and sign-in happen before
    that, so we check it here too (stops a "login CSRF" trick from another site).
    """

    def has_permission(self, request, view):
        SessionAuthentication().enforce_csrf(request)  # raises 403 if the token is missing or wrong
        return True


@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def csrf(request):
    """Sets the csrftoken cookie. The frontend sends it back as X-CSRFToken on every change."""
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([CsrfRequired])
@throttle_classes([AuthThrottle])
def signup(request):
    serializer = SignUpSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    login(request, user)
    return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([CsrfRequired])
@throttle_classes([AuthThrottle])
def signin(request):
    serializer = SignInSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = authenticate(
        request, email=serializer.validated_data["email"].lower(), password=serializer.validated_data["password"]
    )
    if user is None:
        return Response({"detail": "Email or password is wrong."}, status=status.HTTP_400_BAD_REQUEST)
    login(request, user)
    return Response(UserSerializer(user).data)


@api_view(["POST"])
@permission_classes([AllowAny])
def signout(request):
    logout(request)
    return Response({"ok": True})


@api_view(["GET", "PATCH"])
@permission_classes([AllowAny])
def me(request):
    if not request.user.is_authenticated:
        return Response({"user": None})
    if request.method == "PATCH":
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()  # "role" is read-only in the serializer, so it is never saved
        return Response({"user": serializer.data})
    return Response({"user": UserSerializer(request.user).data})


class AddressList(generics.ListCreateAPIView):
    serializer_class = AddressSerializer
    pagination_class = None

    def get_queryset(self):
        return self.request.user.addresses.all()  # only your own addresses

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
