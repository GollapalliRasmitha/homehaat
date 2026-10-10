# HOMEHAAT — Build Brief for Claude Code

You are the lead engineer, product designer and **teacher** for **HomeHaat**, a multi-seller marketplace for home businesses: home bakers, artists, tailors, pickle makers and crafters. Buyers browse sellers near them, add products from **several sellers to one cart**, and **pay once**. The order is split per seller, and each seller prepares, delivers and updates their own part. Buyers can also send a **custom request** ("photo cake for Saturday", "blouse in this design") and the seller replies with a quote.

The result must look and feel like a real product: **warm, local, trustworthy e-commerce**, good enough for a portfolio, interviews, and a few real sellers using it.

I'm Rasmitha, a student. I built my first project, Oppora, with you. For HomeHaat I want to **understand and explain every important line**, so this brief works differently from Oppora's. Read Section 0 carefully.

---

## 0. How we work (read this first)

1. **Risky part first.** The hard part of HomeHaat is money: cart, order split, payment, stock and order status. We build one thin path that works end to end (real database, real test payment) **before** any polish. Each later stage widens it.
2. **8 stages, in the order in Section 10.** At the end of each stage:
   - run lint, type-check and tests, and fix any failures
   - confirm earlier features still work
   - commit with a message like `stage-2: multi-seller order split`
   - post a short summary: what was built, what you assumed, what's left, and **3 interview questions about this stage with short answers**
   - **stop and wait for me to say "continue"**.
3. **Explain mode for the core (you write all the code).** I don't write code. Some functions are marked **[KEY LOGIC]** in Section 10. For those:
   - write the tests first, then the implementation
   - after the stage, explain each one in plain English: what it does, step by step, why it is safe, and which Django features it uses (for example `transaction.atomic`, `select_for_update`, `F()` expressions)
   - add that explanation to the **"How it works"** section of `CLAUDE.md`, plus a simple example I can say out loud in an interview
   - keep the code short and readable, with clear names and comments on the tricky lines, so I can read it and follow along.
   Everything else, build as usual.
4. **Tests before money code.** Every payment, order or stock feature gets its tests written first.
5. **Keep `CLAUDE.md` up to date:** design tokens, components, folder structure, decisions, the current stage and a **"How it works"** section in simple words that I can read before interviews.
6. **One product, one design system.** Every page uses the shared tokens and components. Don't restyle a component for one page.
7. **Ask me before you** add a paid service, add a new tool or service to the setup, change a design token, change the data model in a way that breaks earlier stages, or switch payments out of test mode.
8. **Never invent facts** in UI copy or AI output. Prices, ratings and stats are always computed from data. Unknown values show as "Not provided by seller".
9. **Money is always integer paise** (₹450 = `45000`) in the database, API and frontend. Format for display in one shared helper (`formatINR`). Never use floats for money.
10. **Visual reference:** files in `design/`. Match their atmosphere, but don't copy them literally.

---

## 1. Tech stack (kept simple on purpose, all free)

| Layer | Choice |
|---|---|
| Frontend | Next.js (App Router) + TypeScript + Tailwind CSS + Radix + Lucide icons + Sonner toasts |
| Backend | Django + Django REST Framework + django-filter |
| Database | PostgreSQL (one Docker container locally; Neon in production) |
| Payments | **Razorpay Test Mode only** (Orders API + Checkout.js + signed webhook) |
| Images | Local `MEDIA_ROOT` in development; Cloudinary free tier in production, behind one storage setting |
| AI | Gemini REST API (free tier), for one feature only: the listing helper |
| Email | Django console email backend (no paid provider) |
| Deploy | Vercel (frontend) + Render (API) + Neon (Postgres) |

**Local ports:** HomeHaat's Postgres container runs on port **5433** so it doesn't clash with Oppora's (5432). Close Oppora's local windows before starting HomeHaat, since both use ports 3000 and 8000.

**Gemini key:** HomeHaat uses its **own** `GEMINI_API_KEY`, never Oppora's, so one project can't use up the other's free daily limit.

**No Redis, no Celery, no background workers.** HomeHaat doesn't need them. The one scheduled job (expiring unpaid orders) is a management command run by a free GitHub Actions schedule in production and by hand locally.

**Local setup must stay small:** Docker Desktop (Postgres only), Node LTS, Python. One `start-homehaat.ps1` that checks these, creates `.env` from `.env.example`, installs packages, runs migrations and `seed_categories`, and opens **two** windows: Django on port 8000 and Next.js on port 3000.

**Repo layout:** a monorepo with `/frontend`, `/backend`, `/design`, `/docs`, `docker-compose.yml`, `start-homehaat.ps1`, `CLAUDE.md`.

**Data layer rule:** components never call `fetch` directly. All data goes through typed service functions in `frontend/lib/api/*` that call the real Django API from Stage 1 onwards. Next.js proxies `/api/*` to Django so the session cookie is first-party.

---

## 2. Design system

**The full UI/UX brief is in `UI-UX.md` in the repo root. Read it before Stage 1 and follow it for every screen.** It replaces any earlier design notes.

In short: editorial and minimal, like the reference `design/HomeHaat-demo-empty.html`. A white page, black ink, Inter Tight with one Instrument Serif italic accent per heading ("Made at home. *Made for you.*"), a centred pill search bar, black pill buttons, soft neutral cards and real photos (Unsplash for categories; sellers' own uploads for products). No gradients, glassmorphism, emoji or 3D illustrations.

Use its tokens and fonts from Stage 1 (pages can stay plain until then). Apply it fully in Stage 4. Reference screens are in `design/`.

---

## 3. Definition of done for every page (from Stage 4 onwards)

Follow Sections 6–10 of `UI-UX.md`: phone first, loading/empty/error/no-results states, keyboard and screen-reader friendly, 4.5:1 contrast, a toast after every action, optimistic UI for bag quantities and the wishlist only, never for payments.

---

## 4. Real data only (no sample data)

HomeHaat shows **only real data** created by real users. There is **no `seed_demo`**, and no sample sellers, products, reviews, orders or numbers anywhere in the app, in development or production.

- The only thing seeded is the fixed list of **categories** (`python manage.py seed_categories`, safe to run again): Cakes & bakes, Homemade pickles, Homemade snacks, Art & paintings, Tailoring, Crafts & gifts, Jewellery, Home décor.
- A brand-new site is **empty by design**: every page needs a designed empty state (see `UI-UX.md`, Section 6) that explains what will appear and what to do next, for example "No makers yet. Be the first to open your shop." with an **Open your shop** button.
- To try the app locally, I sign up as a buyer and as a seller myself and add real products through the seller dashboard. Tests use factories inside the test suite only; nothing from tests appears in the running site.
- Product images are the seller's uploaded photos. Until a product has a photo, show the category's 3D-style illustration on its category colour. Never stock photos.
- Every number in the UI (counts, totals, "Popular this week", ratings, stats) is computed from the database. When there's no data, show nothing or "—", never a made-up number.
- `design/HomeHaat-demo-empty.html` is the reference. It starts empty and has no sample data. Copy its look and flows, never seed anything from it.

---

## 5. Pages and features

### Buyer
- **Home:** follow `UI-UX.md` Section 5 and the reference demo: centred hero (eyebrow "Handmade by people near you", "Made at home. *Made for you.*", subtitle, pill search with a black **Search** button) · 3 photo showcase cards · "Browse by *category*" photo tiles · "Trending *nearby*" (computed from real order counts, hidden until there are orders) · "Fresh *this week*" (newest real listings) · black custom-order banner · "Makers *near you*" · footer. With no data yet, sections show their empty states instead.
- **Search & category:** products and sellers; filters for category, price range and in stock only; sort by relevance, price, newest, rating. Filters live in the URL.
- **Store page `/store/[slug]`:** cover, monogram avatar, name, bio, rating and count, kind, area, delivery badge, **Request a custom order**, **Share**; product tabs by category; Reviews tab.
- **Product page `/product/[id]`:** gallery (up to 5 images), price, stock ("Only N left" at ≤ 3, "Sold out" at 0), description, delivery info, quantity, optional note to the seller, **Add to cart**, "More from this seller".
- **Cart `/cart`:** grouped by seller, each group with delivery badge, items, quantity, remove, subtotal and delivery fee; summary with total and **Checkout**; the line "One payment. HomeHaat splits it into N seller orders." Guest carts live in the browser and merge into the server cart on sign-in.
- **Checkout `/checkout`:** address (pick or add; 6-digit pincode validated) → review → **Pay ₹<total>** with a "Test mode, no real money" badge → "Confirming payment…" screen that polls the order → success page listing the seller orders, or failure page with **Try again** ("Your payment didn't go through. You haven't been charged.").
- **Orders `/orders`, `/orders/[id]`:** one block per seller order with an OrderTimeline (New → Preparing → Out for delivery → Delivered), items, and **Write a review** once delivered.
- **Custom requests `/requests`:** form (description, up to 3 photos, needed-by date, optional budget); statuses Open → Quoted (price + note, **Accept** / **Decline**) → Accepted. Accepting adds a cart item at the quoted price, linked to the request.
- **Account:** sign up and sign in with email + password, profile (name, phone), saved addresses, delete my account, sign out.

### Seller
- **Open your shop `/sell`:** name, slug (auto, editable, unique), kind, area, bio, cover, delivery days and fee. Creating a store makes the user a seller.
- **Dashboard `/seller`** (SellerShell: Overview, Orders, Products, Custom requests, Reviews, Store settings):
  - Overview: greeting · StatCards (earnings this week, open orders, products listed, rating, all computed) · incoming orders.
  - Orders: table with status filter; tapping a status moves it to the next step; **Cancel** asks for confirmation.
  - Products: list with stock and an active toggle; add/edit form with up to 5 photos (drag-and-drop, reorder, compressed in the browser) and **Write listing with AI**.
  - Custom requests: **Send quote** / **Decline**. Reviews: read-only with the average. Store settings: everything from onboarding plus **Pause store**.

### AI listing helper (Gemini free tier)
- After a photo is uploaded, **Write listing with AI** suggests a title, description and category. The seller edits before saving. Strict JSON schema, validated.
- **Never suggest a price. Never invent ingredients, sizes or materials.** On failure or a used-up free limit: "Couldn't write a listing, please fill it in yourself." Rate-limited per seller; the app works fully with `AI_ENABLED=false`.

### Empty states
Empty cart: "Your cart is empty." → **Browse sellers**. Matching empty states for orders, requests, seller orders, seller products ("Add your first product"), reviews and search. Out of stock at checkout: "Some items sold out while you were shopping." Show which ones and let the buyer remove them.

---

## 6. Data model (Django)

**Apps:** `accounts`, `catalog`, `cart`, `orders`, `payments`, `reviews`, `custom_requests`, `ai`, `core`.

- `User` (custom, email login) with `role` buyer / seller / admin and `phone`. Users can never change their own role through the API.
- `Address` (user, label, name, phone, line1, line2, city, pincode).
- `Seller` (owner one-to-one, unique slug, name, kind, bio, area, cover, delivery_days, delivery_fee_paise, is_active).
- `Category`; `Product` (seller, category, name, description, price_paise, stock, is_active, created_at); `ProductImage` (product, image, position).
- `CartItem` (user, product, qty 1–50, note, optional custom_request).
- **`Order`**: one per checkout (buyer, items_total, delivery_total, grand_total, payment_status pending/paid/failed/refunded, razorpay_order_id unique, razorpay_payment_id unique, ship_to JSON snapshot, created_at, paid_at).
- **`SellerOrder`**: each seller's share (order, seller, subtotal, delivery_fee, status new/preparing/out_for_delivery/delivered/cancelled, a timestamp per status; unique order + seller).
- **`OrderItem`** (seller_order, product nullable, **name and unit_price snapshotted**, qty, note).
- `Review` (seller, buyer, rating 1–5, comment; unique seller + buyer; only after a delivered seller order).
- `CustomRequest` (buyer, seller, description, images, needed_by, budget_paise, quote_paise, seller_note, status open/quoted/accepted/declined).
- Indexes on every field used for filtering or joins.

**Allowed status moves** (enforced on the server): new → preparing → out_for_delivery → delivered; new or preparing → cancelled. Anything else is rejected.

---

## 7. Checkout and payments (the core of the project)

```
Cart ─► POST /api/checkout/ ─► Order + SellerOrders + OrderItems (pending) ─► Razorpay order
     ─► Razorpay Checkout in the browser ─► webhook (payment.captured)
     ─► verify signature + amount ─► mark paid, reduce stock, clear cart ─► seller dashboards
```

- **Prices come from the database, never from the request.** Checkout reads the server cart, checks stock and active status, and computes every total itself.
- Create the Order, one SellerOrder per seller and the OrderItems **in one `transaction.atomic()` block**, with `select_for_update()` on the products so two buyers can't buy the last item at once.
- **An order becomes paid only in the webhook**, after verifying `X-Razorpay-Signature` (HMAC-SHA256 with the webhook secret, constant-time compare) **and** that the captured amount equals `grand_total`. The browser callback only shows "Confirming payment…".
- **The webhook is idempotent:** if the order is already paid, do nothing. Stock is reduced and the cart cleared only once.
- **Local development:** Razorpay cannot send webhooks to `localhost`. `start-homehaat.ps1` starts a free Cloudflare quick tunnel (`cloudflared`, no account needed) and prints the public webhook URL to paste into the Razorpay test dashboard. As a local backup, also verify the Checkout handler's `razorpay_signature` (HMAC-SHA256 of `order_id|payment_id` with the key secret, constant-time compare) on `POST /api/payments/verify/`, which marks the order paid through the **same idempotent `mark_order_paid()`** and the same amount check. The webhook stays the source of truth in production.
- Unpaid orders older than 30 minutes become `failed` (`python manage.py expire_orders`).
- Cancelling a paid seller order records "refund needed" (no live refunds in test mode).

**Required tests:** happy path with Razorpay faked; bad signature rejected; amount mismatch rejected; repeated webhook doesn't reduce stock twice; a price sent in the request body is ignored; two buyers racing for the last item give one order and one "sold out" error; the cart from 3 sellers creates exactly 3 seller orders with correct subtotals and delivery fees.

---

## 8. Permissions (tested)

Every non-public endpoint needs sign-in, and every queryset is filtered by the user. Tests must prove:
- buyer A can't read or change buyer B's cart, addresses or orders;
- seller A can't read seller B's orders or edit seller B's products;
- a seller can change only the **status** of their own seller orders, never the amounts, and only along the allowed moves;
- a buyer can't review a seller without a delivered order;
- nobody can change their own role.

Session auth with secure, httpOnly, SameSite cookies; CSRF on every change. Buyer phone numbers and addresses are visible only to the sellers of that buyer's orders.

---

## 9. Security, images and privacy

- Secrets only in `.env`, never committed, never in the frontend bundle. Razorpay key secret and webhook secret are server-only.
- Rate-limit sign-in, sign-up, checkout, AI listing and custom requests.
- Images go through the API only: JPEG/PNG/WebP, ≤ 5 MB, EXIF location stripped, a resized copy for cards.
- Secure headers (CSP, no framing, nosniff), CORS limited to the frontend origin, `DEBUG=false` in production.
- Delete my account: removes addresses and cart, anonymises past orders.

---

## 10. Build order: 8 stages, one at a time

**Stage 1: Thin path end to end** (plain styling, real data)
Monorepo, Docker Postgres, `start-homehaat.ps1`, Django + Next.js wired through the `/api` proxy, email sign-in, the models in Section 6, `seed_categories`, design tokens and fonts. Pages: a simple product list, product page, a single-seller cart, checkout with one address, real Razorpay test payment, webhook, order success page, and a simple seller page listing paid orders.
- **[KEY LOGIC]** `backend/orders/services.py` → `create_order_from_cart(user, address)` for a **single seller**, and `backend/payments/webhook.py` → signature check + `mark_order_paid(order, payment_id)` (idempotent). Write the tests first, then the code, then explain it.
- Done when I can buy a cake with a Razorpay test card and see the order on the seller page.

**Stage 2: Multi-seller cart and order split**
Cart grouped by seller, guest cart + merge on sign-in, checkout review step, order detail page with one block per seller, out-of-stock handling, `expire_orders`. All tests in Section 7.
- **[KEY LOGIC]** extend `create_order_from_cart` to split into one SellerOrder per seller, with `transaction.atomic()` and `select_for_update()`. Write the race-condition test and explain how it works.

**Stage 3: Seller side**
Open your shop, SellerShell, Overview stats, Orders with status changes, Products with add/edit and photo upload (local storage), Store settings, Pause store. Permission tests in Section 8.
- **[KEY LOGIC]** `backend/orders/status.py` → `advance_status(seller_order, new_status, user)` enforcing the allowed moves and ownership.
- **After this stage I'll ask 2–3 real home sellers to try it.** Add a short `docs/seller-guide.md` (how to open a shop and add products, in simple words, with screenshots) for them.

**Stage 4: Design system and polish**
Build every component in Section 2 and restyle every page built so far. Apply Section 3 to every page on phone, tablet and desktop. Home page in full, search and category pages, store page in full.

**Stage 5: Custom requests**
Buyer form with photos, seller quote and decline, buyer accept and decline, accepted request → cart item at the quoted price → normal checkout.
- **[KEY LOGIC]** the status rules for custom requests and the accept → cart item step.

**Stage 6: Reviews, search and the AI listing helper**
Reviews after delivery with the seller average, full search with filters and sort, the Gemini listing helper with its schema, validation and limits.

**Stage 7: Security, speed and accessibility**
Everything in Section 9, Cloudinary for production images, caching for public pages, query checks (no N+1), Lighthouse 90+ on Home, Store and Product on mobile, keyboard-only and screen-reader checks. Fix what the real sellers reported.

**Stage 8: Deploy and finish**
Deploy to Vercel + Render + Neon with a GitHub Actions schedule for `expire_orders`. Render's free server sleeps after 15 idle minutes: add a lightweight `GET /api/health/` (no database or Redis calls, returns `{"ok":true}`), set up a cron-job.org ping to it every 10 minutes, and make checkout and the "Confirming payment…" screen wait and retry while the server wakes (Razorpay retries webhooks, so none are lost) (`docs/deploy.md`, step by step for Windows). Run the full journey on the live site:
Home → search → store → add items from 3 sellers → sign in (cart merges) → address → pay in test mode → webhook → order split into 3 → seller marks Preparing → Out for delivery → Delivered → buyer reviews → custom request → quote → accept → pay.
Write `README.md`: what HomeHaat is, screenshots, the architecture diagram, setup steps, a 2-minute demo script, and an **"Interview notes"** section that collects the questions and answers from every stage.

**Start now with Stage 1 only. Stop when it's done and summarise.**