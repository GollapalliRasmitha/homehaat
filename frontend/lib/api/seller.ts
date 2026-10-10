import { apiFetch } from "./client";
import type { IncomingOrder, SellerProduct, Store } from "./types";

export type NewStore = Pick<Store, "name" | "kind" | "main_category" | "bio" | "area" | "delivery_days" | "delivery_fee_paise">;

export const getMyStore = () => apiFetch<Store>("/seller/store/");

export const openStore = (body: NewStore) => apiFetch<Store>("/seller/store/", { method: "POST", body });

export const listMyProducts = () => apiFetch<SellerProduct[]>("/seller/products/");

export type NewProduct = Pick<SellerProduct, "name" | "description" | "category" | "price_paise" | "stock">;

export const addProduct = (body: NewProduct) =>
  apiFetch<SellerProduct>("/seller/products/", { method: "POST", body });

export const listIncomingOrders = () => apiFetch<IncomingOrder[]>("/seller/orders/");
