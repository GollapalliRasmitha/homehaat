import { apiFetch } from "./client";
import type { CheckoutSession, Order, RazorpaySuccess } from "./types";

/** Creates the pending order and the Razorpay order. Totals are computed on the server. */
export const startCheckout = (addressId: number) =>
  apiFetch<CheckoutSession>("/checkout/", { method: "POST", body: { address_id: addressId } });

/**
 * Backup for the webhook: forwards Razorpay's signed response for the server to check. Safe to send twice
 * (mark_order_paid is idempotent), so it asks again if the server is waking up.
 */
export const verifyPayment = (response: RazorpaySuccess) =>
  apiFetch<{ order_id: number; payment_status: string }>("/payments/verify/", {
    method: "POST",
    body: response,
    retry: true,
  });

export const getOrder = (id: number | string) => apiFetch<Order>(`/orders/${id}/`);

export const listOrders = () => apiFetch<Order[]>("/orders/");

/** Cancel one maker's part while it's New. The server refunds exactly that part (items + its delivery fee). */
export const cancelPart = (partId: number) => apiFetch<Order>(`/orders/parts/${partId}/cancel/`, { method: "POST" });

/** While the maker is preparing it: ask them to cancel. They accept (refund) or decline. */
export const requestCancel = (partId: number) =>
  apiFetch<Order>(`/orders/parts/${partId}/request-cancel/`, { method: "POST" });
