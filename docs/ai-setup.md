# Turning on the AI listing helper (free)

HomeHaat works fully without AI. With it on, sellers see **Write listing with AI** on the Add/Edit product
form: it looks at their first photo and suggests a name, a description and a category. It never suggests a
price, and the seller checks and edits everything before saving.

It uses Google's **Gemini API free tier**. No card is needed.

## 1. Get a key (about 3 minutes)

1. Open <https://aistudio.google.com/apikey> and sign in with a Google account.
2. Click **Create API key**. If it asks for a project, create a new one called `homehaat`.
   Use HomeHaat's **own** key, never Oppora's, so one project can't use up the other's free daily limit.
3. Copy the key. Treat it like a password: don't paste it into chat, code or documents.

## 2. Put it in `.env`

Open `homehaat\.env` (not `.env.example`) in Notepad and set:

```
AI_ENABLED=true
GEMINI_API_KEY=paste-your-key-here
```

Leave `GEMINI_MODEL` empty to use the default (`gemini-flash-lite-latest`, with `gemini-flash-latest` as the
backup). Save, then restart the Django window
(close it and run `.\start-homehaat.ps1` again).

## 3. Check it

Sign in as a seller → **My shop → Products → Add product** → add a photo → **Write listing with AI**.

- A suggestion appears with **Use this** / **Dismiss**.
- If anything goes wrong (no internet, the free daily limit used up, a bad answer), the seller sees
  *"Couldn't write a listing, please fill it in yourself."* and the form keeps working.

## Good to know

- **Keys:** both the older `AIza…` keys and the newer `AQ.…` keys work (they're sent in a header).
- **Messages sellers can see:**
  - *"Google's AI is busy right now. Please try again in a minute…"*: Google is overloaded (503) or slow. HomeHaat
    already waited 2 seconds and tried once more before showing this.
  - *"Today's free AI limit is used up. Please try again tomorrow…"*: the key's free daily quota is used up (429).
  - *"AI couldn't describe this photo. Try a plain photo of your product."*: Google refused the photo (for example a
    cartoon character).
  - otherwise *"Couldn't write a listing, please fill it in yourself."*
- **Waiting:** up to about 50 seconds when Google is busy (Flash-Lite gets 20 s, Flash 15 s, plus one retry).
- **If it stops working:** the Django window shows a line starting with `AI:` with Google's exact reason (the key is
  never printed), e.g. `Gemini answered 503 (busy)` or `Gemini answered 429 (daily_limit)`. If Google retires a model
  name, the next one in the list is tried automatically.
- **Limits:** each seller can use it 10 times per hour (`ai_listing` in `settings.py`). Google's free tier also
  has its own daily limit for the whole key.
- **What is sent to Google:** only the photo (already shrunk, with its location data removed) and the product name
  the seller typed. No buyer data, no prices, no addresses.
- **Privacy on the free tier:** Google may use free-tier requests to improve its products. Product photos are meant
  to be public anyway, but this is why custom request photos are never sent.
- **Switching it off:** set `AI_ENABLED=false` (or remove the key) and restart. The button disappears.
