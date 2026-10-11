# HomeHaat: project notes

A multi-seller marketplace for home businesses (bakers, pickle makers, artists, tailors, crafters).
Buyers fill one bag, pay once, and the order is split per seller. Full brief: `PROMPT.md`. Design brief: `UI-UX.md`.
Visual reference: `design/HomeHaat-demo-empty.html` (copy its look, never its data). `design/_old-styles/` is NOT used.

**Current stage: 1 of 8 — thin path end to end (done, waiting for "continue").**

---

## How we work (short version of PROMPT.md section 0)

- One stage at a time, in order. After each: lint, type-check, tests, commit `stage-N: …`, summary + 3 interview Q&As, **stop**.
- **[KEY LOGIC]** functions: tests first, then code, then a plain-English explanation in "How it works" below.
- Money is **integer paise** everywhere (₹450 = `45000`). Display only through `formatINR` (`frontend/lib/format.ts`).
- Real data only. The only seeded thing is the category list (`seed_categories`). No demo sellers/products/orders, ever.
- Unknown values show "Not provided by seller". Every number shown is computed from the database.
- Ask Rasmitha before: adding a paid service or new tool, changing a design token, breaking-model changes, leaving Razorpay test mode.

## Commands

```powershell
.\start-homehaat.ps1                 # everything: Docker Postgres, packages, migrate, seed, two windows
# backend (from backend\)
.\.venv\Scripts\python.exe manage.py test        # all backend tests (needs Postgres running)
.\.venv\Scripts\ruff.exe check . ; .\.venv\Scripts\ruff.exe format --check .
# frontend (from frontend\)
npm run lint ; npm run typecheck ; npm test
```

Ports: Postgres **5433** (Oppora uses 5432), Django **8000**, Next.js **3000** (close Oppora first).

## Folder structure

```
homehaat/
  backend/                Django + DRF (Python 3.14, Django 5.2 LTS)
    config/               settings.py (reads ../.env), urls.py (all /api/ routes in one list)
    accounts/             User (email login, role), Address, sign-up/in/out, /auth/me
    catalog/              Category, Seller, Product, ProductImage; public products; seller store/products
                          management/commands/seed_categories.py
    cart/                 CartItem; /api/cart/ (totals computed from DB prices)
    orders/               Order, SellerOrder, OrderItem; services.py [KEY LOGIC]; checkout + order views
    payments/             webhook.py [KEY LOGIC]; razorpay_client.py (only file that calls Razorpay); views.py
    reviews/, custom_requests/   models only for now (Stages 5–6)
    ai/                   empty until Stage 6
    core/tests/factories.py   test-only helpers (never used by the running site)
  frontend/               Next.js 16 (App Router) + TypeScript + Tailwind v4 + lucide-react + sonner
    app/                  pages (see "Pages" below)
    components/           Header, Footer, ProductCard, ProductImage, CategoryArt, EmptyState, AuthForm
    lib/api/*.ts          the ONLY way components get data (client.ts is the only fetch call)
    lib/format.ts         formatINR, rupeesToPaise, deliveryText (+ format.test.ts)
    lib/razorpay.ts       loads Checkout.js, opens the payment window
    lib/session.tsx       who is signed in + bag count
  design/  docs/  docker-compose.yml  start-homehaat.ps1  .env.example
```

## Design system (UI-UX.md)

Tokens live in `frontend/app/globals.css` as CSS variables and are mapped to Tailwind (`text-ink`, `bg-soft`,
`border-line`, `font-serif`…). Never use raw hex in components.

| Token | Value | | Token | Value |
|---|---|---|---|---|
| --ink | #111111 | | --sand | #F2EFEA |
| --muted | #5F5F5F | | --mist | #EEF0F2 |
| --line | #EAEAEA | | --linen | #F1EEE6 |
| --page | #FFFFFF | | --sage | #EDF0EA |
| --soft | #F6F5F2 | | --blush | #F5EDEC |
| --black-2 | #2B2B2B | | --stone | #EFEDEA |
| --error | #B42318 | | status pills | --st-*-bg / --st-* |

Fonts: Inter Tight (everything) + Instrument Serif Italic (one accent phrase per heading, class `serif`),
loaded with `next/font/google` in `app/layout.tsx`.

Shared classes (in `globals.css` `@layer components`, become full components in Stage 4):
`.wrap` `.serif` `.eyebrow` `.title` `.price` `.btn` `.btn-black` `.btn-white` `.btn-lg` `.panel` `.field-label`
`.input` `.textarea` `.field-error` `.status` + `.st-new|preparing|out_for_delivery|delivered|cancelled` `.testpill`.

Components so far: `Header`, `Footer`, `ProductCard` (+ `stockTag`), `ProductImage` (seller photo or category line
drawing on its tint), `CategoryArt` (8 fine-line drawings), `EmptyState` (soft panel, round 120px photo, heading,
one line, one action), `AuthForm`. Toast = sonner, black pill, bottom centre.

## Pages (Stage 1, plain styling)

| URL | What |
|---|---|
| `/` | hero heading + "Fresh this week" product list (empty state when none) |
| `/product/[id]` | product page, quantity, note, Add to bag |
| `/cart` | the bag (one maker in Stage 1) with totals from the server |
| `/checkout` | Address → Review → Pay (Razorpay Checkout.js) |
| `/checkout/confirming/[orderId]` | "Confirming payment…" — verifies, then polls the order |
| `/orders/[id]` | order success page (one block per seller order) |
| `/signin`, `/signup`, `/account` | email + password |
| `/sell` | plain "Open your shop" form |
| `/seller` | plain seller page: paid orders + product list |
| `/seller/products/new` | plain "Add a product" form (no photos yet) |

## API (all under `/api/`, proxied by Next.js)

`auth/csrf` · `auth/signup` · `auth/signin` · `auth/signout` · `auth/me` (GET/PATCH) · `addresses` ·
`categories` · `products` · `products/<id>` · `cart` · `cart/items` · `cart/items/<id>` · `checkout` ·
`orders` · `orders/<id>` · `payments/verify` · `payments/webhook` · `seller/store` · `seller/products` ·
`seller/products/<id>` · `seller/orders`

## Decisions and assumptions

- **Proxy:** the browser only talks to Next.js; `next.config.ts` rewrites `/api/*` → Django (adding back the
  trailing slash Django needs; `skipTrailingSlashRedirect: true`). So the session cookie is first-party.
- **Auth:** Django sessions (httpOnly, SameSite=Lax, Secure in production) + CSRF on every change. DRF only checks
  CSRF for signed-in users, so sign-up/sign-in add a `CsrfRequired` permission (stops "login CSRF").
- **Cookie names are `homehaat_session` / `homehaat_csrftoken`**, not Django's defaults. Browsers share cookies
  across ports on `localhost`, so Oppora's `sessionid`/`csrftoken` would otherwise collide with ours. The frontend
  reads the name in `lib/api/client.ts` (`CSRF_COOKIE`); keep it in sync with `settings.CSRF_COOKIE_NAME`.
- **Roles:** set only by the server. `role` is read-only in the API; opening a shop makes you a seller.
- **Next.js 16 `cacheComponents` is off** to keep the data model simple: every API call is `cache: "no-store"`.
  Caching for public pages comes in Stage 7.
- **Stage 1 limit:** one maker per bag (cart API returns 409 for a second maker). Stage 2 removes it.
- **Stock is reduced only when the payment is confirmed**, not at checkout. Checkout still locks and checks stock.
  Open question for Stage 2: two buyers can both check out the last cake before either pays; we need to decide between
  *reserving stock at checkout* (released by `expire_orders`) or *refunding the second payer*. Until then
  `mark_order_paid` floors stock at 0 so a captured payment is never lost.
- **Local payments** use the signed `/api/payments/verify/` backup (cloudflared tunnel skipped by choice). The webhook
  code is built and tested and goes live in Stage 8.
- `Seller.main_category` (nullable) was added to the Section 6 model: it's the cover-photo fallback and default
  product category (UI-UX "Open your shop: … category").
- `CustomRequest.images` is a separate `CustomRequestImage` table (up to 3), like `ProductImage`.
- `mark_order_paid(order, payment_id, amount_paise)` takes the amount too, so the webhook and verify paths share one
  amount check.
- Products without a photo show the **fine black line drawing** of their category (UI-UX.md §7), not a "3D-style"
  illustration (PROMPT.md §4 says 3D; UI-UX.md replaces it and bans 3D).
- UI copy says **"bag"** (UI-UX.md); the URL is `/cart` and the code says `cart` (PROMPT.md).
- Frontend unit tests use Node's built-in test runner (`node --test`), so no extra test tool was added.
- Tests use a fast password hasher (`settings.py`, only when running `manage.py test`).

---

## How it works (read this before interviews)

### 1. Money is integer paise

₹450 is stored as `45000`. Computers can't store 0.1 exactly as a float (`0.1 + 0.2 = 0.30000000000000004`), and
with money that turns into missing paise. Integers are always exact. We only turn paise into text in one place,
`formatINR`, which splits the number with integer maths (`45050 → 450 rupees + 50 paise → "₹450.50"`). When a seller
types a price, `rupeesToPaise` reads the text itself (`"450.5"` → `45050`), never `parseFloat`.

> *Say it:* "All money is integer paise in the database, API and frontend. One helper formats it, so there are no
> rounding bugs and no two places that format money differently."

### 2. `create_order_from_cart(user, address)` — `backend/orders/services.py` [KEY LOGIC]

**What it does:** turns this buyer's bag into a *pending* order, ready to pay.

**Step by step:**
1. Read the buyer's cart items (`CartItem.objects.filter(user=user)`) — only *this* buyer's rows. Empty → error.
2. Load the products with `select_for_update()`. This **locks those rows** in Postgres until the transaction ends,
   so no other checkout can change their stock while we're checking it. `of=("self",)` locks only the products.
3. Check there's exactly one seller (Stage 1) and the store isn't paused.
4. Check every product is still active and has enough stock. If not → `SoldOutError` with the product names, so the
   bag can show which ones.
5. Compute the totals **from the database prices**: `items_total = Σ price_paise × qty`, plus the seller's delivery fee.
6. Create the `Order` (pending), one `SellerOrder`, and the `OrderItem`s with **snapshots** of the name and price.
7. Don't touch stock or the cart yet — that happens only when the payment is confirmed.

**Why it's safe:**
- The whole function is wrapped in **`@transaction.atomic`**: if anything fails halfway (e.g. sold out), *nothing* is
  saved. You never get an order without its items.
- **Prices never come from the request.** The checkout API only accepts `address_id`; a test sends
  `grand_total: 100` and proves it's ignored.
- **Snapshots** (`OrderItem.name`, `unit_price`, `Order.ship_to`) mean a seller editing a product, or a buyer editing
  their address, can't change an order that already exists.
- The address is looked up with `user=request.user`, so you can't ship to someone else's saved address.

**Django features:** `transaction.atomic`, `select_for_update(of=...)`, `select_related`, `bulk_create`, JSONField.

> *Say it:* "Checkout reads the cart on the server, locks the products with `select_for_update` inside
> `transaction.atomic`, checks stock, and computes the total from database prices. If the buyer sends a price,
> it's ignored. Everything is saved together or not at all."

### 3. Signature checks — `backend/payments/webhook.py` [KEY LOGIC]

Anyone on the internet can send a POST to our webhook URL saying "order 5 is paid". So we need proof it's Razorpay.

- Razorpay and HomeHaat share a **secret**. Razorpay computes **HMAC-SHA256(message, secret)** and sends it in a
  header. We compute the same thing ourselves and compare. Without the secret, nobody can produce the right value.
- **Webhook:** message = the exact raw request body, secret = `RAZORPAY_WEBHOOK_SECRET`,
  header = `X-Razorpay-Signature`. We check the *raw bytes* before parsing JSON, because any change breaks the match.
- **Checkout handler (verify backup):** message = `"order_id|payment_id"`, secret = the Key Secret.
- We compare with **`hmac.compare_digest`**, which takes the same time no matter where the strings differ. A normal
  `==` stops at the first wrong character, and an attacker could time that to guess the signature piece by piece.
- An empty secret or empty signature is always rejected (`_signature_matches`), and the webhook returns 503 if no
  secret is configured, so a missing setting can never mean "trust everything".

> *Say it:* "The webhook is verified with HMAC-SHA256 of the raw body using a shared secret, compared in constant
> time with `hmac.compare_digest`. A bad signature gets a 400 and nothing changes."

### 4. `mark_order_paid(order, payment_id, amount_paise)` — idempotent [KEY LOGIC]

**What it does:** the *only* place an order becomes paid. Both the webhook and `/api/payments/verify/` call it.

**Step by step:**
1. Re-load the order with **`select_for_update()`** (locks the order row).
2. Already **paid** → return `False` and do nothing. This is what *idempotent* means: calling it 1 time or 5 times
   has the same result. Razorpay retries webhooks, and the verify call can arrive at the same time as the webhook.
3. Not pending (e.g. failed) → refuse. **Amount ≠ `grand_total`** → `AmountMismatchError`, order stays pending.
4. Set `payment_status="paid"`, save the `razorpay_payment_id` (unique in the DB) and `paid_at`.
5. Reduce stock with **`F("stock") - qty`**. `F()` makes Postgres do `stock = stock - 1` itself, instead of Python
   reading 5 and writing 4 (which could overwrite someone else's change). `Greatest(..., 0)` stops it going negative.
6. Remove just those products from the buyer's cart (things added after checkout stay).

**Why it's safe:** the lock in step 1 means two simultaneous calls run one after the other — the second one sees
"paid" and stops. So stock is reduced exactly once (a test sends the same webhook 3 times and checks stock went
down by 1). It's all inside `transaction.atomic`, so "paid" and "stock reduced" happen together or not at all.

**Django features:** `transaction.atomic`, `select_for_update`, `F()` expressions, `Greatest`, `update()`.

> *Say it:* "Marking paid is idempotent: it locks the order row, and if it's already paid it returns early. So a
> retried webhook can't reduce stock twice. Stock goes down with an `F()` expression, so the database does the
> subtraction atomically."

### 5. The payment flow end to end

```
Bag ─► POST /api/checkout/ {address_id}
       └ create_order_from_cart → Order (pending)  ─► Razorpay Orders API (amount fixed on their side)
Browser opens Razorpay Checkout.js ─► buyer pays with a test card
       └ Razorpay returns {order_id, payment_id, signature} to the browser
"Confirming payment…" page ─► POST /api/payments/verify/   (local backup)
       └ check signature → ask Razorpay for the payment → capture if needed → amount check → mark_order_paid
       └ (production: Razorpay → POST /api/payments/webhook/ → signature → mark_order_paid)
"Confirming payment…" polls GET /api/orders/<id>/ until "paid" ─► Order placed page
Seller page lists only PAID seller orders, with the buyer's delivery address.
```

The browser never decides an order is paid — it only shows "Confirming payment…" and asks the server.

### 6. Sessions, CSRF and the proxy

The browser talks only to `localhost:3000`. Next.js forwards `/api/*` to Django, so Django's session cookie belongs
to the same site (first-party) and can be **httpOnly** (JavaScript can't read it, so an XSS bug can't steal it).
Because cookies are sent automatically, another website could try to make your browser POST to us (CSRF). Django
blocks that: every change must include the `csrftoken` value in an `X-CSRFToken` header, which only our own pages
can read. `lib/api/client.ts` does this for every POST/PATCH/DELETE.

---

## Interview notes

### Stage 1
1. **Why integer paise instead of decimals or floats?** Floats can't represent 0.1 exactly, so sums drift by a paisa.
   Integers are exact, and one shared `formatINR` keeps display consistent.
2. **How do you stop someone faking a payment?** An order becomes paid only on the server, after an HMAC-SHA256
   signature check (constant-time compare) *and* an amount check against the order total. The browser callback just
   shows "Confirming payment…".
3. **What if Razorpay sends the same webhook twice?** `mark_order_paid` is idempotent: it locks the order row with
   `select_for_update` and returns early if it's already paid, so stock is reduced once. A test proves it.

## Stage log

- **Stage 1** — monorepo, Docker Postgres (5433), `start-homehaat.ps1`, Django + Next.js via `/api` proxy, email
  sign-in, all Section 6 models, `seed_categories`, tokens + fonts, product list/page, single-seller bag, checkout with
  one address, Razorpay test payment (verify backup), webhook (tested), success page, seller page with paid orders.
