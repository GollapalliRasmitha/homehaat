"""
The visitor's real IP address, for per-visitor limits (the sign-in rate limit).

The browser talks to Next.js, and Next.js calls Django, so every request reaches Django from the Next.js server's
address. frontend/proxy.ts therefore passes the visitor's IP in X-HomeHaat-Client-IP, together with
X-HomeHaat-Proxy-Secret = PROXY_SECRET (set the same value for both apps). Django trusts the IP header ONLY when the
secret matches: anyone can send headers straight to Django and fake an IP to dodge the limit, but they don't know the
secret. No secret configured (local) -> nothing is trusted and the connecting address is used, as before.
"""

import hmac
import ipaddress

from django.conf import settings


def client_ip(request) -> str:
    connecting = request.META.get("REMOTE_ADDR", "")
    secret = getattr(settings, "PROXY_SECRET", "")
    sent = request.META.get("HTTP_X_HOMEHAAT_PROXY_SECRET", "")
    if not secret or not sent or not hmac.compare_digest(sent, secret):
        return connecting
    claimed = request.META.get("HTTP_X_HOMEHAAT_CLIENT_IP", "").strip()
    try:
        return str(ipaddress.ip_address(claimed))
    except ValueError:
        return connecting
