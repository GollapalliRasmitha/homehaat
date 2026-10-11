"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { getCart, previewCart, removeCartItem, updateCartItem } from "./api/cart";
import { errorMessage } from "./api/client";
import type { Cart, CartLine } from "./api/types";
import { withQty } from "./bag-math";
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
  const [loadError, setLoadError] = useState<unknown>(null);

  const load = useCallback(async () => {
    try {
      const guest = readGuestBag();
      setCart(user ? await getCart() : guest.length ? await previewCart(guest) : EMPTY);
      setLoadError(null);
    } catch (error) {
      setLoadError(error); // the page shows it with a Try again button
    }
  }, [user]);

  useEffect(() => {
    // Load the bag once we know who is signed in (syncing with the server).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (!sessionLoading) load();
  }, [sessionLoading, load]);

  async function run(change: () => Promise<Cart | void>, message?: string, undo?: Cart | null) {
    try {
      const updated = await change();
      if (updated) setCart(updated);
      else await load();
      await refresh(); // header bag count
      if (message) toast(message);
    } catch (error) {
      if (undo) setCart(undo); // the server said no: put the bag back as it was
      toast(`Couldn't update your bag. ${errorMessage(error)}`);
    }
  }

  /** Optimistic: the new quantity and totals show at once; the server's answer then replaces them. */
  const setQty = (line: CartLine, qty: number) => {
    const before = cart;
    if (cart) setCart(withQty(cart, line.product.id, qty));
    return run(
      async () => {
        if (line.id !== null) return updateCartItem(line.id, qty);
        writeGuestBag(setLineQty(readGuestBag(), line.product.id, qty));
      },
      undefined,
      before,
    );
  };

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

  const failed = loadError !== null;
  return { cart, failed, loadError, loading: sessionLoading || (!cart && !failed), setQty, remove, removeProducts, reload: load };
}
