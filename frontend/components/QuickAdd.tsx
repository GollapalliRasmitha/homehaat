"use client";

import { Plus } from "lucide-react";
import { useState } from "react";

import { addProductToBag } from "@/lib/add-to-bag";
import type { Product } from "@/lib/api/types";
import { useSession } from "@/lib/session";

/** The round black + on product cards: adds one to the bag without leaving the page. */
export function QuickAdd({ product }: { product: Product }) {
  const { user, refresh } = useSession();
  const [busy, setBusy] = useState(false);
  const mine = user?.store_slug === product.seller.slug;
  const soldOut = product.stock === 0;

  return (
    <button
      type="button"
      onClick={async () => {
        setBusy(true);
        await addProductToBag(product, 1, "", user, refresh);
        setBusy(false);
      }}
      disabled={busy || soldOut || mine}
      aria-label={soldOut ? `${product.name} is sold out` : mine ? `${product.name} is your product` : `Add ${product.name} to bag`}
      title={mine ? "This is your product" : undefined}
      className="flex size-11 flex-none items-center justify-center rounded-full bg-ink text-white transition-transform hover:bg-black-2 active:scale-[0.97] disabled:opacity-30"
    >
      <Plus size={20} strokeWidth={2.4} aria-hidden="true" />
    </button>
  );
}
