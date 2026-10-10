import { apiFetch } from "./client";
import type { CheckoutSession, Order, RazorpaySuccess } from "./types";

/** Creates the pending order and the Razorpay order. Totals are computed on the server. */
export const startCheckout = (addressId: number) =>
  apiFetch<CheckoutSession>("/checkout/", { method: "POST", body: { address_id: addressId } });

/** Local backup for the webhook: forwards Razorpay's signed response for the server to check. */
export const verifyPayment = (response: RazorpaySuccess) =>
  apiFetch<{ order_id: number; payment_status: string }>("/payments/verify/", { method: "POST", body: response });

export const getOrder = (id: number | string) => apiFetch<Order>(`/orders/${id}/`);

export const listOrders = () => apiFetch<Order[]>("/orders/");
