"use client";

import Link from "next/link";

import { BagLine } from "@/components/BagLine";
import { EmptyState } from "@/components/EmptyState";
import { LoadError } from "@/components/LoadError";
import { useBag } from "@/lib/bag";
import { deliveryText, formatINR } from "@/lib/format";
import { useSession } from "@/lib/session";

export default function CartPage() {
  const { user } = useSession();
  const { cart, failed, loadError, loading, setQty, remove, removeProducts, reload } = useBag();

  if (failed) return <LoadError error={loadError} onRetry={reload} title="Couldn't load your bag" />;
  if (loading || !cart) return <p className="text-muted">Loading your bag…</p>;
  if (cart.groups.length === 0) {
    return (
      <EmptyState
        title="Your bag is empty"
        text="Find something handmade by a maker near you."
        action={
          <Link href="/" className="btn btn-black">
            Start exploring
          </Link>
        }
      />
    );
  }

  const makers = cart.groups.length;
  const problemIds = cart.groups.flatMap((g) => g.items).filter((l) => l.problem).map((l) => l.product.id);
  return (
    <>
      <h1 className="title">Your bag</h1>
      <p className="mb-6 mt-1.5 text-muted">
        {cart.count} {cart.count === 1 ? "item" : "items"} from {makers} {makers === 1 ? "maker" : "makers"}
      </p>

      {cart.has_problems && (
        <div className="panel mb-5 flex flex-wrap items-center justify-between gap-3" role="alert">
          <p className="font-semibold">Some items sold out while you were shopping.</p>
          <button className="btn btn-white" onClick={() => removeProducts(problemIds)}>
            Remove sold-out items
          </button>
        </div>
      )}

      <div className="flex flex-wrap items-start gap-7">
        <div className="flex min-w-0 flex-[999_1_520px] flex-col gap-[18px]">
          {cart.groups.map((group) => (
            <section key={group.seller.slug} className="panel" aria-label={group.seller.name}>
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3.5">
                <div>
                  <div className="text-lg font-semibold">{group.seller.name}</div>
                  {group.seller.area && <div className="text-sm text-muted">{group.seller.area}</div>}
                </div>
                <span className="status st-delivered">{deliveryText(group.seller.delivery_days)}</span>
              </div>
              {group.items.map((line) => (
                <BagLine
                  key={line.product.id}
                  line={line}
                  onQty={(qty) => setQty(line, qty)}
                  onRemove={() => remove(line)}
                />
              ))}
              <div className="flex flex-col gap-1.5 pt-3">
                <div className="flex justify-between text-[15px] text-muted">
                  <span>Delivery</span>
                  <span>{formatINR(group.delivery_fee)}</span>
                </div>
                <div className="flex justify-between text-[15px] font-bold">
                  <span>Subtotal from {group.seller.name}</span>
                  <span>{formatINR(group.subtotal)}</span>
                </div>
              </div>
            </section>
          ))}
        </div>

        <aside className="sticky top-4 flex min-w-0 flex-[1_1_300px] flex-col gap-3.5 rounded-[24px] bg-soft p-6" aria-label="Order summary">
          <h2 className="text-[22px]">Summary</h2>
          <div className="flex justify-between text-[15px] text-muted">
            <span>Items ({cart.count})</span>
            <span>{formatINR(cart.items_total)}</span>
          </div>
          <div className="flex justify-between text-[15px] text-muted">
            <span>
              Delivery ({makers} {makers === 1 ? "maker" : "makers"})
            </span>
            <span>{formatINR(cart.delivery_total)}</span>
          </div>
          <div className="flex items-baseline justify-between border-t border-[#ddd] py-3.5">
            <span className="font-bold">Total</span>
            <b className="price text-[30px]">{formatINR(cart.grand_total)}</b>
          </div>
          <div className="rounded-[14px] bg-white px-3.5 py-3 text-sm">
            One payment. HomeHaat splits it into {makers} seller {makers === 1 ? "order" : "orders"}.
          </div>
          {cart.has_problems ? (
            <button className="btn btn-black btn-lg" disabled>
              Remove sold-out items to check out
            </button>
          ) : (
            <Link href={user ? "/checkout" : "/signin?next=/checkout"} className="btn btn-black btn-lg">
              {user ? "Checkout" : "Sign in to check out"}
            </Link>
          )}
        </aside>
      </div>
    </>
  );
}
