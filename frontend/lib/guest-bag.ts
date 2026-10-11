/**
 * The guest bag: what a signed-out visitor adds, kept in their own browser
 * (localStorage). It holds only product ids, quantities and notes, never prices:
 * the server prices it (POST /api/cart/preview/) and merges it on sign-in.
 */

import type { GuestLine } from "./api/cart";

const KEY = "homehaat-guest-bag";
export const MAX_QTY = 50;

// --- pure helpers (tested in guest-bag.test.ts) ---

/** Add qty of a product, never going above `max`. Returns the new lines and the quantity actually in the bag. */
export function addLine(lines: GuestLine[], productId: number, qty: number, note: string, max: number) {
  const existing = lines.find((l) => l.product_id === productId);
  const current = existing?.qty ?? 0;
  const next = Math.min(current + qty, max, MAX_QTY);
  const updated = existing
    ? lines.map((l) => (l.product_id === productId ? { ...l, qty: next, note: note || l.note } : l))
    : [...lines, { product_id: productId, qty: next, note }];
  return { lines: next > 0 ? updated : lines, added: next - current };
}

export function setLineQty(lines: GuestLine[], productId: number, qty: number): GuestLine[] {
  return lines.map((l) => (l.product_id === productId ? { ...l, qty: Math.max(1, Math.min(qty, MAX_QTY)) } : l));
}

export function removeLines(lines: GuestLine[], productIds: number[]): GuestLine[] {
  return lines.filter((l) => !productIds.includes(l.product_id));
}

export const countLines = (lines: GuestLine[]) => lines.reduce((sum, l) => sum + l.qty, 0);

// --- browser storage (can be blocked, e.g. in some private windows: then the bag is just empty) ---

export function readGuestBag(): GuestLine[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function writeGuestBag(lines: GuestLine[]) {
  try {
    localStorage.setItem(KEY, JSON.stringify(lines));
  } catch {
    // storage blocked: nothing we can do, the bag stays in memory for this page only
  }
}

export function clearGuestBag() {
  try {
    localStorage.removeItem(KEY);
  } catch {
    // ignore
  }
}
