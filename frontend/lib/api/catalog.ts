import { apiFetch } from "./client";
import type { Category, Product, PublicStore, StoreReview } from "./types";

const query = (params: Record<string, string | number | undefined>) => {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== "") as [string, string][];
  return entries.length ? `?${new URLSearchParams(entries.map(([k, v]) => [k, String(v)]))}` : "";
};

export const listCategories = () => apiFetch<Category[]>("/categories/");

/** Search and browse. Filters: q, category, seller, min_price/max_price (paise), in_stock, sort, ids, limit. */
export const listProducts = (params: Record<string, string | number | undefined> = {}) =>
  apiFetch<Product[]>(`/products/${query(params)}`);

export const getProduct = (id: number | string) => apiFetch<Product>(`/products/${id}/`);

export const listStores = (params: { q?: string; limit?: number } = {}) =>
  apiFetch<PublicStore[]>(`/stores/${query(params)}`);

export const getStore = (slug: string) => apiFetch<PublicStore>(`/stores/${encodeURIComponent(slug)}/`);

export const getStoreReviews = (slug: string) =>
  apiFetch<StoreReview[]>(`/stores/${encodeURIComponent(slug)}/reviews/`);
