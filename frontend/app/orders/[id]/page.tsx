"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { OrderTimeline } from "@/components/OrderTimeline";
import { getOrder } from "@/lib/api/orders";
import type { Order } from "@/lib/api/types";
import { formatINR } from "@/lib/format";
import { PHOTOS } from "@/lib/photos";
import { STATUS_LABEL } from "@/lib/status";

export default function OrderPage() {
  // Suspense is needed because the page reads ?placed=1 from the URL.
  return (
    <Suspense>
      <OrderDetail />
    </Suspense>
  );
}

function OrderDetail() {
  const { id } = useParams<{ id: string }>();
  const justPlaced = useSearchParams().get("placed") === "1"; // set by the "Confirming payment…" page
  const [order, setOrder] = useState<Order | null>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    getOrder(id)
      .then(setOrder)
      .catch(() => setMissing(true));
  }, [id]);

  if (missing) return <EmptyState title="Order not found" text="This order doesn't exist, or it isn't yours." />;
  if (!order) return <p className="text-muted">Loading your order…</p>;

  const parts = order.seller_orders.length;
  const paid = order.payment_status === "paid";
  return (
    <div className="mx-auto flex max-w-[900px] flex-col gap-4">
      <div className="text-sm text-muted">
        <Link href="/orders" className="text-muted">
          My orders
        </Link>{" "}
        / #{order.id}
      </div>

      {paid && justPlaced && (
        <EmptyState
          photoId={PHOTOS.crafts}
          title="Order placed"
          text={`Payment of ${formatINR(order.grand_total)} confirmed. Your order was split into ${parts} ${
            parts === 1 ? "order" : "orders"
          }, one for each maker.`}
        />
      )}

      <div>
        <h1 className="title">Order #{order.id}</h1>
        <p className="mt-1.5 text-muted">
          {paid
            ? `Paid ${formatINR(order.grand_total)} once · split into ${parts} maker ${parts === 1 ? "order" : "orders"}`
            : order.payment_status === "pending"
              ? "Waiting for payment confirmation."
              : "This order wasn't paid. You haven't been charged."}
          {" · "}delivering to {order.ship_to.name}, {order.ship_to.city}
        </p>
      </div>

      {order.seller_orders.map((part) => (
        <section key={part.id} className="panel">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3.5">
            <b className="text-lg">{part.seller.name}</b>
            {paid && <span className={`status st-${part.status}`}>{STATUS_LABEL[part.status]}</span>}
          </div>
          {paid && <OrderTimeline status={part.status} />}
          {part.status === "cancelled" && (
            <p className="my-3 text-muted">
              {part.refund_needed
                ? "This maker couldn't fill this part of your order. A refund of it is on its way."
                : "This part of your order was cancelled."}
            </p>
          )}
          {part.items.map((item) => (
            <div key={item.id} className="mt-2 flex justify-between text-[15px] text-muted">
              <span>
                {item.qty} × {item.name}
              </span>
              <span>{formatINR(item.line_total)}</span>
            </div>
          ))}
          <div className="mt-1 flex justify-between text-[15px] text-muted">
            <span>Delivery</span>
            <span>{formatINR(part.delivery_fee)}</span>
          </div>
          <div className="mt-1 flex justify-between text-[15px] font-semibold">
            <span>Subtotal</span>
            <span>{formatINR(part.subtotal + part.delivery_fee)}</span>
          </div>
        </section>
      ))}

      <p className="text-sm text-muted">
        Delivering to {order.ship_to.name}, {order.ship_to.line1}
        {order.ship_to.line2 && `, ${order.ship_to.line2}`}, {order.ship_to.city} {order.ship_to.pincode}
      </p>
      <Link href="/" className="btn btn-white self-start">
        Keep exploring
      </Link>
    </div>
  );
}
