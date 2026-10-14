"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { IncomingOrderCard } from "@/components/IncomingOrderCard";
import { LoadError } from "@/components/LoadError";
import { StatCard } from "@/components/StatCard";
import { TakingOrders } from "@/components/TakingOrders";
import { getOverview } from "@/lib/api/seller";
import type { SellerOverview } from "@/lib/api/types";
import { formatINR } from "@/lib/format";
import { PHOTOS } from "@/lib/photos";
import { useSession } from "@/lib/session";

export default function OverviewPage() {
  const { user, refresh } = useSession();
  const [data, setData] = useState<SellerOverview | null>(null);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    getOverview()
      .then(setData)
      .catch(setLoadError);
  }, [attempt]);

  if (loadError) {
    const retry = () => {
      setLoadError(null);
      setAttempt((n) => n + 1);
    };
    return <LoadError error={loadError} onRetry={retry} />;
  }
  if (!data) return <p className="text-muted">Loading…</p>;

  const firstName = user?.name.split(" ")[0];
  return (
    <>
      <TakingOrders />

      <h2 className="mt-8 text-[clamp(26px,3vw,36px)]">
        Hi{firstName ? `, ${firstName}` : ""}. <span className="serif">Here&apos;s your shop today.</span>
      </h2>

      {/* Every number comes from the database. "—" means there's nothing to count yet. */}
      <div className="mb-10 mt-6 grid grid-cols-[repeat(auto-fill,minmax(160px,1fr))] gap-3.5">
        <StatCard value={formatINR(data.earnings_week)} label="Earned in the last 7 days" />
        <StatCard value={String(data.open_orders)} label="Open orders" />
        <StatCard
          value={String(data.products_listed)}
          note={data.out_of_stock > 0 ? `${data.out_of_stock} out of stock` : undefined}
          label="Products listed"
        />
        <StatCard
          value={data.rating === null ? "—" : `${data.rating} ★`}
          label={
            data.review_count
              ? `Rating (${data.review_count} ${data.review_count === 1 ? "review" : "reviews"})`
              : "Rating (no reviews yet)"
          }
        />
      </div>

      {data.refund_problems.length > 0 && (
        <div className="mb-8 rounded-[18px] border border-error/40 px-5 py-4" role="status">
          <b>
            {data.refund_problems.length === 1 ? "1 refund is" : `${data.refund_problems.length} refunds are`} delayed
          </b>
          <ul className="mt-1 text-[15px] text-muted">
            {data.refund_problems.map((r) => (
              <li key={r.seller_order_id}>
                {formatINR(r.amount)} for order #{r.order_id}. HomeHaat is retrying it automatically.
              </li>
            ))}
          </ul>
        </div>
      )}

      {data.open_requests > 0 && (
        <Link
          href="/seller/requests"
          className="mb-8 flex flex-wrap items-center justify-between gap-3 rounded-[18px] border border-line px-5 py-4 no-underline hover:border-ink"
        >
          <span>
            <b>
              {data.open_requests} custom {data.open_requests === 1 ? "request is" : "requests are"} waiting for your price
            </b>
          </span>
          <span className="font-medium underline underline-offset-4">Reply</span>
        </Link>
      )}

      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <h3 className="text-[24px]">Incoming orders</h3>
        {data.incoming.length > 0 && <Link href="/seller/orders">See all orders</Link>}
      </div>
      {data.incoming.length === 0 ? (
        <EmptyState
          photoId={PHOTOS.pickles}
          title="No orders yet"
          text={
            data.products_listed
              ? "When someone buys from your shop and pays, the order appears here with their address."
              : "Add your first product so buyers can find you."
          }
          action={
            data.products_listed ? undefined : (
              <Link href="/seller/products/new" className="btn btn-black">
                Add your first product
              </Link>
            )
          }
        />
      ) : (
        <div className="flex flex-col gap-3.5">
          {data.incoming.map((order) => (
            <IncomingOrderCard
              key={order.id}
              order={order}
              onChange={() => {
                setAttempt((n) => n + 1); // reload: the numbers above change too
                refresh(); // and the "Shop orders" count in the tabs and menu
              }}
            />
          ))}
        </div>
      )}
    </>
  );
}
