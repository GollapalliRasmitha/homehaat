# HomeHaat UI/UX brief

**Reference:** `design/HomeHaat-demo-empty.html`. Open it in Chrome; it starts empty, just like the real site. Copy its look, layout and behaviour. Nothing in it is data to seed.

## 1. Look in one line
Editorial and minimal: a white page, black ink, one italic serif accent, soft neutral cards and real photos. Calm and premium, like a design magazine, not a busy marketplace.

Don't use gradients, glassmorphism, coloured buttons, emoji, 3D illustrations or drop shadows (except the one soft shadow on the hero search bar).

## 2. Design tokens
Put these in `globals.css` as CSS variables and use them everywhere. Don't use raw hex values in components.

| Token | Value | Use |
|---|---|---|
| --ink | #111111 | text, buttons, icons |
| --muted | #5F5F5F | secondary text |
| --line | #EAEAEA | borders, dividers |
| --page | #FFFFFF | page background |
| --soft | #F6F5F2 | empty states, stat cards, maker cards |
| --black-2 | #2B2B2B | button hover |
| --sand #F2EFEA · --mist #EEF0F2 · --linen #F1EEE6 · --sage #EDF0EA · --blush #F5EDEC · --stone #EFEDEA | | category tints, shown behind photos while they load |

**Status pills** (6px dot + label, rounded):

| Status | Background | Text |
|---|---|---|
| New | #FBF0E4 | #8A4B12 |
| Preparing | #F1EEE6 | #5A4A2A |
| Out for delivery | #EDF1F6 | #2D4A73 |
| Delivered | #E9F4EC | #1F6A3B |
| Cancelled | #F1F1F1 | #666666 |

**Errors:** #B42318.

## 3. Typography
- **Inter Tight** (400–800) for everything, loaded with `next/font/google`.
- **Instrument Serif Italic** for the accent word only, for example "Made at home. *Made for you.*", "Fresh *this week*", "Makers *near you*". Use one italic phrase per heading at most.
- Headings are bold with tight letter-spacing (about −0.03em to −0.055em on the hero).
- Eyebrow labels: 13–15px, uppercase, letter-spacing .14em, --muted.
- Prices: weight 600, tabular numbers.

## 4. Components
- **Header:** white with a 1px --line bottom border, about 88px tall.
  - Left: the "homehaat" wordmark (weight 800), then the links Explore · Categories · Makers · Custom orders. Plain text; an underline marks the active page.
  - Right: Sell on HomeHaat (becomes My shop for sellers), then the search, wishlist and bag icons with small black count badges (shown only when the count is above 0), then the outlined "Sign in" pill.
- **Buttons:** fully rounded pills.
  - Primary: black with white text.
  - Secondary: white with a thin border.
  - Large size is 56px tall. On black sections, the primary button turns white.
- **Hero search:** a pill about 82px tall, 1px border, one soft shadow, with a search icon, an input and a black "Search" button inside.
- **Showcase cards:** 3 large photo cards (radius 28px). A white label card sits at the bottom-left and a round white arrow button at the bottom-right.
- **Category tiles:** a square photo (radius 20px) with the category name underneath. The photo zooms slightly on hover.
- **Product card:** no box around it. It has:
  - a square image (radius 22px)
  - a white heart button at the top-right
  - a small white tag at the top-left: "Only 3 left", "Sold out" (black) or the maker's tag
  - below the image: the maker name (--muted), the product name (600 weight), delivery text, then the price with a round black + button
- **Maker card:** --soft background, a round monogram in a dark tone with an italic serif letter, then name, kind, area and product count.
- **Panels/forms:** white with a 1px --line border, radius 24px. Inputs are 50px tall with radius 14px; focus turns the border --ink.
- **Tabs (seller dashboard):** text tabs with a 2px black underline on the active one.
- **Stat cards:** --soft background, a big bold number and a small --muted label.
- **Toast:** black pill at the bottom centre.
- **Footer:** a top border, the wordmark, small --muted links, and "Photos: Unsplash" when stock photos are used.

## 5. Pages
- **Home**, top to bottom:
  1. Hero: eyebrow "HANDMADE BY PEOPLE NEAR YOU", then "Made at home. *Made for you.*", the subtitle and the search pill.
  2. 3 showcase cards: Cakes & bakes, Pickles & snacks, Art & gifts.
  3. "Browse by *category*" with 8 tiles.
  4. "Trending *nearby*": real order counts, hidden until there are orders.
  5. "Fresh *this week*": the newest real listings.
  6. The black custom-order banner with a photo on the right.
  7. "Makers *near you*".
  8. Footer.
- **Explore / category:** title, a search box, a sort dropdown, an "In stock only" chip, category chips, then the product grid.
- **Categories:** all 8 tiles with live product counts.
- **Store:** a cover photo (the seller's upload, or the category photo as a fallback), then monogram, name, kind · area, bio, facts (delivery, products, reviews) and the product grid.
- **Product:** a large square image, maker link, name, price and stock pill, description, quantity stepper, a note to the maker, "Add to bag" and Save, then rows for delivery, fee and payment.
- **Bag:** grouped by maker, each group with its own delivery fee and subtotal. The summary sits on a --soft panel and explains "One payment, split into N orders".
- **Checkout:** 3 steps (Address → Review → Pay), with a 6-digit pincode check and a 10-digit phone check.
- **Orders and order detail:** one status timeline per maker (4 black bars), and a review form once delivered.
- **Custom orders:** a request form (maker, description, date, budget) and a "Your requests" list with quotes to accept or decline.
- **Seller:**
  - Open your shop: name, kind, category, area, fee, delivery text, bio.
  - Dashboard: stats, then the tabs Products · Orders · Custom requests · Shop settings.
  - Product form: photos (up to 5), details, price and stock.

## 6. Empty states (important: the site starts empty)
Every list has a designed empty state: a --soft panel with a round 120px photo, a short heading, one line of help and one action. For example:
- Fresh this week: "Handmade finds will appear here" → Open your shop
- Makers: "No makers yet" → Open your shop
- Bag: "Your bag is empty" → Start exploring
- Orders: "No orders yet"
- Seller products: "Add your first product"
- Seller orders: "No orders yet"

## 7. Photos
- **Category, showcase, banner and empty-state photos:** Unsplash images (free licence), listed in the reference file's `CATS` (`ph` ids). Serve them through `next/image` with `images.unsplash.com` allowed in `next.config`.
- **Product images:** always the seller's own uploads. A product without a photo shows a fine black line drawing of its category on the tint colour, never a stock photo.
- **Store cover:** the seller's upload, falling back to the category photo.

## 8. Behaviour and accessibility
- Hover effects:
  - cards lift 4px
  - photos zoom 4–5%
  - buttons press to 97%
- Everything respects `prefers-reduced-motion`.
- Focus ring: 2px --ink outline with a 3px offset. All icon buttons have aria-labels. Contrast is AA or better.
- Responsive:
  - Showcase goes to 1 column under 900px.
  - The header links wrap below the logo.
  - The 16px side gutter stays and the page never scrolls sideways.
