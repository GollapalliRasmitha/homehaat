"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { EmptyState } from "@/components/EmptyState";
import { ProductImage } from "@/components/ProductImage";
import { getCart, removeCartItem, updateCartItem } from "@/lib/api/cart";
import { ApiError } from "@/lib/api/client";
import type { Cart } from "@/lib/api/types";
import { deliveryText, formatINR } from "@/lib/format";
import { useSession } from "@/lib/session";

export default function CartPage() {
  const { user, loading, refresh } = useSession();
  const [cart, setCart] = useState<Cart | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!user) return;
    getCart()
      .then(setCart)
      .catch(() => setFailed(true));
  }, [user]);

  async function change(action: () => Promise<Cart>, message?: string) {
    try {
      setCart(await action()); // the server sends back the whole bag with fresh totals
      await refresh();
      if (message) toast(message);
    } catch (error) {
      toast(error instanceof ApiError ? error.message : "Couldn't update your bag.");
    }
  }

  if (loading || (user && !cart && !failed)) return <p className="text-muted">Loading your bag…</p>;
  if (failed) return <EmptyState title="Couldn't load your bag" text="Please refresh the page in a moment." />;

  const startExploring = (
    <Link href="/" className="btn btn-black">
      Start exploring
    </Link>
  );
  if (!user) {
    return (
      <EmptyState
        title="Your bag is empty"
        text="Sign in to add handmade things to your bag."
        action={
          <Link href="/signin?next=/cart" className="btn btn-black">
            Sign in
          </Link>
        }
      />
    );
  }
  if (!cart || cart.items.length === 0) {
    return <EmptyState title="Your bag is empty" text="Find something handmade by a maker near you." action={startExploring} />;
  }

  const seller = cart.items[0].product.seller; // Stage 1: one maker per bag
  return (
    <>
      <h1 className="title">Your bag</h1>
      <p className="mb-6 mt-1.5 text-muted">
        {cart.count} {cart.count === 1 ? "item" : "items"} from {seller.name}
      </p>
      <div className="flex flex-wrap items-start gap-7">
        <section className="panel min-w-0 flex-[999_1_520px]" aria-label={seller.name}>
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3.5">
            <div>
              <div className="text-lg font-semibold">{seller.name}</div>
              {seller.area && <div className="text-sm text-muted">{seller.area}</div>}
            </div>
            <span className="status st-delivered">{deliveryText(seller.delivery_days)}</span>
          </div>
          {cart.items.map((item) => (
            <div key={item.id} className="flex flex-wrap items-center gap-4 border-b border-line py-4">
              <ProductImage product={item.product} className="size-[84px] flex-none rounded-2xl" />
              <div className="min-w-0 flex-[1_1_180px]">
                <div className="font-bold">{item.product.name}</div>
                <div className="text-sm text-muted">{formatINR(item.product.price_paise)} each</div>
                {item.note && <div className="text-sm text-muted">Note: {item.note}</div>}
                <button
                  className="py-2 text-sm text-muted underline"
                  onClick={() => change(() => removeCartItem(item.id), "Removed from bag")}
                >
                  Remove
                </button>
              </div>
              <div className="inline-flex h-[46px] items-center rounded-full border border-line">
                <button
                  className="h-11 w-[46px] rounded-full text-xl hover:bg-soft disabled:opacity-30"
                  aria-label={`Decrease quantity of ${item.product.name}`}
                  disabled={item.qty <= 1}
                  onClick={() => change(() => updateCartItem(item.id, item.qty - 1))}
                >
                  −
                </button>
                <span className="min-w-7 text-center font-semibold tabular-nums">{item.qty}</span>
                <button
                  className="h-11 w-[46px] rounded-full text-xl hover:bg-soft"
                  aria-label={`Increase quantity of ${item.product.name}`}
                  onClick={() => change(() => updateCartItem(item.id, item.qty + 1))}
                >
                  +
                </button>
              </div>
              <span className="price min-w-[90px] text-right">{formatINR(item.line_total)}</span>
            </div>
          ))}
          <div className="flex justify-between pt-3 text-[15px] text-muted">
            <span>Delivery</span>
            <span>{formatINR(cart.delivery_total)}</span>
          </div>
        </section>

        <aside className="sticky top-4 flex min-w-0 flex-[1_1_300px] flex-col gap-3.5 rounded-[24px] bg-soft p-6" aria-label="Order summary">
          <h2 className="text-[22px]">Summary</h2>
          <div className="flex justify-between text-[15px] text-muted">
            <span>Items ({cart.count})</span>
            <span>{formatINR(cart.items_total)}</span>
          </div>
          <div className="flex justify-between text-[15px] text-muted">
            <span>Delivery</span>
            <span>{formatINR(cart.delivery_total)}</span>
          </div>
          <div className="flex items-baseline justify-between border-t border-[#ddd] py-3.5">
            <span className="font-bold">Total</span>
            <b className="price text-[30px]">{formatINR(cart.grand_total)}</b>
          </div>
          <div className="rounded-[14px] bg-white px-3.5 py-3 text-sm">One payment. HomeHaat splits it into 1 order, one for each maker.</div>
          <Link href="/checkout" className="btn btn-black btn-lg">
            Checkout
          </Link>
        </aside>
      </div>
    </>
  );
}
