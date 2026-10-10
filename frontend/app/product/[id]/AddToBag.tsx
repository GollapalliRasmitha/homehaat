"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { addToCart } from "@/lib/api/cart";
import { ApiError } from "@/lib/api/client";
import { useSession } from "@/lib/session";

export function AddToBag({ productId, stock, sellerSlug }: { productId: number; stock: number; sellerSlug: string }) {
  const { user, refresh } = useSession();
  const router = useRouter();
  const [qty, setQty] = useState(1);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const isMine = user?.store_slug === sellerSlug;
  const max = Math.min(stock, 50);

  async function add() {
    if (!user) {
      // Guest bags arrive in Stage 2. For now, sign in first and come back here.
      router.push(`/signin?next=/product/${productId}`);
      return;
    }
    setBusy(true);
    try {
      await addToCart(productId, qty, note);
      await refresh();
      toast("Added to bag");
    } catch (error) {
      toast(error instanceof ApiError ? error.message : "Couldn't add to bag. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div>
        <span className="field-label">Quantity</span>
        <div className="inline-flex h-[46px] items-center rounded-full border border-line bg-white">
          <button
            type="button"
            className="h-11 w-[46px] rounded-full text-xl hover:bg-soft"
            onClick={() => setQty((q) => Math.max(1, q - 1))}
            aria-label="Decrease quantity"
          >
            −
          </button>
          <span className="min-w-7 text-center font-semibold tabular-nums" aria-live="polite">
            {qty}
          </span>
          <button
            type="button"
            className="h-11 w-[46px] rounded-full text-xl hover:bg-soft"
            onClick={() => setQty((q) => Math.min(Math.max(max, 1), q + 1))}
            aria-label="Increase quantity"
          >
            +
          </button>
        </div>
      </div>
      <div>
        <label className="field-label" htmlFor="note">
          Note to the maker (optional)
        </label>
        <textarea id="note" className="textarea" rows={2} maxLength={300} value={note} onChange={(e) => setNote(e.target.value)} />
      </div>
      <button className="btn btn-black btn-lg" onClick={add} disabled={busy || stock === 0 || isMine}>
        {isMine ? "This is your product" : stock === 0 ? "Sold out" : busy ? "Adding…" : "Add to bag"}
      </button>
    </>
  );
}
