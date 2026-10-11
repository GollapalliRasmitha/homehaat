# HomeHaat: project notes

A multi-seller marketplace for home businesses (bakers, pickle makers, artists, tailors, crafters).
Buyers fill one bag, pay once, and the order is split per seller. Full brief: `PROMPT.md`. Design brief: `UI-UX.md`.
Visual reference: `design/HomeHaat-demo-empty.html` (copy its look, never its data). `design/_old-styles/` is NOT used.

**Current stage: 3 of 8 — seller side (done, waiting for "continue").**

---

## How we work (short version of PROMPT.md section 0)

- One stage at a time, in order. After each: lint, type-check, tests, commit `stage-N: …`, push to GitHub
  (`origin` = https://github.com/GollapalliRasmitha/homehaat, branch `main`), summary + 3 interview Q&As, **stop**.
- Before every push: `.env` must stay untracked (it's in `.gitignore`); only `.env.example` with empty values is
  committed. Never put real keys in code, docs or chat.
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
    catalog/              Category, Seller, Product, ProductImage; public products; seller store/products/photos
                          images.py (check + clean uploads); management/commands/seed_categories.py
    cart/                 CartItem; /api/cart/ grouped by seller, guest preview + merge (totals from DB prices)
    orders/               Order, SellerOrder, OrderItem; services.py + status.py [KEY LOGIC]; checkout, order,
                          seller-order and overview views
                          management/commands/expire_orders.py
    payments/             webhook.py [KEY LOGIC]; razorpay_client.py (only file that calls Razorpay); views.py
    reviews/              Review model; seller's read-only reviews list (writing reviews: Stage 6)
    custom_requests/      models only for now (Stage 5)
    ai/                   empty until Stage 6
    core/tests/factories.py   test-only helpers (never used by the running site)
  frontend/               Next.js 16 (App Router) + TypeScript + Tailwind v4 + lucide-react + sonner
    app/                  pages (see "Pages" below)
    components/           Header, Footer, ProductCard, ProductImage, CategoryArt, EmptyState, AuthForm,
                          PasswordInput, BagLine, OrderTimeline, LoadError, ServerStatus, StatCard,
                          ConfirmDialog (Radix), PhotoPicker, StoreForm, ProductForm, IncomingOrderCard
    lib/api/*.ts          the ONLY way components get data (client.ts is the only fetch call)
    lib/format.ts         formatINR, rupeesToPaise, deliveryText (+ format.test.ts)
    lib/guest-bag.ts      signed-out bag in localStorage: ids + qty only, never prices (+ guest-bag.test.ts)
    lib/bag.ts            useBag(): one bag API for pages, signed in or guest
    lib/compress-image.ts shrinks photos in the browser before upload (+ test)
    lib/seller-context.tsx useSeller(): the seller's shop, shared by the dashboard pages
    lib/razorpay.ts       loads Checkout.js, opens the payment window (closes when the hold ends)
    lib/session.tsx       who is signed in + bag count; signedIn() merges the guest bag
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
one line, one action), `AuthForm`, `PasswordInput` (show/hide eye toggle, hidden by default — use it for
**every** password field), `BagLine` (+ `problemText`), `OrderTimeline` (4 bars: New → Preparing → Out for
delivery → Delivered), `StatCard` (soft panel, big number, muted label), `ConfirmDialog` (Radix AlertDialog for
"can't be undone"), `PhotoPicker` (drag-and-drop, reorder by drag or ← → buttons, max N, compresses in the
browser), `StoreForm` (Open your shop + Store settings), `ProductForm` (add/edit), `IncomingOrderCard` (one seller
order: buyer contact, items, next-step button, Cancel with confirm). Toast = sonner, black pill, bottom centre.

## Pages (plain styling until Stage 4)

| URL | What |
|---|---|
| `/` | hero heading + "Fresh this week" product list (empty state when none) |
| `/product/[id]` | product page, quantity, note, Add to bag |
| `/cart` | the bag grouped by maker (guest or signed in), sold-out flags, "split into N seller orders" |
| `/checkout` | Address → Review (grouped) → Pay; sold-out list with "Remove them from my bag" |
| `/checkout/confirming/[orderId]` | "Confirming payment…" — verifies, then polls the order |
| `/orders` | my orders (failed attempts hidden), each maker's status |
| `/orders/[id]` | one block per seller order with OrderTimeline; `?placed=1` shows "Order placed" |
| `/signin`, `/signup`, `/account` | email + password |
| `/sell` | Open your shop (StoreForm: link auto from name and editable, cover photo) → then Add a product |
| `/seller` | SellerShell (`app/seller/layout.tsx`: shop name, Paused badge, tabs) → **Overview**: greeting, 4 StatCards, open orders |
| `/seller/orders` | status filter chips with counts; next-step button; Cancel with confirmation |
| `/seller/products` | list with photo, price, stock, sold, Live/Hidden switch, Edit |
| `/seller/products/new`, `/seller/products/[id]` | ProductForm with up to 5 photos |
| `/seller/requests` | empty state (custom requests: Stage 5) |
| `/seller/reviews` | read-only reviews + average (empty until Stage 6 lets buyers review) |
| `/seller/settings` | StoreForm + Pause my shop |

## API (all under `/api/`, proxied by Next.js)

`auth/csrf` · `auth/signup` · `auth/signin` · `auth/signout` · `auth/me` (GET/PATCH) · `addresses` ·
`categories` · `products` · `products/<id>` · `cart` · `cart/items` · `cart/items/<id>` · `cart/preview` (guest,
no sign-in) · `cart/merge` · `checkout` ·
`orders` · `orders/<id>` · `payments/verify` · `payments/webhook` · `seller/overview` · `seller/store` (GET/POST/
PATCH) · `seller/store/cover` (POST/DELETE) · `seller/products` · `seller/products/<id>` ·
`seller/products/<id>/images` (POST) · `seller/products/<id>/images/order` · `seller/products/<id>/images/<img>`
(DELETE) · `seller/orders` (`?status=`) · `seller/orders/<id>/status` (POST `{status}`) · `seller/reviews`

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
- **Stock is held at checkout for 15 minutes** (Rasmitha's decision, Stage 2; PROMPT.md said 30 min for
  `expire_orders`, 15 wins). `Product.stock` therefore means *available* stock. `settings.ORDER_HOLD_MINUTES = 15`.
- **`Order.stock_held`** says whether an order has stock off the shelf. Release gives stock back only if it's True,
  so Stage 1 orders (which never held stock) can't inflate stock when they expire.
- **Holds are released** by `expire_orders` (start script, and a GitHub Actions schedule in Stage 8), **and lazily at
  the start of every checkout**, so an expired hold never blocks the next buyer even if the job hasn't run. A buyer
  pressing Pay again also releases their own earlier unpaid attempt. Razorpay Checkout gets a `timeout` so the
  window closes when the hold ends.
- **Late payment** (money arrives after the hold ended): `mark_order_paid` takes the stock again per seller; a seller
  whose items are gone gets their part *cancelled with `refund_needed`* (no live refunds in test mode). The order is
  still marked paid, because the money was taken.
- **Guest bag** lives in `localStorage` (product ids, qty, note only). The server prices it (`cart/preview`) and merges
  it at sign-in/sign-up (`cart/merge`: adds quantities, caps at stock and 50, skips your own products).
- My orders hides `failed` attempts (closed payment windows, expired holds); the detail page still opens.
- `next.config.ts` reads an optional `NEXT_DIST_DIR`, only so a throwaway end-to-end copy can run beside your
  normal one (ports 3001/8001, database `homehaat_e2e`). Normal runs use `.next`.
- **Local payments** use the signed `/api/payments/verify/` backup (cloudflared tunnel skipped by choice). The webhook
  code is built and tested and goes live in Stage 8.
- `Seller.main_category` (nullable) was added to the Section 6 model: it's the cover-photo fallback and default
  product category (UI-UX "Open your shop: … category").
- `CustomRequest.images` is a separate `CustomRequestImage` table (up to 3), like `ProductImage`.
- `mark_order_paid(order, payment_id, amount_paise)` takes the amount too, so the webhook and verify paths share one
  amount check.
- **Errors never crash a page.** Rules for every page:
  - every API call has a `.catch`/`try`; loading failures render `<LoadError error onRetry>` (reason + Try again);
  - action failures show a toast built from `errorMessage(error)`;
  - forms put `error.fieldError("field")` next to the field.

  `apiFetch` turns every failure into an `ApiError` with a plain-words message (`friendlyMessage`: Django's
  `detail`, else first form error, else per status: 0 = can't reach, 5xx = server problem, 404, 429). A dropped
  connection becomes `status 0`, not a raw `TypeError`. In development, failures are also logged with
  `console.warn` (method, path, status).
- **The session never pretends you're signed out** when the server can't be reached: `serverError` is set,
  `<ServerStatus>` under the header shows the reason + Try again, and pages redirect to Sign in only when
  `signedOut` (the server confirmed no user). `app/error.tsx` and `app/not-found.tsx` are the last safety net.
- **Photos** (`catalog/images.py`): the browser shrinks them to 1600 px JPEG first (`compress-image.ts`); the server
  still opens and decodes every file, accepts only JPEG/PNG/WebP up to 5 MB, turns it upright, shrinks it to
  1600 px and **re-saves it without EXIF** (no GPS location of the seller's home). Max 5 per product; order is
  `ProductImage.position`. The "resized copy for cards" and Cloudinary are Stage 7.
- **Cancelling a paid seller order** sets `refund_needed` and puts that order's items back into stock.
- **Shop link (slug)**: made from the name, editable at Open your shop and in Store settings; lowercase letters,
  numbers and dashes; unique (keeping your own is fine).
- **Pause store** = `Seller.is_active=False`: products disappear for buyers and checkout refuses that seller.
- **Reviews**: the seller's read-only list exists now; *writing* reviews (and the Section 8 test "a buyer can't
  review without a delivered order") is Stage 6, where the review endpoint is built.
- **Overview "earnings this week"** = paid in the last 7 days, items + delivery, cancelled parts excluded.
- **Test copy media**: `MEDIA_ROOT` can be set by env; the throwaway e2e copy uses its own folder, so it never
  touches real uploads.
- Known limit: while an item is held, its product page shows the reduced stock ("Sold out" for the last one) until
  the hold is paid or released. That's the honest answer, since another buyer is paying for it right now.
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

**What it does:** turns this buyer's bag into *one* pending order (one payment), **split into one `SellerOrder`
per seller**, and **holds the stock** for 15 minutes.

**Step by step:**
0. If this buyer has an earlier unpaid attempt (they closed the payment window and pressed Pay again), release it
   first, so their own hold doesn't block them.
1. Read the buyer's cart items (`CartItem.objects.filter(user=user)`): only *this* buyer's rows. Empty → error.
2. Load the products with `select_for_update()`, which **locks those rows** until the transaction ends (see section 7).
   `of=("self",)` locks only the product rows, and `order_by("id")` locks them in the same order every time.
3. **Group the cart by seller** (`defaultdict(list)`: seller → their cart items). Any paused store → error. Buying
   from your own shop → error.
4. Check every product is still active and has enough stock. If not → `SoldOutError` with `{product_id, name}` for
   each, so the bag can show them and remove them in one click.
5. Compute the money **from database prices**: each line `price_paise × qty`; `items_total` = all lines;
   `delivery_total` = **one delivery fee per seller**; `grand_total` = both.
6. Create the `Order` (pending, `stock_held=True`), then for each seller one `SellerOrder` (that seller's items
   subtotal + their delivery fee) with its `OrderItem`s, which **snapshot** the name and price.
7. **Hold the stock:** `stock = F("stock") - qty` for each line. The rows are still locked, so nothing can change
   between the check in step 4 and this.
8. The cart is *not* cleared yet; that happens only when the payment is confirmed.

Example: a cake (₹450 × 2) and a candle (₹50) from a baker with ₹40 delivery, plus pickles (₹120 × 3) from a pickle
maker with ₹30 delivery → two SellerOrders: baker ₹950 + ₹40, pickles ₹360 + ₹30 → one payment of **₹1,380**.

**Why it's safe:**
- The whole function is wrapped in **`@transaction.atomic`**: if anything fails halfway (e.g. one item sold out),
  *nothing* is saved and *no* stock is held. You never get half an order, or stock held for an order that doesn't
  exist.
- **Prices never come from the request.** The checkout API only accepts `address_id`; a test sends
  `grand_total: 100` and proves it's ignored.
- **Snapshots** (`OrderItem.name`, `unit_price`, `Order.ship_to`) mean a seller editing a product, or a buyer editing
  their address, can't change an order that already exists.
- The address is looked up with `user=request.user`, so you can't ship to someone else's saved address.

**Django features:** `transaction.atomic`, `select_for_update(of=...)`, `F()`, `bulk_create`, `defaultdict` grouping.

> *Say it:* "Checkout reads the cart on the server, locks the products with `select_for_update` inside
> `transaction.atomic`, groups the items by seller and creates one SellerOrder each, with one delivery fee per
> seller. Prices come from the database, and the stock is held right away for 15 minutes. It's all or nothing."

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
3. Must be pending, or failed (a *late* payment after the hold ran out). **Amount ≠ `grand_total`** →
   `AmountMismatchError`, nothing changes.
4. Normal case: the stock was already held at checkout (`stock_held=True`), so **stock isn't touched again**.
   Late case (`stock_held=False`): `_take_stock_again` locks each seller's products and, if they're all still there,
   takes them with `F("stock") - qty`. A seller whose items are gone gets their SellerOrder **cancelled with
   `refund_needed=True`**. The money was taken, so we record it rather than lose it.
5. Set `payment_status="paid"`, save the `razorpay_payment_id` (unique in the DB) and `paid_at`.
6. Remove just those products from the buyer's cart (things added after checkout stay).

**Why it's safe:** the lock in step 1 means two simultaneous calls run one after the other; the second one sees
"paid" and stops. A test sends the same webhook 3 times and checks the stock went down once. Everything is inside
`transaction.atomic`.

**Django features:** `transaction.atomic`, `select_for_update`, `F()` expressions, `prefetch_related`, `update()`.

> *Say it:* "Marking paid is idempotent: it locks the order row and returns early if it's already paid. Stock was
> already held at checkout, so paying doesn't touch it. If the money arrives after the hold ran out, we try to take
> the stock again, and if a seller's items are gone we cancel just that part and flag a refund."

### 5. The payment flow end to end

```
Bag ─► POST /api/checkout/ {address_id}
       └ expire_unpaid_orders (free old holds) → create_order_from_cart
         → Order (pending) + one SellerOrder per seller, stock held 15 min
         ─► Razorpay Orders API (amount fixed on their side)  [fails → release_hold]
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

### 7. The race for the last item — `select_for_update` [KEY LOGIC]

Two buyers press Pay for the **last cake** at the same instant. Without care, both read "stock = 1", both pass the
check, and both buy it: one cake, two paid orders.

`select_for_update()` makes Postgres put a **row lock** on that product. Buyer A's checkout gets the lock and runs.
Buyer B's checkout reaches the same line and **waits**. A holds the cake (stock 1 → 0) and commits, which releases
the lock. Only then does B continue; Postgres hands B the *fresh* row (stock 0), so B gets "Some items sold out
while you were shopping." One order, one sold-out message, stock 0, never −1.

The test (`orders/tests/test_race.py`) really does this: two threads with their own database connections, started
together by a `threading.Barrier`, inside a `TransactionTestCase` (real transactions, like two real requests).
**Proof the lock matters:** with `select_for_update` removed, the same test fails every time. Both buyers pass the
check, and the second crashes trying to set the stock to −1.

`order_by("id")` on the locked query avoids a *deadlock*: if A locked cake-then-jar while B locked jar-then-cake,
each would wait for the other forever. Locking in id order means they always queue the same way.

> *Say it:* "Checkout locks the product rows with `select_for_update`. The second buyer waits for the first to
> commit, then sees the updated stock and gets a sold-out error. I proved it with a two-thread test, and showed the
> test fails without the lock."

### 8. Holding stock for 15 minutes — `release_hold` and `expire_unpaid_orders` [KEY LOGIC]

Checkout takes the stock off the shelf straight away, so two people can't both pay for the last cake. But someone
might start checkout and then walk away, so the hold must end:

- **`release_hold(order)`** locks the order. If it's still **pending**, it puts the held stock back
  (`stock = F("stock") + qty`, only if `stock_held` is True), sets `failed`, and sets `stock_held=False`. For a paid
  or already-failed order it does nothing, so it's safe to call twice.
- **`expire_unpaid_orders()`** releases every pending order older than `ORDER_HOLD_MINUTES` (15). It runs from
  `python manage.py expire_orders` (start script now, a schedule in Stage 8) **and at the start of every checkout**,
  so an abandoned hold never blocks the next buyer.
- When Razorpay can't be reached at checkout, the new order is released immediately.
- Razorpay's window gets a `timeout`, so it closes when the hold ends. If money still arrives late, section 4
  handles it.

Why `stock_held`? Stage 1 orders took stock only when paid. Without the flag, releasing an old Stage 1 order would
*add* stock that was never taken away. The flag makes "give back" happen only for orders that really hold stock.

> *Say it:* "Stock is held at checkout for 15 minutes. If the order isn't paid, a release puts it back. That runs
> on a schedule, and also lazily at the next checkout so it never depends on the job alone. A flag on the order
> makes sure we only give back stock we actually took."

### 9. The guest bag

Signed-out visitors can fill a bag. It's kept in their browser's `localStorage` as product ids, quantities and
notes, **never prices**. To show it, the browser sends that list to `POST /api/cart/preview/`, and the server prices
it exactly like a real cart. When they sign in or sign up, `session.signedIn()` sends the list to
`POST /api/cart/merge/`, which adds it to their account bag (quantities added together, capped at stock and 50, own
products skipped), then clears the browser copy. Checkout still needs sign-in.

### 10. `advance_status(seller_order, new_status, user)` — `backend/orders/status.py` [KEY LOGIC]

**What it does:** moves a seller's part of an order one step:
`new → preparing → out_for_delivery → delivered`, or `new / preparing → cancelled`.

**Step by step:**
1. Lock the SellerOrder row with `select_for_update()` (two taps, or a phone and a laptop, are handled one after
   the other).
2. **Ownership:** if `part.seller.owner` isn't this user → `NotYourOrderError`. Buyers and other sellers get the
   same answer as for a missing order (404), so we don't even reveal it exists.
3. **Only paid orders** can be moved.
4. **Only along the arrows:** `ALLOWED_MOVES` is a small dictionary, current status → set of allowed next statuses.
   Anything else (skipping, going back, changing a delivered or cancelled order, a made-up status) →
   `StatusError` with a sentence the seller can read.
5. Set the status and its timestamp (`preparing_at`, `delivered_at`…).
6. **Cancel:** set `refund_needed=True` and give the items back to stock with `F("stock") + qty`.
7. `save(update_fields=[…])` writes *only* those columns, so the money can never change here. The API reads only
   `status` from the request, and a test sends `subtotal: 1` and proves it's ignored.

**Why it's safe:** the rules live in one table (`ALLOWED_MOVES`), not scattered `if`s; the check happens on the
server inside a locked transaction; ownership is checked before anything else.

**Django features:** `transaction.atomic`, `select_for_update`, `TextChoices`, `F()`, `save(update_fields=…)`.

> *Say it:* "Status changes go through one function with an allowed-moves table. It locks the row, checks the
> seller owns this part and the order is paid, rejects any move that isn't in the table, and saves only the status
> fields, so a seller can never change amounts or skip steps."

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

### Stage 2
1. **How do you split one payment between several sellers?** One `Order` holds the single payment; checkout groups
   the bag by seller and creates one `SellerOrder` per seller with its own subtotal and delivery fee. Each seller
   only sees and updates their own part. A test checks a 3-seller bag makes exactly 3 seller orders with the right
   amounts.
2. **Two people buy the last item at the same moment: what happens?** Checkout locks the product rows with
   `select_for_update` inside `transaction.atomic`. The second checkout waits, then reads stock 0 and gets
   "sold out". A two-thread test proves it, and fails if the lock is removed.
3. **Why hold stock at checkout instead of when paid, and what if they never pay?** Holding at checkout means the
   buyer who reached payment can't lose the item to someone slower. The hold lasts 15 minutes; `release_hold` puts
   the stock back for unpaid orders. It runs on a schedule and at every checkout, and a `stock_held` flag stops it
   giving back stock that was never taken.

### Stage 3
1. **How do you stop a seller changing an order in a way they shouldn't?** All status changes go through
   `advance_status`, which checks ownership, that the order is paid, and an allowed-moves table, then saves only
   the status fields. Sellers can't skip steps, go back, or touch amounts; tests cover each case.
2. **How do you handle uploaded photos safely?** The server never trusts the file name: it decodes the image with
   Pillow, accepts only JPEG/PNG/WebP under 5 MB, resizes it, and re-saves it without EXIF, so the GPS location in
   phone photos is removed. The browser shrinks photos first so uploads are fast on mobile data.
3. **How do you make sure seller A can't see seller B's data?** Every seller query starts from
   `request.user.seller` (e.g. `user.seller.products`), so another seller's id simply isn't found (404). Tests try
   reading, editing and uploading to another seller's orders and products.

## Stage log

- **Stage 1** — monorepo, Docker Postgres (5433), `start-homehaat.ps1`, Django + Next.js via `/api` proxy, email
  sign-in, all Section 6 models, `seed_categories`, tokens + fonts, product list/page, single-seller bag, checkout with
  one address, Razorpay test payment (verify backup), webhook (tested), success page, seller page with paid orders.
- **Stage 2**: bag grouped by seller, guest bag + merge on sign-in, grouped checkout review, one SellerOrder per
  seller, stock held 15 min (`release_hold`, `expire_orders`, lazy expiry at checkout, Razorpay timeout), late-payment
  handling, sold-out list with one-click remove, My orders + order detail with OrderTimeline, race-condition test.
- **Stage 3**: SellerShell with 6 tabs; Overview stats from data; Orders with filter, next-step and confirmed Cancel
  (`advance_status`); Products with Live/Hidden switch and add/edit with up to 5 photos (browser compression,
  server checks + EXIF stripped); Store settings with editable shop link, cover photo and Pause; seller reviews
  list; permission tests; `docs/seller-guide.md` with screenshots.
