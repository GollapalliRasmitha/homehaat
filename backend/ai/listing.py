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
BUSY = "Google's AI is busy right now. Please try again in a minute, or fill it in yourself."
DAILY_LIMIT = "Today's free AI limit is used up. Please try again tomorrow, or fill it in yourself."
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
- Title: name only the kind of product and how it looks, e.g. "Homemade pickle in a glazed jar". Never name
  flavours, fruits, vegetables, spices, ingredients, fabrics or metals unless the seller's own name for the product
  includes them. At most 60 characters, plain words, no emoji.
- Description: 2 to 3 short sentences, plain English, no emoji, hashtags or links.
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
# Words that say what something is made of or tastes of. A photo can't show these (a yellow pickle may be mango,
# lemon or neither), so the AI may use them only if the seller already typed them (title and description alike).
# Words that are mostly colours ("orange", "cream", "mustard") are left out: colour is something a photo shows.
GUESS_WORDS = (
    # materials and metals
    "silk cotton linen wool woollen leather jute khadi polyester chiffon georgette brass copper silver gold "
    "handwoven hand-woven "
    # dietary and "how it's made" claims
    "eggless egg-free vegan organic sugar-free gluten-free preservative-free natural pure "
    # dairy, sweeteners, flours and grains
    "ghee butter cheese paneer jaggery honey millet ragi jowar bajra wheat atta maida oats rice "
    # flavours
    "chocolate vanilla butterscotch caramel coffee mocha strawberry pineapple blueberry raspberry cherry red-velvet "
    # fruits and vegetables
    "mango lemon lime apple banana grape guava papaya coconut amla gooseberry tamarind fig dates "
    "jackfruit garlic ginger onion tomato carrot beetroot brinjal gongura chilli chili "
    # spices
    "cardamom elaichi saffron kesar cinnamon clove pepper cumin jeera turmeric fenugreek methi ajwain "
    # nuts and seeds
    "almond badam cashew kaju pistachio pista walnut peanut hazelnut sesame til flax"
).split()
CLAIM_WORD = re.compile(r"\b(?:" + "|".join(re.escape(w) for w in GUESS_WORDS) + r")(?:e?s|ies)?\b", re.I)
CONNECTORS = {"and", "&", "n", "+", ",", "-", "or"}
PHRASE_START = {"with", "of", "containing", "topped", "filled"}  # "pickle with garlic and chilli"
LINK = re.compile(r"https?://|www\.", re.I)
HASHTAG = re.compile(r"#\w+")
EMOJI = re.compile("[\U0001f000-\U0001ffff☀-➿️‍]")


def _norm(text: str) -> str:
    """Lowercase, one space between words, "1 kg" == "1kg" (so we can compare with the seller's words)."""
    text = re.sub(r"\s+", " ", text.lower()).strip()
    return re.sub(r"(\d)\s+(?=[a-z])", r"\1", text)


def _all_in_hint(matches, hint: str) -> bool:
    return all(_norm(m) in hint for m in matches)


def _word(text: str) -> str:
    """One form per word, to compare with the seller's words: "Pickles," -> "pickle", "chillies" -> "chilli"."""
    w = re.sub(r"[^a-z]", "", text.lower())
    if len(w) > 4 and w.endswith("ies"):
        return w[:-2]
    if len(w) > 4 and w.endswith("oes"):
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def _seller_words(hint: str) -> set:
    return {_word(w) for w in re.split(r"[\s/-]+", hint) if w}


def _guessed(token: str, seller_words: set) -> bool:
    """A material/ingredient/flavour word the seller didn't type themselves."""
    bare = re.sub(r"[^\w-]", "", token)
    return bool(bare) and bool(CLAIM_WORD.fullmatch(bare)) and _word(bare) not in seller_words


def clean_title(title: str, hint: str) -> str:
    """
    Take guessed ingredients, flavours and materials out of a title, unless the seller typed them:
    "Mango and Lemon Pickles" -> "Pickles"; "Homemade pickle with garlic and chilli" -> "Homemade pickle".
    """
    seller = _seller_words(hint)
    tokens = []
    for token in title.split():
        parts = token.split("-")
        if len(parts) > 1 and any(_guessed(p, seller) for p in parts):
            tokens.extend(p for p in parts if p)  # "Mango-Lemon" -> "Mango", "Lemon"
        else:
            tokens.append(token)
    # "... with garlic and chilli": a guessed phrase after "with"/"of" goes as a whole, so nothing is left dangling.
    for i, token in enumerate(tokens):
        if i and token.lower() in PHRASE_START and any(_guessed(t, seller) for t in tokens[i + 1 :]):
            tokens = tokens[:i]
            break
    # Any other guessed word goes, with one "and"/"&" next to it.
    keep = [True] * len(tokens)
    for i, token in enumerate(tokens):
        if not _guessed(token, seller):
            continue
        keep[i] = False
        if i > 0 and keep[i - 1] and tokens[i - 1].lower() in CONNECTORS:
            keep[i - 1] = False
        elif i + 1 < len(tokens) and tokens[i + 1].lower() in CONNECTORS:
            keep[i + 1] = False
    words = [t for t, k in zip(tokens, keep, strict=True) if k]
    while words and words[0].lower() in CONNECTORS | PHRASE_START:
        words.pop(0)
    while words and words[-1].lower() in CONNECTORS | PHRASE_START:
        words.pop()
    text = " ".join(words).strip(" ,;:-")
    return text[:1].upper() + text[1:]


def _sentence_is_safe(sentence: str, hint: str) -> bool:
    if PRICE.search(sentence) or LINK.search(sentence):
        return False  # a price or a link is never allowed, even if the seller typed one
    if not _all_in_hint([m.group() for m in SIZE.finditer(sentence)], hint):
        return False  # a size/weight the seller didn't give us
    words = [m.group() for m in CLAIM_WORD.finditer(sentence)]
    if words:
        seller = _seller_words(hint)
        return all(_word(w) in seller for w in words)  # "silk" is fine only if the seller said "silk"
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
    sellers_name = (hint or "").strip()
    hint = _norm(sellers_name)

    # Title: remove prices, unknown sizes and guessed ingredients/flavours/materials from it (a title is short,
    # so we fix it rather than drop it).
    title = _clean_text(title)
    title = PRICE.sub("", re.sub(r"(₹|rs\.?|inr)\s*[\d,]+(?:\.\d+)?", "", title, flags=re.I))
    title = SIZE.sub(lambda m: m.group() if _norm(m.group()) in hint else "", title)
    title = clean_title(re.sub(r"\(\s*\)|\s+", " ", title).strip(" -,|:"), sellers_name)
    title = _cut(title, MAX_TITLE)
    if len(title) < 3 and len(sellers_name) >= 3:
        title = _cut(sellers_name, MAX_TITLE)  # nothing safe was left: use the seller's own name for it
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
        message = {"busy": BUSY, "daily_limit": DAILY_LIMIT}.get(exc.kind, FAILED)
        raise ListingError(str(exc), message) from exc
    return validate_listing(answer, category_slugs, hint)
