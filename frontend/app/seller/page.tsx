"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { getMyStore, listIncomingOrders, listMyProducts } from "@/lib/api/seller";
import type { IncomingOrder, SellerProduct, Store } from "@/lib/api/types";
import { formatINR } from "@/lib/format";
import { PHOTOS } from "@/lib/photos";
import { useSession } from "@/lib/session";
import { STATUS_LABEL } from "@/lib/status";

// Stage 1: a simple seller page listing PAID orders. The full SellerShell dashboard is Stage 3.
export default function SellerPage() {
  const { user, loading } = useSession();
  const router = useRouter();
  const [store, setStore] = useState<Store | null>(null);
  const [orders, setOrders] = useState<IncomingOrder[] | null>(null);
  const [products, setProducts] = useState<SellerProduct[] | null>(null);

  useEffect(() => {
    if (loading) return;
    if (!user) return router.replace("/signin?next=/seller");
    if (!user.store_slug) return router.replace("/sell");
    Promise.all([getMyStore(), listIncomingOrders(), listMyProducts()]).then(([s, o, p]) => {
      setStore(s);
      setOrders(o);
      setProducts(p);
    });
  }, [user, loading, router]);

  if (!store || !orders || !products) return <p className="text-muted">Loading your shop…</p>;

  return (
    <>
      <h1 className="title">{store.name}</h1>
      <p className="mb-8 mt-1.5 text-muted">Your shop dashboard</p>

      <section aria-labelledby="orders-h" className="mb-12">
        <h2 id="orders-h" className="mb-4 text-[28px]">
          Paid orders
        </h2>
        {orders.length === 0 ? (
          <EmptyState
            photoId={PHOTOS.pickles}
            title="No orders yet"
            text="When someone buys from your shop and pays, the order appears here with their address."
          />
        ) : (
          <div className="flex flex-col gap-3.5">
            {orders.map((o) => (
              <div key={o.id} className="panel">
                <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line pb-3.5">
                  <div>
                    <b className="text-lg">Order #{o.order_id}</b>
                    <div className="text-sm text-muted">
                      Paid {new Date(o.paid_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}
                    </div>
                    <div className="text-sm text-muted">
                      {o.ship_to.name}, {o.ship_to.phone} · {o.ship_to.line1}
                      {o.ship_to.line2 && `, ${o.ship_to.line2}`}, {o.ship_to.city} {o.ship_to.pincode}
                    </div>
                  </div>
                  <span className={`status st-${o.status}`}>{STATUS_LABEL[o.status]}</span>
                </div>
                {o.items.map((item) => (
                  <div key={item.id} className="mt-2 flex justify-between text-[15px]">
                    <span>
                      {item.qty} × {item.name}
                      {item.note && <span className="block text-sm text-muted">Note: {item.note}</span>}
                    </span>
                    <span>{formatINR(item.line_total)}</span>
                  </div>
                ))}
                <div className="mt-2 flex justify-between text-[15px] text-muted">
                  <span>Delivery fee</span>
                  <span>{formatINR(o.delivery_fee)}</span>
                </div>
                <div className="mt-1 flex justify-between font-semibold">
                  <span>You receive</span>
                  <span>{formatINR(o.subtotal + o.delivery_fee)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section aria-labelledby="products-h">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <h2 id="products-h" className="text-[28px]">
            Your products
          </h2>
          {products.length > 0 && (
            <Link href="/seller/products/new" className="btn btn-black">
              Add a product
            </Link>
          )}
        </div>
        {products.length === 0 ? (
          <EmptyState
            photoId={PHOTOS.cakes}
            title="Add your first product"
            text="Name it, set a price and stock. Buyers can then find it."
            action={
              <Link href="/seller/products/new" className="btn btn-black btn-lg">
                Add a product
              </Link>
            }
          />
        ) : (
          <div className="panel">
            {products.map((p) => (
              <div key={p.id} className="flex flex-wrap items-center gap-3.5 border-b border-line py-3.5 last:border-0">
                <div className="min-w-0 flex-[1_1_200px]">
                  <Link href={`/product/${p.id}`} className="font-bold">
                    {p.name}
                  </Link>
                  <div className="text-sm text-muted">
                    {formatINR(p.price_paise)} · {p.stock} in stock
                  </div>
                </div>
                <span className={`status ${p.is_active ? "st-delivered" : "st-cancelled"}`}>{p.is_active ? "Live" : "Hidden"}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
