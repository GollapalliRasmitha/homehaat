"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { IncomingOrderCard } from "@/components/IncomingOrderCard";
import { LoadError } from "@/components/LoadError";
import { listIncomingOrders } from "@/lib/api/seller";
import type { IncomingOrder, SellerOrderStatus } from "@/lib/api/types";
import { PHOTOS } from "@/lib/photos";
import { useSession } from "@/lib/session";
import { STATUS_LABEL } from "@/lib/status";

const FILTERS: (SellerOrderStatus | "all")[] = ["all", "new", "preparing", "out_for_delivery", "delivered", "cancelled"];

export default function SellerOrdersPage() {
  const { refresh } = useSession();
  const [orders, setOrders] = useState<IncomingOrder[] | null>(null);
  const [filter, setFilter] = useState<SellerOrderStatus | "all">("all");
  const [loadError, setLoadError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    listIncomingOrders()
      .then(setOrders)
      .catch(setLoadError);
  }, [attempt]);

  if (loadError) {
    const retry = () => {
      setLoadError(null);
      setAttempt((n) => n + 1);
    };
    return <LoadError error={loadError} onRetry={retry} title="Couldn't load your orders" />;
  }
  if (!orders) return <p className="text-muted">Loading your orders…</p>;

  const count = (f: SellerOrderStatus | "all") => (f === "all" ? orders.length : orders.filter((o) => o.status === f).length);
  const shown = filter === "all" ? orders : orders.filter((o) => o.status === filter);

  return (
    <>
      <div className="mb-6 flex flex-wrap gap-2.5" role="group" aria-label="Show orders">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            aria-pressed={filter === f}
            className={`h-[42px] rounded-full border px-[18px] text-[15px] font-medium ${
              filter === f ? "border-ink bg-ink text-white" : "border-line bg-white hover:border-ink"
            }`}
          >
            {f === "all" ? "All" : STATUS_LABEL[f]} ({count(f)})
          </button>
        ))}
      </div>

      {shown.length === 0 ? (
        <EmptyState
          photoId={PHOTOS.pickles}
          title={orders.length === 0 ? "No orders yet" : `No ${STATUS_LABEL[filter as SellerOrderStatus].toLowerCase()} orders`}
          text={
            orders.length === 0
              ? "When someone buys from your shop and pays, the order appears here with their address."
              : "Choose another filter to see your other orders."
          }
        />
      ) : (
        <div className="flex flex-col gap-3.5">
          {shown.map((order) => (
            <IncomingOrderCard
              key={order.id}
              order={order}
              onChange={(updated) => {
                setOrders(orders.map((o) => (o.id === updated.id ? updated : o)));
                refresh(); // the open-orders count in the tabs and the account menu
              }}
            />
          ))}
        </div>
      )}
    </>
  );
}
