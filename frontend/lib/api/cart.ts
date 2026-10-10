import { apiFetch } from "./client";
import type { Cart } from "./types";

export const getCart = () => apiFetch<Cart>("/cart/");

// Only the product and quantity are sent. The server looks up the price itself.
export const addToCart = (productId: number, qty: number, note = "") =>
  apiFetch<Cart>("/cart/items/", { method: "POST", body: { product_id: productId, qty, note } });

export const updateCartItem = (itemId: number, qty: number) =>
  apiFetch<Cart>(`/cart/items/${itemId}/`, { method: "PATCH", body: { qty } });

export const removeCartItem = (itemId: number) => apiFetch<Cart>(`/cart/items/${itemId}/`, { method: "DELETE" });
