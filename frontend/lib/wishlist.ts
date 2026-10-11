"use client";

/**
 * The wishlist (hearts): product ids saved in this browser's localStorage.
 * Saving is instant (optimistic, nothing to wait for), and every heart and the header count stay in sync.
 * Decision: kept in the browser for now (no new database table); see CLAUDE.md.
 */

import { useSyncExternalStore } from "react";

const KEY = "homehaat-wishlist";
const EVENT = "homehaat-wishlist-change";
export const MAX_SAVED = 60;

/** Pure helper (tested): add or remove an id, newest first, at most MAX_SAVED. */
export function toggleId(ids: number[], id: number): number[] {
  return ids.includes(id) ? ids.filter((x) => x !== id) : [id, ...ids].slice(0, MAX_SAVED);
}

let cache: { raw: string | null; ids: number[] } = { raw: null, ids: [] };

function read(): number[] {
  let raw: string | null = null;
  try {
    raw = localStorage.getItem(KEY);
  } catch {
    return [];
  }
  if (raw !== cache.raw) {
    // Same raw text -> same array object, so React doesn't re-render for nothing.
    try {
      const parsed = JSON.parse(raw ?? "[]");
      cache = { raw, ids: Array.isArray(parsed) ? parsed.filter(Number.isInteger) : [] };
    } catch {
      cache = { raw, ids: [] };
    }
  }
  return cache.ids;
}

function subscribe(onChange: () => void) {
  window.addEventListener(EVENT, onChange);
  window.addEventListener("storage", onChange); // another tab changed it
  return () => {
    window.removeEventListener(EVENT, onChange);
    window.removeEventListener("storage", onChange);
  };
}

const EMPTY: number[] = [];

/** Saved ids, kept in sync across the page (and other tabs). Empty during server rendering. */
export function useWishlist(): number[] {
  return useSyncExternalStore(subscribe, read, () => EMPTY);
}

/** Save or unsave. Returns true if the product is now saved. */
export function toggleWishlist(id: number): boolean {
  const next = toggleId(read(), id);
  try {
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // storage blocked (some private windows): nothing is saved
  }
  window.dispatchEvent(new Event(EVENT));
  return next.includes(id);
}
