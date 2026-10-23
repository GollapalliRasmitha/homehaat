"""
The visitor's real IP address, for per-visitor limits (the sign-in rate limit).

The browser talks to Next.js, and Next.js calls Django, so every request reaches Django from the Next.js server's
address. frontend/proxy.ts therefore passes the visitor's IP in X-HomeHaat-Client-IP, together with
X-HomeHaat-Proxy-Secret = PROXY_SECRET (set the same value for both apps). Django trusts the IP header ONLY when the
secret matches: anyone can send headers straight to Django and fake an IP to dodge the limit, but they don't know the
secret. No secret configured (local) -> nothing is trusted and the connecting address is used, as before.

Requests that skip the website (scanners calling the Render address directly) don't carry the header. On Render the
connecting address is only Render's relay, the same for everyone. There X-Forwarded-For ends
"..., visitor, Cloudflare, Render's relay" (measured 23 Oct 2026), and Cloudflare writes the visitor's address after
anything the visitor sent, so TRUSTED_PROXY_HOPS=3 counts back to it and can't be fooled. 0 (local) = don't use it.
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


def _forwarded_ip(request) -> str | None:
    """The visitor in X-Forwarded-For, TRUSTED_PROXY_HOPS from the end; None if the chain isn't what we expect."""
    hops = getattr(settings, "TRUSTED_PROXY_HOPS", 0)
    chain = [part.strip() for part in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",") if part.strip()]
    if hops <= 0 or len(chain) < hops:
        return None
    try:
        return str(ipaddress.ip_address(chain[-hops]))
    except ValueError:
        return None


def client_ip(request) -> str:
    connecting = request.META.get("REMOTE_ADDR", "")
    if not _from_our_proxy(request):
        return _forwarded_ip(request) or connecting
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
