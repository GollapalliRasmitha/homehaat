"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { getOrder } from "@/lib/api/orders";
import type { Order } from "@/lib/api/types";
import { formatINR } from "@/lib/format";
import { PHOTOS } from "@/lib/photos";
import { STATUS_LABEL } from "@/lib/status";

// Stage 1: the order success page. The full order history and timeline are Stage 2.
export default function OrderPage() {
  const { id } = useParams<{ id: string }>();
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
  return (
    <div className="mx-auto flex max-w-[820px] flex-col gap-4">
      {order.payment_status === "paid" ? (
        <EmptyState
          photoId={PHOTOS.crafts}
          title="Order placed"
          text={`Payment of ${formatINR(order.grand_total)} confirmed. Your order was split into ${parts} ${
            parts === 1 ? "order" : "orders"
          }, one for each maker.`}
        />
      ) : (
        <div className="panel">
          <h1 className="title text-[32px]">Order #{order.id}</h1>
          <p className="text-muted">
            {order.payment_status === "pending" ? "Waiting for payment confirmation." : "This order wasn't paid. You haven't been charged."}
          </p>
        </div>
      )}

      {order.seller_orders.map((part) => (
        <section key={part.id} className="panel">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3.5">
            <b className="text-lg">{part.seller.name}</b>
            <span className={`status st-${part.status}`}>{STATUS_LABEL[part.status]}</span>
          </div>
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
        </section>
      ))}

      <p className="text-sm text-muted">
        Delivering to {order.ship_to.name}, {order.ship_to.line1}, {order.ship_to.city} {order.ship_to.pincode}
      </p>
      <Link href="/" className="btn btn-white self-start">
        Keep exploring
      </Link>
    </div>
  );
}
