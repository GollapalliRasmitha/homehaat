import { apiFetch } from "./client";
import type { CustomRequest } from "./types";

// --- buyer ---

export interface NewRequest {
  seller: string; // the shop's link (slug)
  description: string;
  needed_by: string | null;
  budget_paise: number | null;
}

export const listMyRequests = () => apiFetch<CustomRequest[]>("/requests/");

export const createRequest = (body: NewRequest) => apiFetch<CustomRequest>("/requests/", { method: "POST", body });

export function uploadRequestPhoto(id: number, photo: Blob) {
  const form = new FormData();
  form.append("image", photo, "reference.jpg");
  return apiFetch<{ ok: true }>(`/requests/${id}/images/`, { method: "POST", form });
}

export const getMyRequest = (id: number) => apiFetch<CustomRequest>(`/requests/${id}/`);

/** Accept the maker's quote: the server puts a one-off item at the quoted price in your bag. */
export const acceptQuote = (id: number) => apiFetch<CustomRequest>(`/requests/${id}/accept/`, { method: "POST" });

export const declineQuote = (id: number) => apiFetch<CustomRequest>(`/requests/${id}/decline/`, { method: "POST" });

export const addQuoteToBag = (id: number) => apiFetch<CustomRequest>(`/requests/${id}/add-to-bag/`, { method: "POST" });

// --- seller ---

export const listShopRequests = () => apiFetch<CustomRequest[]>("/seller/requests/");

export const sendQuote = (id: number, quote_paise: number, note: string) =>
  apiFetch<CustomRequest>(`/seller/requests/${id}/quote/`, { method: "POST", body: { quote_paise, note } });

export const declineRequest = (id: number) =>
  apiFetch<CustomRequest>(`/seller/requests/${id}/decline/`, { method: "POST" });
