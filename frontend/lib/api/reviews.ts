import { apiFetch } from "./client";
import type { MyReview } from "./types";

/** Write (or edit) my review of a maker. The server allows it only after one of their orders was delivered. */
export const writeReview = (seller: string, rating: number, comment: string) =>
  apiFetch<MyReview>("/reviews/", { method: "POST", body: { seller, rating, comment } });
