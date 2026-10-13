"use client";

import { useState } from "react";

import { WishlistButton } from "@/components/WishlistButton";
import { addProductToBag } from "@/lib/add-to-bag";
import { useSession } from "@/lib/session";

export function AddToBag({
  productId,
  productName,
  stock,
  sellerSlug,
  takingOrders = true,
}: {
  productId: number;
  productName: string;
  stock: number;
  sellerSlug: string;
  takingOrders?: boolean;
}) {
  const { user, refresh } = useSession();
  const [qty, setQty] = useState(1);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const isMine = user?.store_slug === sellerSlug;
  const max = Math.min(stock, 50);

  async function add() {
    setBusy(true);
    await addProductToBag({ id: productId, stock }, qty, note, user, refresh);
    setBusy(false);
  }

  return (
    <>
      <div>
        <span className="field-label" id="qty-label">
          Quantity
        </span>
        <div className="inline-flex h-[46px] items-center rounded-full border border-line bg-white" role="group" aria-labelledby="qty-label">
          <button
            type="button"
            className="h-11 w-[46px] rounded-full text-xl hover:bg-soft disabled:opacity-30"
            onClick={() => setQty((q) => Math.max(1, q - 1))}
            disabled={qty <= 1}
            aria-label="Decrease quantity"
          >
            −
          </button>
          <span className="min-w-7 text-center font-semibold tabular-nums" aria-live="polite">
            {qty}
          </span>
          <button
            type="button"
            className="h-11 w-[46px] rounded-full text-xl hover:bg-soft disabled:opacity-30"
            onClick={() => setQty((q) => Math.min(Math.max(max, 1), q + 1))}
            disabled={qty >= max}
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
        <textarea
          id="note"
          className="textarea"
          rows={2}
          maxLength={300}
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="e.g. Write “Happy birthday Meera”, less spicy, size M"
        />
      </div>
      <div className="flex flex-wrap gap-2.5">
        <button className="btn btn-black btn-lg flex-[1_1_220px]" onClick={add} disabled={busy || stock === 0 || isMine || !takingOrders}>
          {isMine
            ? "This is your product"
            : !takingOrders
              ? "Not taking orders right now"
              : stock === 0
                ? "Sold out"
                : busy
                  ? "Adding…"
                  : "Add to bag"}
        </button>
        <WishlistButton productId={productId} productName={productName} variant="large" />
      </div>
    </>
  );
}
