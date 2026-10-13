"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { LoadError } from "@/components/LoadError";
import { listOrders } from "@/lib/api/orders";
import type { Order } from "@/lib/api/types";
import { formatINR } from "@/lib/format";
import { PHOTOS } from "@/lib/photos";
import { useSession } from "@/lib/session";
import { STATUS_LABEL } from "@/lib/status";

export default function OrdersPage() {
  const { user, signedOut } = useSession();
  const router = useRouter();
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0); // bump to load again

  useEffect(() => {
    if (signedOut) router.replace("/signin?next=/orders");
    if (!user) return;
    listOrders()
      .then(setOrders)
      .catch(setLoadError);
  }, [user, signedOut, router, attempt]);

  if (loadError) {
    const retry = () => {
      setLoadError(null);
      setAttempt((n) => n + 1);
    };
    return <LoadError error={loadError} onRetry={retry} title="Couldn't load your orders" />;
  }
  if (!orders) return <p className="text-muted">Loading your orders…</p>;

  return (
    <>
      <p className="eyebrow">Buying · My orders</p>
      <h1 className="title mt-1">My orders</h1>
      <div className="mt-6">
        {orders.length === 0 ? (
          <EmptyState
            photoId={PHOTOS.pickles}
            title="No orders yet"
            text="Your orders will show here after checkout."
            action={
              <Link href="/" className="btn btn-black">
                Start exploring
              </Link>
            }
          />
        ) : (
          <div className="flex flex-col gap-3.5">
            {orders.map((order) => (
              <Link
                key={order.id}
                href={`/orders/${order.id}`}
                className="panel flex flex-wrap items-center justify-between gap-3 no-underline transition-transform hover:-translate-y-1"
              >
                <div>
                  <b className="text-lg">Order #{order.id}</b>
                  <div className="text-sm text-muted">
                    {new Date(order.created_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })} ·{" "}
                    {order.seller_orders.length} {order.seller_orders.length === 1 ? "maker" : "makers"}
                  </div>
                </div>
                <div className="flex min-w-0 max-w-full flex-wrap gap-1.5">
                  {order.payment_status === "paid" ? (
                    order.seller_orders.map((part) => (
                      <span key={part.id} className={`status st-${part.status}`}>
                        {part.seller.name}: {STATUS_LABEL[part.status]}
                      </span>
                    ))
                  ) : (
                    <span className="status st-new">Waiting for payment</span>
                  )}
                </div>
                <span className="price">{formatINR(order.grand_total)}</span>
              </Link>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
