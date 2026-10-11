"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { getCart, previewCart, removeCartItem, updateCartItem } from "./api/cart";
import { ApiError } from "./api/client";
import type { Cart, CartLine } from "./api/types";
import { readGuestBag, removeLines, setLineQty, writeGuestBag } from "./guest-bag";
import { useSession } from "./session";

const EMPTY: Cart = { groups: [], count: 0, items_total: 0, delivery_total: 0, grand_total: 0, has_problems: false };

/**
 * The bag, signed in or not. Signed in: saved on the server. Guest: kept in
 * this browser and priced by the server. Pages use this and don't need to care which.
 */
export function useBag() {
  const { user, loading: sessionLoading, refresh } = useSession();
  const [cart, setCart] = useState<Cart | null>(null);
  const [failed, setFailed] = useState(false);

  const load = useCallback(async () => {
    try {
      const guest = readGuestBag();
      setCart(user ? await getCart() : guest.length ? await previewCart(guest) : EMPTY);
      setFailed(false);
    } catch {
      setFailed(true);
    }
  }, [user]);

  useEffect(() => {
    // Load the bag once we know who is signed in (syncing with the server).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (!sessionLoading) load();
  }, [sessionLoading, load]);

  async function run(change: () => Promise<Cart | void>, message?: string) {
    try {
      const updated = await change();
      if (updated) setCart(updated);
      else await load();
      await refresh(); // header bag count
      if (message) toast(message);
    } catch (error) {
      toast(error instanceof ApiError ? error.message : "Couldn't update your bag.");
    }
  }

  const setQty = (line: CartLine, qty: number) =>
    run(async () => {
      if (line.id !== null) return updateCartItem(line.id, qty);
      writeGuestBag(setLineQty(readGuestBag(), line.product.id, qty));
    });

  const remove = (line: CartLine) =>
    run(async () => {
      if (line.id !== null) return removeCartItem(line.id);
      writeGuestBag(removeLines(readGuestBag(), [line.product.id]));
    }, "Removed from bag");

  /** Remove several products at once (e.g. the ones that sold out). */
  const removeProducts = (productIds: number[]) =>
    run(async () => {
      const lines = (cart?.groups ?? []).flatMap((g) => g.items).filter((l) => productIds.includes(l.product.id));
      if (user) {
        for (const line of lines) if (line.id !== null) await removeCartItem(line.id);
      } else {
        writeGuestBag(removeLines(readGuestBag(), productIds));
      }
    }, "Removed from bag");

  return { cart, failed, loading: sessionLoading || (!cart && !failed), setQty, remove, removeProducts, reload: load };
}
