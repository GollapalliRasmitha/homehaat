import { apiFetch } from "./client";
import type { Cart } from "./types";

export interface GuestLine {
  product_id: number;
  qty: number;
  note: string;
}

export const getCart = () => apiFetch<Cart>("/cart/");

// Only the product and quantity are sent. The server looks up the price itself.
export const addToCart = (productId: number, qty: number, note = "") =>
  apiFetch<Cart>("/cart/items/", { method: "POST", body: { product_id: productId, qty, note } });

export const updateCartItem = (itemId: number, qty: number) =>
  apiFetch<Cart>(`/cart/items/${itemId}/`, { method: "PATCH", body: { qty } });

export const removeCartItem = (itemId: number) => apiFetch<Cart>(`/cart/items/${itemId}/`, { method: "DELETE" });

/** A guest's bag lives in their browser; the server prices it (nothing is saved). */
export const previewCart = (items: GuestLine[]) =>
  apiFetch<Cart>("/cart/preview/", { method: "POST", body: { items } });

/** After sign-in: add the guest bag into the account's bag. */
export const mergeGuestCart = (items: GuestLine[]) =>
  apiFetch<Cart & { skipped: string[] }>("/cart/merge/", { method: "POST", body: { items } });
