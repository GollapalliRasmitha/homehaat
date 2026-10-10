"""
The only file that talks to Razorpay's servers. Test mode only (settings.py
refuses any key that doesn't start with rzp_test_). Tests replace these
functions with fakes, so tests never call Razorpay.
"""

import requests
from django.conf import settings

API = "https://api.razorpay.com/v1"
TIMEOUT_SECONDS = 15


class RazorpayError(Exception):
    pass


def _call(method: str, path: str, **kwargs) -> dict:
    if not (settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET):
        raise RazorpayError("Razorpay test keys are not set in .env.")
    try:
        response = requests.request(
            method,
            f"{API}{path}",
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
            timeout=TIMEOUT_SECONDS,
            **kwargs,
        )
    except requests.RequestException as exc:
        raise RazorpayError(f"Couldn't reach Razorpay: {exc}") from exc
    if response.status_code >= 400:
        raise RazorpayError(f"Razorpay said {response.status_code}: {response.text[:200]}")
    return response.json()


def create_order(*, amount_paise: int, receipt: str) -> dict:
    """Razorpay's Orders API: fixes the amount on their side before the buyer pays."""
    return _call("POST", "/orders", json={"amount": amount_paise, "currency": "INR", "receipt": receipt})


def fetch_payment(payment_id: str) -> dict:
    return _call("GET", f"/payments/{payment_id}")


def capture_payment(payment_id: str, amount_paise: int) -> dict:
    return _call("POST", f"/payments/{payment_id}/capture", json={"amount": amount_paise, "currency": "INR"})
