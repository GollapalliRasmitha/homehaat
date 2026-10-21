"""
The visitor's real IP address, for per-visitor limits (the sign-in rate limit).

The browser talks to Next.js, and Next.js calls Django, so every request reaches Django from the Next.js server's
address. frontend/proxy.ts therefore passes the visitor's IP in X-HomeHaat-Client-IP, together with
X-HomeHaat-Proxy-Secret = PROXY_SECRET (set the same value for both apps). Django trusts the IP header ONLY when the
secret matches: anyone can send headers straight to Django and fake an IP to dodge the limit, but they don't know the
secret. No secret configured (local) -> nothing is trusted and the connecting address is used, as before.
The visitor's country (X-HomeHaat-Client-Country, from Vercel) is passed and trusted the same way; GuardRail uses it.
"""

import hmac
import ipaddress

from django.conf import settings


def _from_our_proxy(request) -> bool:
    """True only if the request carries the right PROXY_SECRET (constant-time compare)."""
    secret = getattr(settings, "PROXY_SECRET", "")
    sent = request.META.get("HTTP_X_HOMEHAAT_PROXY_SECRET", "")
    return bool(secret) and bool(sent) and hmac.compare_digest(sent, secret)


def client_ip(request) -> str:
    connecting = request.META.get("REMOTE_ADDR", "")
    if not _from_our_proxy(request):
        return connecting
    claimed = request.META.get("HTTP_X_HOMEHAAT_CLIENT_IP", "").strip()
    try:
        return str(ipaddress.ip_address(claimed))
    except ValueError:
        return connecting


def client_country(request) -> str | None:
    """The visitor's country (2 letters, from Vercel), passed on by our proxy like the IP. None if unknown."""
    if not _from_our_proxy(request):
        return None
    country = request.META.get("HTTP_X_HOMEHAAT_CLIENT_COUNTRY", "").strip().upper()
    return country if len(country) == 2 and country.isalpha() else None
