"""
The AI listing helper [KEY LOGIC]. From a product photo, Gemini suggests a title, a description and a
category. The seller edits the suggestion before saving; nothing is saved here.

Two rules from PROMPT.md: never suggest a price, and never invent ingredients, sizes or materials.
1. The prompt says so, and the JSON schema has no price field at all.
2. We don't trust the answer: validate_listing() checks the shape and removes any sentence that mentions
   a price, a size or weight, or an ingredient/material claim, unless the seller wrote it themselves.
"""

import re

from ai import gemini_client

FAILED = "Couldn't write a listing, please fill it in yourself."
BUSY = "The AI helper is busy right now. Please try again in a minute, or fill it in yourself."
BLOCKED = "AI couldn't describe this photo. Try a plain photo of your product."
MAX_TITLE = 80
MAX_DESCRIPTION = 1000

PROMPT = """You write short product listings for HomeHaat, a marketplace for things people make at home in India.
Look at the photo and suggest a title, a description and one category.

Rules:
- Describe only what you can see in the photo: what it is, its colours, shape and look.
- Never mention a price, cost or value.
- Never state ingredients, materials, fabric, weight, size, quantity, servings, shelf life or dietary claims
  (like eggless or organic). The seller adds those facts. If you aren't sure, leave it out.
- Title: at most 60 characters, plain words, no emoji. Description: 2 to 3 short sentences, plain English,
  no emoji, hashtags or links.
- category must be one of: {categories}.
{hint}"""

SCHEMA_PROPERTIES = ("title", "description", "category")


def schema(category_slugs) -> dict:
    """The exact JSON shape Gemini must answer with. There is deliberately no price field."""
    return {
        "type": "OBJECT",
        "properties": {
            "title": {"type": "STRING"},
            "description": {"type": "STRING"},
            "category": {"type": "STRING", "enum": sorted(category_slugs)},
        },
        "required": list(SCHEMA_PROPERTIES),
    }


class ListingError(Exception):
    """`message` is what the seller sees: FAILED, BUSY or BLOCKED."""

    def __init__(self, reason, message=FAILED):
        super().__init__(reason)
        self.message = message


# --- What a suggestion may not contain -------------------------------------------------------------
PRICE = re.compile(r"₹|\brs\b|\binr\b|\brupees?\b|\bprices?d?\b|\bcosts?\b|\bcheap\b|/-|\$\s*\d", re.I)
SIZE = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:kgs?|g|gms?|grams?|ml|l|litres?|liters?|cm|mm|m|inch(?:es)?|in|ft|feet|oz|lbs?"
    r"|pieces?|pcs|pack|servings?|serves|people|slices?|x\s*\d+)\b"
    r"|\bserves?\s+\d+",
    re.I,
)
# A sentence like "Made with butter" makes a claim about ingredients/materials we can't see in a photo.
CLAIM_PHRASE = re.compile(
    r"\b(?:made (?:with|from|of|using)|ingredients?|contains?|crafted (?:from|with|of)|materials?)\b", re.I
)
CLAIM_WORD = re.compile(
    r"\b(?:silk|cotton|linen|wool(?:len)?|leather|jute|khadi|polyester|chiffon|georgette|brass|copper|silver|gold"
    r"|eggless|egg-?free|vegan|organic|sugar-?free|gluten-?free|preservative-?free|natural|pure|ghee|butter"
    r"|jaggery|millets?|hand-?woven)\b",
    re.I,
)
LINK = re.compile(r"https?://|www\.", re.I)
HASHTAG = re.compile(r"#\w+")
EMOJI = re.compile("[\U0001f000-\U0001ffff☀-➿️‍]")


def _norm(text: str) -> str:
    """Lowercase, one space between words, "1 kg" == "1kg" (so we can compare with the seller's words)."""
    text = re.sub(r"\s+", " ", text.lower()).strip()
    return re.sub(r"(\d)\s+(?=[a-z])", r"\1", text)


def _all_in_hint(matches, hint: str) -> bool:
    return all(_norm(m) in hint for m in matches)


def _sentence_is_safe(sentence: str, hint: str) -> bool:
    if PRICE.search(sentence) or LINK.search(sentence):
        return False  # a price or a link is never allowed, even if the seller typed one
    if not _all_in_hint([m.group() for m in SIZE.finditer(sentence)], hint):
        return False  # a size/weight the seller didn't give us
    words = [m.group() for m in CLAIM_WORD.finditer(sentence)]
    if words:
        return _all_in_hint(words, hint)  # "pure silk" is fine only if the seller said "pure silk"
    return not CLAIM_PHRASE.search(sentence)  # "made with ..." something we can't verify


def _clean_text(text: str) -> str:
    text = EMOJI.sub("", HASHTAG.sub("", text))
    return re.sub(r"\s+", " ", text).strip()


def _cut(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:-")


def validate_listing(data, category_slugs, hint: str = "") -> dict:
    """Check and clean Gemini's answer. Returns {title, description, category} or raises ListingError."""
    if not isinstance(data, dict):
        raise ListingError("not an object")
    title, description = data.get("title"), data.get("description")
    if not isinstance(title, str) or not isinstance(description, str):
        raise ListingError("title and description must be text")
    hint = _norm(hint or "")

    # Title: remove prices and unknown sizes from it (a title is short, so we fix it rather than drop it).
    title = _clean_text(title)
    title = PRICE.sub("", re.sub(r"(₹|rs\.?|inr)\s*[\d,]+(?:\.\d+)?", "", title, flags=re.I))
    title = SIZE.sub(lambda m: m.group() if _norm(m.group()) in hint else "", title)
    title = _cut(re.sub(r"\(\s*\)|\s+", " ", title).strip(" -,|:"), MAX_TITLE)
    if len(title) < 3:
        raise ListingError("no usable title")

    # Description: keep only the sentences that pass every rule, then cut at a sentence end.
    # Split after . ! or ?, but not after "Rs." (so "Rs. 99 a jar" stays one sentence and is dropped whole).
    sentences = re.split(r"(?<=[.!?])(?<![Rr]s\.)\s+", _clean_text(description))
    kept, length = [], 0
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence or not _sentence_is_safe(sentence, hint):
            continue
        if length + len(sentence) + 1 > MAX_DESCRIPTION:
            break
        kept.append(sentence)
        length += len(sentence) + 1
    description = " ".join(kept)
    if len(description) < 15:
        description = ""  # better empty (the seller writes it) than a fragment

    category = data.get("category")
    return {
        "title": title,
        "description": description,
        "category": category if category in category_slugs else None,  # unknown -> the seller picks
    }


def write_listing(image: bytes, mime_type: str, category_slugs, hint: str = "") -> dict:
    """Ask Gemini, then validate. Any failure becomes ListingError with the message to show the seller."""
    hint_line = f'- The seller calls this product: "{hint[:120]}". Keep their words for the title.' if hint else ""
    prompt = PROMPT.format(categories=", ".join(sorted(category_slugs)), hint=hint_line)
    try:
        answer = gemini_client.generate_json(prompt, image, mime_type, schema(category_slugs))
    except gemini_client.GeminiBlocked as exc:
        raise ListingError(str(exc), BLOCKED) from exc  # e.g. a cartoon character or other protected content
    except gemini_client.GeminiError as exc:
        raise ListingError(str(exc), BUSY if exc.busy else FAILED) from exc
    return validate_listing(answer, category_slugs, hint)
