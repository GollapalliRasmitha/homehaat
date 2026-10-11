// Shapes returned by the Django API. All money fields are integer paise.

export type Role = "buyer" | "seller" | "admin";

export interface User {
  id: number;
  email: string;
  name: string;
  phone: string;
  role: Role;
  store_slug: string | null;
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
}

export type NewAddress = Omit<Address, "id">;

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
}

export interface SellerOrder {
  id: number;
  seller: { slug: string; name: string };
  subtotal: number;
  delivery_fee: number;
  status: SellerOrderStatus;
  refund_needed: boolean;
  items: OrderItem[];
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
  rating: number | null; // null = no reviews yet
  review_count: number;
  incoming: IncomingOrder[];
}

export interface SellerReviews {
  average: number | null;
  count: number;
  reviews: { id: number; rating: number; comment: string; buyer_name: string; created_at: string }[];
}
