"use client";

import { toast } from "sonner";

import { addToCart } from "./api/cart";
import { errorMessage } from "./api/client";
import type { User } from "./api/types";
import { addLine, readGuestBag, writeGuestBag } from "./guest-bag";

/**
 * Add a product to the bag, signed in or not, and tell the buyer what happened.
 * Guests: kept in this browser (moves into the account at sign-in). Signed in: saved on the server.
 * Returns true if something was added.
 */
export async function addProductToBag(
  { id, stock }: { id: number; stock: number },
  qty: number,
  note: string,
  user: User | null,
  refresh: () => Promise<void>,
): Promise<boolean> {
  if (!user) {
    const { lines, added } = addLine(readGuestBag(), id, qty, note, Math.min(stock, 50));
    if (added === 0) {
      toast(`Only ${stock} available, and ${stock === 1 ? "it's" : "they're"} already in your bag.`);
      return false;
    }
    writeGuestBag(lines);
    await refresh();
    toast(added < qty ? `Added ${added}: only ${stock} available` : "Added to bag");
    return true;
  }
  try {
    await addToCart(id, qty, note);
    await refresh();
    toast("Added to bag");
    return true;
  } catch (error) {
    toast(`Couldn't add to bag. ${errorMessage(error)}`);
    return false;
  }
}
