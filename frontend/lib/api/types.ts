// Shapes returned by the Django API. All money fields are integer paise.

export type Role = "buyer" | "seller" | "admin";

export interface User {
  id: number;
  email: string;
  name: string;
  phone: string;
  role: Role;
  store_slug: string | null;
  shop_name: string | null; // null = no shop yet
  open_orders: number; // paid shop orders still to prepare or deliver (the account menu badge)
}

export interface Category {
  slug: string;
  name: string;
  tint: string;
  art: string;
  photo_id: string;
  product_count?: number; // only from /categories/: live products in it
}

/** A shop as buyers see it. Counts and rating are computed on the server; rating is null until reviewed. */
export interface PublicStore {
  slug: string;
  name: string;
  kind: string;
  kind_label: string;
  area: string;
  bio: string;
  cover: string | null;
  main_category: Category | null;
  delivery_days: number;
  delivery_fee_paise: number;
  product_count: number;
  rating: number | null;
  review_count: number;
  taking_orders: boolean; // false = paused: the page still opens, but nothing can be ordered
}

export interface StoreReview {
  id: number;
  rating: number;
  comment: string;
  buyer_name: string;
  created_at: string;
}

export interface SellerSummary {
  slug: string;
  name: string;
  kind: string;
  kind_label: string;
  area: string;
  delivery_days: number;
  delivery_fee_paise: number;
  taking_orders: boolean; // false = the shop is paused: no Add to bag
}

export interface Product {
  id: number;
  name: string;
  description: string;
  price_paise: number;
  stock: number;
  category: Category;
  seller: SellerSummary;
  image: string | null;
  images: string[];
  created_at: string;
}

/** Why a bag line can't be bought right now. */
export type LineProblem = "sold_out" | "not_enough" | "unavailable" | null;

export interface CartLine {
  id: number | null; // null for a guest's bag (kept in the browser)
  qty: number;
  note: string;
  line_total: number;
  problem: LineProblem;
  product: Product;
}

export interface CartGroup {
  seller: SellerSummary;
  items: CartLine[];
  items_total: number;
  delivery_fee: number;
  subtotal: number;
}

export interface Cart {
  groups: CartGroup[];
  count: number;
  items_total: number;
  delivery_total: number;
  grand_total: number;
  has_problems: boolean;
}

export interface SoldOutItem {
  product_id: number;
  name: string;
}

export interface Address {
  id: number;
  label: string;
  name: string;
  phone: string;
  line1: string;
  line2: string;
  city: string;
  pincode: string;
  problems: Partial<Record<"name" | "phone" | "line1" | "line2" | "city" | "pincode", string>>; // {} = fine
}

export type NewAddress = Omit<Address, "id" | "problems">;

export type PaymentStatus = "pending" | "paid" | "failed" | "refunded";
export type SellerOrderStatus = "new" | "preparing" | "out_for_delivery" | "delivered" | "cancelled";

export interface OrderItem {
  id: number;
  product_id: number | null;
  name: string;
  unit_price: number;
  qty: number;
  note: string;
  line_total: number;
  image: string | null; // the product's first photo (for a custom request: the buyer's reference photo)
  tint: string; // category tint + drawing, shown when there's no photo
  art: string;
}

export interface SellerOrder {
  id: number;
  seller: { slug: string; name: string };
  subtotal: number;
  delivery_fee: number;
  status: SellerOrderStatus;
  refund_needed: boolean;
  items: OrderItem[];
  can_review: boolean; // delivered: the buyer may review this maker (the server checks again)
  my_review: { rating: number; comment: string } | null; // the buyer's review of this maker, if any
}

export type ShipTo = Omit<NewAddress, "label">;

export interface Order {
  id: number;
  payment_status: PaymentStatus;
  items_total: number;
  delivery_total: number;
  grand_total: number;
  ship_to: ShipTo;
  created_at: string;
  paid_at: string | null;
  hold_expires_at: string | null;
  seller_orders: SellerOrder[];
}

export interface CheckoutSession {
  order_id: number;
  razorpay_order_id: string;
  amount: number;
  currency: "INR";
  key_id: string;
  prefill: { name: string; email: string; contact: string };
  hold_expires_at: string;
}

export interface RazorpaySuccess {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}

export interface Store {
  slug: string;
  name: string;
  kind: string;
  main_category: string | null;
  bio: string;
  area: string;
  delivery_days: number;
  delivery_fee_paise: number;
  is_active: boolean; // false = paused
  cover: string | null;
}

export interface ProductPhoto {
  id: number;
  url: string;
  position: number;
}

export interface SellerProduct {
  id: number;
  name: string;
  description: string;
  category: string;
  price_paise: number;
  stock: number;
  is_active: boolean;
  images: ProductPhoto[];
  image: string | null;
  sold: number;
  past_orders: number; // orders that include it: Delete archives instead of removing when > 0
  created_at: string;
}

export interface IncomingOrder {
  id: number;
  order_id: number;
  paid_at: string;
  status: SellerOrderStatus;
  subtotal: number;
  delivery_fee: number;
  refund_needed: boolean;
  preparing_at: string | null;
  out_for_delivery_at: string | null;
  delivered_at: string | null;
  cancelled_at: string | null;
  ship_to: ShipTo;
  items: OrderItem[];
}

export interface SellerOverview {
  earnings_week: number; // paise
  open_orders: number;
  products_listed: number;
  out_of_stock: number; // listed products with stock 0
  rating: number | null; // null = no reviews yet
  review_count: number;
  open_requests: number; // custom requests waiting for a quote
  incoming: IncomingOrder[];
}

export interface SellerReviews {
  average: number | null;
  count: number;
  reviews: { id: number; rating: number; comment: string; buyer_name: string; created_at: string }[];
}

export type RequestStatus = "open" | "quoted" | "accepted" | "declined";

/** A custom request ("photo cake for Saturday"), as its buyer or its seller sees it. Money in paise. */
export interface CustomRequest {
  id: number;
  seller: SellerSummary;
  buyer_name: string; // first name only
  description: string;
  needed_by: string | null; // "2026-10-18"
  budget_paise: number | null;
  quote_paise: number | null;
  seller_note: string;
  status: RequestStatus;
  images: string[];
  in_bag: boolean;
  ordered: boolean;
  created_at: string;
  responded_at: string | null;
}

/** One page of Explore results, with the real total and an optional "Did you mean…?". */
export interface SearchPage {
  count: number;
  page: number;
  pages: number;
  page_size: number;
  results: Product[];
  suggestion: string | null;
}

export interface MyReview {
  id: number;
  rating: number;
  comment: string;
  created_at: string;
}

/** The AI listing helper's suggestion. Never a price. category is null when it couldn't pick a known one. */
export interface ListingSuggestion {
  title: string;
  description: string;
  category: string | null;
}
