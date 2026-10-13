"""
Rules for a delivery address in India. One place, used when an address is saved or edited, to flag old
addresses that were saved before these rules, and by checkout (which refuses an address that breaks them).
The form in the browser checks the same rules (frontend/lib/address-rules.ts), but the server decides.
"""

import re

PINCODE = re.compile(r"^[1-9]\d{5}$")  # 6 digits; Indian pincodes never start with 0
MOBILE = re.compile(r"^[6-9]\d{9}$")  # 10 digits; Indian mobile numbers start with 6, 7, 8 or 9

MESSAGES = {
    "name": "Please enter the name of the person receiving the order.",
    "phone": "Enter a 10-digit mobile number starting with 6, 7, 8 or 9.",
    "line1": "Please write your house number and street in words (at least 3 letters).",
    "line2": "Leave this empty, or write it in words.",
    "city": "Please enter your city name (at least 3 letters).",
    "pincode": "Enter a 6-digit pincode (it doesn't start with 0).",
}


def letters(text: str) -> int:
    """How many letters, in any script ("Bengaluru" and "बेंगलुरु" both count). Symbols and digits don't."""
    return sum(ch.isalpha() for ch in text or "")


def normalize_phone(phone: str) -> str:
    """Turns "+91 98765 43210" or "098765-43210" into "9876543210". Anything else stays as typed (then refused)."""
    digits = re.sub(r"[\s\-()]", "", phone or "")
    for prefix in ("+91", "91", "0"):
        if digits.startswith(prefix) and len(digits) == len(prefix) + 10:
            return digits[len(prefix) :]
    return digits if digits.isdigit() else (phone or "").strip()


def address_problems(data: dict) -> dict[str, str]:
    """{field: message} for every field that breaks a rule; {} means the address is fine."""
    get = lambda key: str(data.get(key) or "").strip()  # noqa: E731
    problems = {}
    if letters(get("name")) < 2:
        problems["name"] = MESSAGES["name"]
    if not MOBILE.match(normalize_phone(get("phone"))) or len(set(normalize_phone(get("phone")))) == 1:
        problems["phone"] = MESSAGES["phone"]  # 1111111111-style numbers are refused too
    if letters(get("line1")) < 3:
        problems["line1"] = MESSAGES["line1"]
    if get("line2") and not any(ch.isalnum() for ch in get("line2")):
        problems["line2"] = MESSAGES["line2"]
    if letters(get("city")) < 3:
        problems["city"] = MESSAGES["city"]
    if not PINCODE.match(get("pincode")):
        problems["pincode"] = MESSAGES["pincode"]
    return problems
