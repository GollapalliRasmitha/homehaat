/**
 * Explore filters live in the URL (/explore?q=cake&category=cakes&sort=price_asc…), so a search can be
 * shared, bookmarked, and survives the back button. These two functions convert between the URL and an object.
 */

import { rupeesToPaise } from "./format.ts"; // .ts extension: also loaded by Node's test runner

export const SORTS = [
  ["relevance", "Best match"],
  ["newest", "Newest"],
  ["price_asc", "Price: low to high"],
  ["price_desc", "Price: high to low"],
  ["rating", "Top rated"],
] as const;
export type Sort = (typeof SORTS)[number][0];

export interface ExploreFilters {
  q: string;
  category: string; // "" = all
  sort: Sort;
  inStock: boolean;
  minRupees: string; // as typed, e.g. "200"
  maxRupees: string;
  page: number; // 1, 2, 3… (each page shows 24)
}

const isSort = (value: string | null): value is Sort => SORTS.some(([v]) => v === value);

/** "3" -> 3. Anything that isn't a whole number from 1 up is page 1. */
function readPage(value: string | null): number {
  return value && /^\d+$/.test(value) && Number(value) >= 1 ? Number(value) : 1;
}

/** URL search params -> filters. Unknown values fall back to safe defaults. */
export function readFilters(params: URLSearchParams): ExploreFilters {
  const q = params.get("q")?.trim() ?? "";
  const sort = params.get("sort");
  return {
    q,
    category: params.get("category") ?? "",
    sort: isSort(sort) ? sort : q ? "relevance" : "newest",
    inStock: params.get("in_stock") === "1",
    minRupees: params.get("min") ?? "",
    maxRupees: params.get("max") ?? "",
    page: readPage(params.get("page")),
  };
}

/** Filters -> the URL query string for /explore (empty and default values are left out, to keep links short). */
export function filtersToQuery(f: ExploreFilters): string {
  const params = new URLSearchParams();
  if (f.q) params.set("q", f.q);
  if (f.category) params.set("category", f.category);
  const defaultSort = f.q ? "relevance" : "newest";
  if (f.sort !== defaultSort) params.set("sort", f.sort);
  if (f.inStock) params.set("in_stock", "1");
  if (f.minRupees) params.set("min", f.minRupees);
  if (f.maxRupees) params.set("max", f.maxRupees);
  if (f.page > 1) params.set("page", String(f.page));
  const query = params.toString();
  return query ? `?${query}` : "";
}

/** Filters -> the query for the products API. Prices go to the API in paise; invalid prices are dropped. */
export function filtersToApi(f: ExploreFilters): Record<string, string> {
  const api: Record<string, string> = { sort: f.sort };
  api.page = String(f.page);
  if (f.q) api.q = f.q;
  if (f.category) api.category = f.category;
  if (f.inStock) api.in_stock = "1";
  const min = f.minRupees ? rupeesToPaise(f.minRupees) : null;
  const max = f.maxRupees ? rupeesToPaise(f.maxRupees) : null;
  if (min !== null) api.min_price = String(min);
  if (max !== null) api.max_price = String(max);
  return api;
}
