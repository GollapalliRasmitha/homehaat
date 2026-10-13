# HomeHaat: project notes

A multi-seller marketplace for home businesses (bakers, pickle makers, artists, tailors, crafters).
Buyers fill one bag, pay once, and the order is split per seller. Full brief: `PROMPT.md`. Design brief: `UI-UX.md`.
Visual reference: `design/HomeHaat-demo-empty.html` (copy its look, never its data). `design/_old-styles/` is NOT used.

**Current stage: 6 of 8 — reviews, search and the AI listing helper (done, waiting for "continue"). Next: deploy, with
Cloudinary pulled forward.** Stage 7 must-do: custom request photos visible only to that buyer and that seller.

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
    accounts/             User (email login, role), Address, sign-up/in/out, /auth/me; address_rules.py (Indian
                          pincode/mobile, real letters)
    catalog/              Category, Seller, Product, ProductImage; public products; seller store/products/photos
                          images.py (check + clean uploads); browse.py (full-text search, filters, sort, pages,
                          "Did you mean", trending, public stores); management/commands/seed_categories.py
    cart/                 CartItem; /api/cart/ grouped by seller, guest preview + merge (totals from DB prices)
    orders/               Order, SellerOrder, OrderItem; services.py + status.py [KEY LOGIC]; checkout, order,
                          seller-order and overview views
                          management/commands/expire_orders.py
    payments/             webhook.py [KEY LOGIC]; razorpay_client.py (only file that calls Razorpay); views.py
    reviews/              Review model; services.py write_review [KEY LOGIC] (only after delivery); views
    custom_requests/      CustomRequest + images; services.py [KEY LOGIC] (rules + accept -> bag); buyer and
                          seller views
    ai/                   listing.py [KEY LOGIC] (prompt, schema, validate_listing); gemini_client.py (only file
                          that calls Gemini); views.py (seller/ai/listing)
    core/tests/factories.py   test-only helpers (never used by the running site)
  frontend/               Next.js 16 (App Router) + TypeScript + Tailwind v4 + lucide-react + sonner
    app/                  pages (see "Pages" below)
    components/           Header, Footer, ProductCard, ProductImage, CategoryArt, EmptyState, AuthForm,
                          PasswordInput, BagLine, OrderTimeline, LoadError, ServerStatus, StatCard,
                          ConfirmDialog (Radix), PhotoPicker, StoreForm, ProductForm, IncomingOrderCard,
                          HeroSearch, ShowcaseCard, CategoryTile(+Grid), ProductGrid, QuickAdd, WishlistButton,
                          MakerCard(+Grid), Monogram, SectionHead, ShareButton, SafeImage/SafeImg, RequestCard,
                          ItemThumb, Stars (+StarInput), ReviewForm, AddressForm (add + update), AccountMenu,
                          SellerBar, TakingOrders
    lib/api/*.ts          the ONLY way components get data (client.ts is the only fetch call)
    lib/format.ts         formatINR, rupeesToPaise, deliveryText (+ format.test.ts)
    lib/address-rules.ts  the same address rules as the server, for messages next to each field (+ test)
    lib/product-controls.ts productStatus (Live / Out of stock / Hidden) + deleteText (+ test)
    lib/guest-bag.ts      signed-out bag in localStorage: ids + qty only, never prices (+ guest-bag.test.ts)
    lib/bag.ts            useBag(): one bag API for pages, signed in or guest
    lib/compress-image.ts shrinks photos in the browser before upload (+ test)
    lib/explore.ts        Explore filters <-> URL <-> API query (+ test)
    lib/wishlist.ts       hearts: product ids in localStorage, synced everywhere (+ test)
    lib/bag-math.ts       withQty(): the bag after a quantity change, for optimistic updates (+ test)
    lib/add-to-bag.ts     addProductToBag(): one "add to bag" for the product page and the card's + button
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
order: buyer contact, items, next-step button, Cancel with confirm), `HeroSearch` (82px pill, a plain GET form to
/explore), `ShowcaseCard` (radius 28 photo, white label card, round arrow), `CategoryTile` (square photo radius 20,
zooms on hover, optional live count), `ProductCard` (no box; square photo radius 22, heart top-right, stock tag
top-left, maker link, name, delivery, price, round black +) + `ProductGrid` (2 columns on phones), `MakerCard`
(soft panel, `Monogram` in a dark tone with the italic serif initial), `SectionHead` (title + one serif accent +
link), `ShareButton` (share sheet or copy link). Toast = sonner, black pill, bottom centre.

Tokens added in Stage 4: `--mono-1…5` (monogram dark tones, from the reference file). No existing token changed.

## Pages (plain styling until Stage 4)

| URL | What |
|---|---|
| `/` | hero + pill search · 3 showcase cards · Browse by *category* · Trending *nearby* (hidden until real orders) · Fresh *this week* (or "Newest *finds*" if nothing is from this week) · black custom-order banner · Makers *near you* |
| `/explore` | search & category: title, search box, sort, In stock only, price range, category chips, page (all in the URL); real total, "Did you mean …?", Previous/Next (24 per page); matching makers above the grid |
| `/categories` | 8 tiles with live product counts |
| `/makers` | all open shops |
| `/store/[slug]` | cover (upload, else the main category photo), "Not taking orders right now" when paused, monogram, name, kind · area, bio, facts, Request a custom order / Manage my shop, Share, ARIA tabs per category + Reviews |
| `/wishlist` | saved products (from this browser) |
| `/custom` | request form (maker, description, up to 3 photos, needed-by, budget; `?maker=` preselects) + Your requests (Accept and add to bag / Decline / Add to bag again) |
| `/product/[id]` | gallery (up to 5), maker link, price + stock pill, description, quantity, note, Add to bag, Save, delivery rows, More from this seller |
| `/cart` | the bag grouped by maker (guest or signed in), sold-out flags, "split into N seller orders" |
| `/checkout` | Address → Review (grouped) → Pay; sold-out list with "Remove them from my bag" |
| `/checkout/confirming/[orderId]` | "Confirming payment…" — verifies, then polls the order |
| `/orders` | "Buying · My orders" (failed attempts hidden), each maker's status |
| `/orders/[id]` | one block per seller order with OrderTimeline; `?placed=1` shows "Order placed"; delivered → **Write a review** / Your review + Edit |
| `/signin`, `/signup`, `/account` | email + password |
| `/account/addresses` | "Buying · Saved addresses": list, Update address (old ones that break the rules), Add an address |
| `/sell` | Open your shop (StoreForm: link auto from name and editable, cover photo) → then Add a product |
| `/seller` | **Seller mode**: the black `SellerBar` replaces the header; SellerShell (`app/seller/layout.tsx`) = tabs Overview · Shop orders (count) · Products · Custom requests · Reviews · Settings, and the page's h1 "Selling · <tab>" (+ Paused badge) → **Overview**: Taking orders switch, greeting, 4 StatCards (products "N · M out of stock"), open orders |
| `/seller/orders` | "Selling · Shop orders": status filter chips with counts; next-step button; Cancel with confirmation (buttons full width on phones) |
| `/seller/products` | rows (`ProductRow`): photo, name, "₹price · stock · sold", Live / Out of stock / Hidden pill; Mark out of stock · Back in stock (inline "How many can you make?" panel) · Hide/Show · Edit · Delete (inline confirmation card) |
| `/seller/products/new`, `/seller/products/[id]` | ProductForm with up to 5 photos; **Write listing with AI** (only when AI is on) → suggestion with Use this / Dismiss |
| `/seller/requests` | filter chips with counts; Send quote (₹ + note) / Decline with confirm; the Overview shows "N requests waiting for your price" |
| `/seller/reviews` | read-only reviews (stars, first name, date) + average |
| `/seller/settings` | StoreForm (Pause moved to the Overview "Taking orders" switch) |

## API (all under `/api/`, proxied by Next.js)

`auth/csrf` · `auth/signup` · `auth/signin` · `auth/signout` · `auth/me` (GET/PATCH; user has `shop_name`, `open_orders`) ·
`addresses` (each with
`problems`) · `addresses/<id>` (GET/PATCH, mine only) ·
`categories` (with live `product_count`) · `products` (`?q= category= seller= min_price= max_price=` (paise)
`in_stock=1 sort=relevance|newest|price_asc|price_desc|rating|trending ids= limit=`) · `search` (same filters + `page=` →
`{count, page, pages, page_size, results, suggestion}`) · `products/<id>` · `stores`
(`?q= limit=`) · `stores/<slug>` · `stores/<slug>/reviews` · `cart` · `cart/items` · `cart/items/<id>` · `cart/preview` (guest,
no sign-in) · `cart/merge` · `checkout` ·
`orders` · `orders/<id>` · `payments/verify` · `payments/webhook` · `seller/overview` · `seller/store` (GET/POST/
PATCH) · `seller/store/cover` (POST/DELETE) · `seller/products` · `seller/products/<id>` ·
`seller/products/<id>` DELETE (→ `{result: deleted|archived, past_orders}`) · `seller/products/<id>/images` (POST) · `seller/products/<id>/images/order` · `seller/products/<id>/images/<img>`
(DELETE) · `seller/orders` (`?status=`) · `seller/orders/<id>/status` (POST `{status}`) · `seller/reviews` ·
`seller/requests` · `seller/requests/<id>/quote` (POST `{quote_paise, note}`) · `seller/requests/<id>/decline` ·
`requests` (GET mine / POST new, 10 per hour) · `requests/<id>` · `requests/<id>/images` (≤3, while open) ·
`requests/<id>/accept` · `requests/<id>/decline` · `requests/<id>/add-to-bag` · `reviews` (POST `{seller, rating, comment}`) ·
`seller/ai/listing` (GET `{enabled}` / POST photo `image` or `image_id` + `name` → `{title, description, category}`, 10/hour)

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
- **Address rules** (`accounts/address_rules.py`, mirrored in `frontend/lib/address-rules.ts`): pincode = 6 digits
  starting 1–9; phone = Indian mobile, 10 digits starting 6–9 (typed "+91 98765 43210" / "098765-43210" is accepted
  and saved as `9876543210`; all-same digits refused); name 2+ letters; address line and city 3+ letters (any
  script, so "बेंगलुरु" counts; only symbols or digits is refused); line 2 optional but not only symbols. Each
  broken rule has its own message under its field (shown when leaving the field and on Save).
- **Old addresses** saved before the rules aren't changed: every address in the API carries `problems`
  ({} = fine). Checkout shows "Please update this address (mobile number, pincode)" with **Update address**
  (`PATCH addresses/<id>`) and won't continue until it's fixed, and `POST checkout` refuses such an address
  (400 `address_problems`) before creating any order or holding stock.
- **Razorpay contact** is always the delivery address's phone, sent as `+91XXXXXXXXXX` (Razorpay's format), with
  the account email and the address name, so Razorpay doesn't ask for contact details. Never the profile phone.
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
- **Shopping vs selling.** The shopping header (every page except /seller) has only buying links plus one small
  outlined pill: "Switch to selling" (has a shop) or "Sell on HomeHaat". The account button opens `AccountMenu`:
  BUYING (My orders · Wishlist · My custom requests · Saved addresses), SELLING · shop name (Seller dashboard ·
  Shop orders with the open-orders badge · Products · View my shop page), Sign out. It's a disclosure (button +
  links), not an ARIA menu: Escape and outside clicks close it, and focus returns to the button. On /seller pages
  `SellerBar` (black `bg-ink`, white SELLING pill, shop name, ← Back to shopping, View my shop page from 1024px,
  account) replaces the header; phones stack it (row 1 pill + name + account, row 2 back link). Labels are always
  "Selling · …" / "Buying · …", and the seller's tab is "Shop orders", so it can't be confused with "My orders".
  `/auth/me` carries `shop_name` and `open_orders` for the menu and tabs (refreshed after a status change).
- **Pause = "Taking orders" off** (`Seller.is_active=False`), now a `role="switch"` on the Overview (moved from Store
  settings). Changed in this step so the copy is true ("Buyers can still see your shop"): a paused shop's page and
  its product pages still open (`all_stores`, `shop_products`), with "Not taking orders right now" and Add to bag /
  the card's + disabled; the cart API refuses with "This maker isn't taking orders right now"; checkout refuses that
  seller as before. A paused shop is left out of the Makers list, search, home sections and counts.
- **Out of stock / Back in stock** are just `stock` edits (PATCH): stock 0 → buyers see "Sold out", Add to bag is
  refused and bag lines are flagged `sold_out` at checkout. Back in stock asks "How many can you make?" (1+).
- **Delete a product** (`DELETE seller/products/<id>`): never in a paid or pending order → deleted completely, with
  its photo files. In past orders → **archived** (`Product.is_archived=True` and `is_active=False`, an additive
  field, migration `catalog.0003`): gone from the shop, search and the seller's list, can't be edited back
  (404), still shown in those orders (they keep their snapshot), and it is **removed from every bag** (it can never
  be bought again; migration `cart.0002` cleaned up products archived before this fix). Guest bags drop it too. `past_orders` on each seller product feeds the confirmation text. Failed attempts don't count.
- **Owner only:** every product/order change goes through `my_products(user)` / `user.seller`, so another seller
  gets 404 and a buyer 403 (`catalog/tests/test_product_controls.py`).
- **Reviews**: one per buyer per maker (the existing unique constraint), so writing again **edits** it; allowed only
  after a delivered, paid seller order from that maker; not for your own shop. Buyers see "Write a review" on the
  delivered block of their order page. Shown with first name only. Sellers can't edit or remove reviews. Each block
  of a buyer's order carries `can_review` / `my_review` (the buyer's reviews are loaded in one query per request).
- **Search** uses Postgres full-text search (`django.contrib.postgres.search`, part of Django and Postgres, nothing
  to install) together with the old "part of a word" match, and also searches the maker's area.
- **"Did you mean"** uses Python's own `difflib` against words from live product names, categories and shop names
  (first 3,000 products). Only offered when nothing matched and the suggestion really has results with the same
  filters. Stage 7 can move this to Postgres `pg_trgm` if the catalogue grows.
- **Price range check** (`priceRangeError` in `lib/explore.ts`): Explore refuses min above max and non-numbers
  with a message under the boxes instead of applying a filter that can't match anything.
- **Pages**: Explore shows 24 per page with the real total (`/api/search/`); `/api/products/` keeps its old shape
  (home page, store page, wishlist). Every sort ends with `-id`, so pages never overlap or skip.
- **AI listing helper**: Gemini `gemini-flash-lite-latest`, then `gemini-flash-latest` (`settings.GEMINI_MODELS`; `GEMINI_MODEL`
  puts a model first) through its REST API with `requests`
  (already installed). Key sent in the `x-goog-api-key` header, never the URL. The photo goes through `clean_image`
  first (EXIF/GPS removed). Off unless `AI_ENABLED=true` **and** a key is set; the button is hidden otherwise
  (`GET seller/ai/listing`). 10 per hour per seller (DRF throttle `ai_listing`). It never saves anything. Setup:
  `docs/ai-setup.md`. Custom request photos are never sent to AI.
- **Gemini models and errors** (`ai/gemini_client.py`): Google closed `gemini-2.5-flash` to new keys (404) and full
  Flash is often overloaded (503) or slow, so models are tried in order: a 404/429/5xx/timeout moves to the next
  (15 s read timeout, 30 s in total); a 400/401/403 (key or request problem) stops at once. Flash-Lite is first: it
  answers in ~2 s and a short photo description is an easy task. Every failure is logged as `AI: <model>: <status>:
  <Google's message>` with the key removed. Google refusing a photo (`promptFeedback.blockReason`, or a
  `finishReason` like `SAFETY`/`IMAGE_SAFETY`/`PROHIBITED_CONTENT`) → 422 "AI couldn't describe this photo. Try a
  plain photo of your product." (not retried on another model); all models busy → 503 "The AI helper is busy right
  now…". New `AQ.` keys work the same as `AIza` keys (header `x-goog-api-key`).
- The AI suggestion is shown in a panel first; **Use this** fills name, description and category (never price or
  stock) and focuses the name, so the seller edits before saving.
- Throttle counts live in Django's default cache (in memory, per server process): fine for one server; noted for
  deploy.
- **Overview "earnings this week"** = paid in the last 7 days, items + delivery, cancelled parts excluded.
- **Test copy media**: `MEDIA_ROOT` can be set by env; the throwaway e2e copy uses its own folder, so it never
  touches real uploads.
- **Wishlist is kept in the browser** (localStorage, `lib/wishlist.ts`), not in the database: there's no wishlist
  model in PROMPT.md §6, and adding one would be a model change. The page says "saved in this browser". Easy to move
  to the server later.
- **Trending** = products with paid, not-cancelled orders in the last 30 days, most sold first; no orders → the
  section is hidden. **Fresh this week** is only called that if a listing really is from the last 7 days;
  otherwise the heading says "Newest finds".
- **Search** (`catalog/browse.py`): every word must match name, description, shop name or category; name matches
  come first. Unknown filter values in the URL are ignored (no errors). Up to 60 results.
- **Rating** (stores, sort) is the average of real reviews; `null` / "No reviews yet" when there are none, and
  unrated products sort last.
- **Optimistic UI** only for bag quantities (`withQty`) and the wishlist, as PROMPT.md §3 says. Never for payments.
- Category list needs an explicit `order_by("position")`: Django ignores `Meta.ordering` in counting (GROUP BY)
  queries.
- `<main>` has `min-w-0`: without it, a sideways-scrolling row (the category chips) made the whole page wider on phones.
- Unsplash photos go through `next/image`; seller uploads use `<img>` until Stage 7 adds resized copies.
- Every page has one `<h1>` (EmptyState takes `asPageTitle` when it is the whole page).
- **Header:** the 88px single row from UI-UX.md only from **1200px** (`wide:` breakpoint, `--breakpoint-wide`
  in globals.css): it needs ~1,000px of room, so at 900–1199px it pushed the account button off the screen. Below
  1200px: compact two rows: row 1 = logo, (search from 400px), wishlist, bag, account button; row 2 = the links plus
  Sell/My shop in one sideways-scrolling row (92px tall at 320px). Long names are always shortened with "…".
  Tested signed out and as a seller with a long name at 320, 375, 768, 900, 1024, 1100, 1150, 1199, 1200, 1280, 1440.
- **Use named breakpoints** (`sm`, `md`, `wide`…) when a rule must beat another breakpoint: Tailwind puts arbitrary
  ones like `min-[1200px]:` before `sm:`, so `sm:h-16` silently won over `min-[1200px]:h-[88px]`.
- **Store cover** uses `object-position: center 35%` (wide, short strip: keeps more of the subject than centre).
- **Nothing wider than the screen:** layouts are built to fit (checked at 320, 375, 768), and `html, body
  { overflow-x: clip }` is a safety net so a page can never scroll sideways. Scrolling rows use `.no-scrollbar`
  (Windows scrollbars added ~17px of height).
- **Images never show a broken icon:** use `SafeImage` (next/image, Unsplash) or `SafeImg` (seller uploads) from
  `components/SafeImage.tsx`, never `<Image>`/`<img>` directly. On failure they disappear, showing the tint behind
  (or a `fallback`, e.g. the category drawing). A ref check also catches images that failed before React started.
- **Accepted quote → a private one-off product** (`Product.is_custom=True`, price = quote, stock 1, linked as
  `CustomRequest.product`) in the buyer's bag, so bag, stock hold, checkout, payment and seller orders work
  unchanged. `is_custom` products are excluded everywhere products are listed or counted (`browse.public_products`,
  store counts, category counts, the seller's product list, Overview "products listed", product photo endpoints).
  New fields `Product.is_custom` and `CustomRequest.product` / `responded_at` are additive (nothing earlier breaks).
- **Custom item picture**: on accept, the buyer's first reference photo becomes the one-off product's photo
  (`use_reference_photo`: a `ProductImage` pointing at the same cleaned file, no copy). So the bag, checkout and
  orders show it, and only that buyer and that seller can ever see it (the product is private; order endpoints are
  buyer/seller-only). No reference photo → no picture → the category line drawing. Migration
  `custom_requests.0003` filled this in for requests accepted earlier.
- **Item thumbnails** (`components/ItemThumb.tsx`) in the checkout review, the buyer's order page and the seller's
  order cards. Order items now carry `image`, `tint` and `art` (prefetched, no extra queries per item).
- **Request rules**: description 20+ characters, needed-by today or later, budget optional; not to your own shop or a
  paused one; up to 3 reference photos (same cleaning as product photos, no EXIF/GPS), only while open; the seller
  sees the buyer's first name only.
- Known limit: request photos are served from `/media/requests/` like product photos (unguessable file names, but
  not access-checked); Stage 7 can move them behind a signed URL if needed.
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

### 9a. Filters in the URL, and optimistic updates (Stage 4)

**Filters in the URL:** Explore keeps everything in the address (`/explore?q=cake&category=cakes&sort=price_asc`).
`readFilters` turns the URL into an object, `filtersToQuery` turns it back (leaving out defaults), and `filtersToApi`
turns it into the API query (rupees → paise). The page is rendered on the server from the URL, so a search can be
shared, bookmarked, and survives the back button. Typing waits 350 ms before searching, so we don't send one
request per key press.

**Optimistic updates:** when a buyer presses + in the bag, `withQty` immediately computes the new line total, seller
subtotal and grand total (integer paise) and shows them; the server's answer replaces them a moment later, or the
old bag comes back if the server refuses. The wishlist is in the browser, so it's instant anyway. Payments are
never optimistic: the order is paid only when the server says so.

> *Say it:* "Explore's filters live in the URL, so results are shareable and the server renders them. Bag
> quantities update optimistically and are reconciled with the server's response; payments never are."

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

### 11. Custom requests — `backend/custom_requests/services.py` [KEY LOGIC]

**The rules are one table**, `RULES`: (current status, action) → (who may do it, new status).

| From | Action | Who | To |
|---|---|---|---|
| open | quote | seller | quoted |
| open | decline | seller | declined |
| quoted | accept | buyer | accepted |
| quoted | decline | buyer | declined |

**`apply_action(request, user, action, quote_paise, note)` step by step:**
1. Lock the request row (`select_for_update`), so a double tap, or buyer and seller at the same moment, run one
   after the other.
2. **Who are you?** The request's buyer → "buyer"; the shop's owner → "seller"; anyone else →
   `NotYourRequestError` (the API answers 404, like a missing request).
3. **Is the move in the table, and is it your move?** If not → `RequestError` with a sentence people can read
   ("Only the buyer can accept a quote."). Accepted and declined have no rows, so they're final.
4. **quote:** the price must be at least ₹1 (integer paise); it's saved with the note.
   **accept:** the shop must be open; then `_make_one_off_product` creates a private product: name "Custom: …",
   **price = the saved quote** (never a number from the request), stock 1, `is_custom=True`, and a `CartItem` for the
   buyer linked to the request.
5. Save the new status and `responded_at`.

`add_quote_to_bag` puts an accepted request back in the bag if the buyer removed it: `get_or_create`, so never a
second line, and refused once it's bought (stock 0).

**Why it's safe:** one table of allowed moves; who-may-act checked before anything else; the price comes from the
database; the private product can't be found or bought by anyone else (tests check the product page, search, the
shop page, another buyer's bag, and the seller's product list). From there it's an ordinary item, so the 15-minute
stock hold, payment checks and seller order flow all apply unchanged.

> *Say it:* "Custom requests follow a small state table: the seller quotes or declines, then the buyer accepts or
> declines. Accepting creates a private one-off product at the quoted price and puts it in the buyer's bag, so it
> goes through the same checkout, stock and payment code as everything else."

### 12. Reviews — `write_review(user, seller, rating, comment)` in `backend/reviews/services.py` [KEY LOGIC]

**What it does:** saves a buyer's 1–5 star review of a maker, but only if they really received something from them.

**Step by step:**
1. Your own shop → refused ("You can't review your own shop.").
2. The rating must be a whole number from 1 to 5. `True` is refused too: in Python `True == 1`, so we check for it.
3. The comment is trimmed and at most 1,000 characters.
4. **The rule:** `has_delivered_order` looks for a `SellerOrder` from *this* seller, in an order *this* buyer paid
   for, whose status is `delivered`. Not paid, still preparing, out for delivery, cancelled, or delivered by another
   maker → refused with "You can review a maker once one of their orders has been delivered to you."
5. `update_or_create(seller, buyer)`: the database allows one review per buyer per maker, so a second review
   edits the first instead of adding another (nobody can stuff the average).

**Why it's safe:** the buyer is always `request.user` (a test sends `buyer: <someone else>` and proves it's
ignored); the delivered check runs on the server even though the page also hides the button; and the average shown
everywhere is computed from the reviews table (`Avg("rating")`).

> *Say it:* "A buyer can review a maker only after one of that maker's orders was delivered to them. The server
> checks that with one query, keeps one review per buyer per maker so a second one edits the first, and the
> average is always computed from the table."

### 13. Full search — `find_products` / `search_page` in `backend/catalog/browse.py`

- **Matching:** every word must match. A word matches if it's *part of* the name, description, shop name, area or
  category (`icontains`, so "choco" finds chocolate), **or** Postgres full-text search says it's the same word
  (`SearchVector` + `SearchQuery` with the `english` config, which reduces words to their stem: "cakes" → "cake",
  "pickles" → "pickl").
- **Ranking ("Best match"):** first, how many search words are in the product *name*; then `SearchRank` with
  weights (name A, shop and category B, description and area C); then newest.
- **Pages:** `count()` gives the real total, `pages` is rounded up, and a bad or too-big `?page=` becomes a page
  that exists. The frontend keeps `page` in the URL (`lib/explore.ts`), and any filter change goes back to page 1.
- **Did you mean:** if nothing matched, `suggest_query` swaps each unknown word for the closest real word from the
  listings (`difflib.get_close_matches`, 75% similar), and we only show it if that search has results.

> *Say it:* "Search combines substring matching with Postgres full-text search, so partial words and plurals both
> work. It ranks name matches first, pages with a real total, and suggests a spelling fix only when that fix has
> results."

### 14. The AI listing helper — `backend/ai/listing.py` [KEY LOGIC]

**What it does:** from the seller's first photo, Gemini suggests a title, a description and a category. The seller
sees it in a panel and chooses **Use this** or **Dismiss**. The AI saves nothing.

**Step by step (`POST /api/seller/ai/listing/`):**
1. Sellers only; AI must be switched on with a key (otherwise 503 with the plain message); 10 per hour per seller.
2. The photo is either a new upload (checked and cleaned by `clean_image`, so no GPS location goes to Google) or the
   `image_id` of a photo on *one of my own* products (another seller's photo → 404).
3. `write_listing` builds the prompt (describe only what's visible; no price, size, ingredients or materials) and a
   **JSON schema** with exactly three fields: `title`, `description`, `category` (an `enum` of our category slugs).
   There is no price field, so the model has nowhere to put one.
4. `gemini_client.generate_json` sends it (key in a header) to each model in `GEMINI_MODELS` until one answers:
   retired, busy, over its limit or too slow → next model; Google refusing the photo → `GeminiBlocked` (the seller is
   told to try a plain photo); anything else, or not JSON → `GeminiError`.
5. **`validate_listing` never trusts the answer:**
   - it must be an object with text `title` and `description`, or it's refused;
   - emoji and hashtags are removed; prices are cut out of the title;
   - the description is split into sentences, and a sentence is **dropped** if it mentions a price (₹, Rs, INR,
     price, cost) or a link, a size/weight/quantity ("1 kg", "serves 10"), or an ingredient/material claim ("made
     with…", "silk", "eggless"), **unless the seller wrote those words themselves** in the product name (so "1 kg"
     stays for "Chocolate cake (1 kg)");
   - text is cut to 80 / 1,000 characters at a word or sentence; an unknown category becomes `null`.
6. Any failure → 503 with "Couldn't write a listing, please fill it in yourself." The form works as before.

**Why it's safe:** the rules are enforced three times (prompt, schema, our own validation); the AI can't save
anything; the key never reaches the browser; and the whole feature switches off with `AI_ENABLED=false`. Tests fake
Gemini (`mock.patch`), so they never call the internet.

> *Say it:* "The AI helper asks Gemini for strict JSON with a schema that has no price field, then validates the
> answer itself: the wrong shape is rejected, and any sentence with a price, a size or an ingredient claim the seller
> didn't write is removed. The seller always reviews it, and the app works fully with AI switched off."

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

### Stage 4
1. **Why put search filters in the URL?** So a search can be shared, bookmarked and kept on back/forward, and the
   server can render the results directly. One pair of functions converts URL ↔ filters, and it's unit-tested.
2. **What is optimistic UI and where do you use it?** Showing the expected result before the server answers, then
   reconciling. HomeHaat uses it only for bag quantities and the wishlist (cheap to undo), never for payments.
3. **How do you avoid showing made-up numbers on a new marketplace?** Every count, rating and "trending" list is
   computed from the database; sections with no data are hidden or show a designed empty state, ratings show
   "No reviews yet", and "Fresh this week" is only used when a listing really is from this week.

### Stage 5
1. **How do you model a workflow like quote → accept?** With a table of allowed transitions (status + action →
   who may do it + next status) checked in one locked function, so every rule lives in one place and anything else
   is refused. Tests try each wrong side and each wrong step.
2. **How does an accepted quote get paid for without a special checkout?** Accepting creates a private one-off
   product priced at the quote, with stock 1, and adds it to the buyer's bag. Checkout, the stock hold and payment
   then work exactly as for any product, and the product is hidden from everyone else.
3. **How do you stop a buyer changing the price when accepting?** The accept endpoint reads nothing from the body:
   the price comes from the quote saved by the seller. A test sends `quote_paise: 100` with the accept and checks
   the bag still has the real quote.

### Stage 6
1. **How do you make sure reviews are real?** A buyer can review a maker only after one of that maker's orders was
   delivered to them, checked on the server; the buyer is always the signed-in user, and there's one review per
   buyer per maker, so a second review edits the first. The average is computed from the table.
2. **How does your search handle plurals and typos?** Postgres full-text search stems words ("cakes" → "cake")
   alongside substring matching for partial words, results are ranked with name matches first, and when nothing
   matches, `difflib` suggests the closest real word, shown only if it has results.
3. **How do you stop an AI from inventing facts in a listing?** Three layers: the prompt says not to, the JSON schema
   has no price field, and `validate_listing` drops any sentence with a price, size or ingredient/material claim the
   seller didn't write. The seller reviews the suggestion before anything is saved, and the app works with AI off.

## QA log

- **13 Oct 2026, full checklist (sections 1–9) on a throwaway copy:** two items failed and were fixed with tests:
  2.5 (min > max wasn't refused) and 5.8 (an archived product stayed in other buyers' bags). The real Gemini
  suggestion couldn't be tested (Google busy on both models for both tries); everything else passed. Section 10
  items confirmed still pending. Likely cause of 10.2 (art shop showing a cake cover): Open your shop defaults
  "Main category" to the first category (Cakes), so a shop that doesn't change it gets the cake photo.

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
- **Stage 4**: search/filter/sort API (`browse.py`) with trending from real orders; public stores and reviews; full
  home page, Explore, Categories, Makers, store page (tabs, share), product gallery, wishlist (browser), header and
  footer per UI-UX; product card with heart and quick +; optimistic bag quantities; phone/tablet/desktop audit of
  every page (no sideways scroll, alt text, labels, one h1).
- **Stage 5**: custom requests: buyer form with up to 3 photos, needed-by and budget; seller Send quote / Decline;
  buyer Accept and add to bag / Decline / Add to bag again; accept creates a private one-off product at the quoted
  price that goes through normal checkout; rules in one table (`apply_action`); rate limit 10 requests/hour;
  Overview nudge for open requests.
- **Stage 6**: reviews after delivery (`write_review`, one per buyer per maker, editable) on the order page, store
  page and seller dashboard; full search (Postgres full-text + substring, area, ranking, 24 per page with real totals,
  "Did you mean"); AI listing helper (Gemini free tier, strict schema, `validate_listing`, 10/hour, off by default,
  `docs/ai-setup.md`); seller guide updated.
- **After Stage 6**: stricter Indian address checks + Razorpay contact prefill; Gemini model fallback; shopping vs
  selling separation (account menu, black seller bar, "Selling · …" labels), Taking orders switch (paused shops stay
  visible), product controls (out of stock / back in stock / delete or archive).
