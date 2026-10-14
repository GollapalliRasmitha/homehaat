"use client";

import { useState } from "react";
import { toast } from "sonner";

import { errorMessage } from "@/lib/api/client";
import { answerCancelRequest, changeOrderStatus } from "@/lib/api/seller";
import type { IncomingOrder, SellerOrderStatus } from "@/lib/api/types";
import { formatINR } from "@/lib/format";
import { refundText } from "@/lib/refunds";
import { STATUS_LABEL } from "@/lib/status";

import { ConfirmDialog } from "./ConfirmDialog";
import { OrderItemThumb } from "./ItemThumb";

/** The one next step for each status, and its button label. Delivered/cancelled have none. */
export const NEXT_STEP: Partial<Record<SellerOrderStatus, { status: SellerOrderStatus; label: string }>> = {
  new: { status: "preparing", label: "Start preparing" },
  preparing: { status: "out_for_delivery", label: "Mark out for delivery" },
  out_for_delivery: { status: "delivered", label: "Mark delivered" },
};
const CAN_CANCEL: SellerOrderStatus[] = ["new", "preparing"];

const when = (iso: string) => new Date(iso).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });

export function IncomingOrderCard({ order, onChange }: { order: IncomingOrder; onChange: (o: IncomingOrder) => void }) {
  const [busy, setBusy] = useState(false);
  const next = NEXT_STEP[order.status];

  async function answer(accept: boolean) {
    setBusy(true);
    try {
      const updated = await answerCancelRequest(order.id, accept);
      onChange(updated);
      toast(accept ? `Cancelled. ${updated.refund ? refundText(updated.refund, "seller") : ""}` : "Declined. Keep preparing it.");
    } catch (error) {
      toast(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function move(status: SellerOrderStatus) {
    setBusy(true);
    try {
      const updated = await changeOrderStatus(order.id, status); // the server checks the move is allowed
      onChange(updated);
      toast(`Order #${order.order_id}: ${STATUS_LABEL[updated.status]}`);
    } catch (error) {
      toast(`Couldn't update the order. ${errorMessage(error)}`);
    } finally {
      setBusy(false);
    }
  }

  const a = order.ship_to;
  return (
    <article className="panel">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line pb-3.5">
        <div>
          <b className="text-lg">Order #{order.order_id}</b>
          <div className="text-sm text-muted">Paid {when(order.paid_at)}</div>
        </div>
        <span className={`status st-${order.status}`}>{STATUS_LABEL[order.status]}</span>
      </div>

      <div className="mt-3 text-[15px]">
        <span className="font-semibold">{a.name}</span> · <a href={`tel:${a.phone}`}>{a.phone}</a>
        <div className="text-muted">
          {a.line1}
          {a.line2 && `, ${a.line2}`}, {a.city} {a.pincode}
        </div>
      </div>

      <div className="mt-3">
        {order.items.map((item) => (
          <div key={item.id} className="mt-2.5 flex items-center gap-3 text-[15px]">
            <OrderItemThumb item={item} />
            <span className="min-w-0 flex-1">
              {item.qty} × {item.name}
              {item.note && <span className="block text-sm text-muted">Note: {item.note}</span>}
            </span>
            <span className="price">{formatINR(item.line_total)}</span>
          </div>
        ))}
        <div className="mt-1.5 flex justify-between text-[15px] text-muted">
          <span>Delivery fee</span>
          <span>{formatINR(order.delivery_fee)}</span>
        </div>
        <div className="mt-1 flex justify-between font-semibold">
          <span>{order.status === "cancelled" ? "Order total" : "You receive"}</span>
          <span className="price">{formatINR(order.subtotal + order.delivery_fee)}</span>
        </div>
      </div>

      {order.status === "cancelled" && (
        <p className="mt-3 rounded-[14px] bg-soft px-3.5 py-3 text-sm" role="status">
          <b>
            {order.cancelled_by === "buyer"
              ? "The buyer cancelled this order."
              : order.cancelled_by === "system"
                ? "Cancelled: the items had sold out before the payment arrived."
                : "You cancelled this order."}
          </b>{" "}
          {order.refund ? refundText(order.refund, "seller") : null} (Test mode: no real money moves.)
        </p>
      )}

      {order.cancel_requested && (
        <div className="mt-3 rounded-[14px] border border-ink px-3.5 py-3" role="status">
          <p className="text-[15px]">
            <b>The buyer asked to cancel this order.</b>{" "}
            <span className="text-muted">
              If you accept, they get {formatINR(order.subtotal + order.delivery_fee)} back and the items go back into
              your stock.
            </span>
          </p>
          <div className="mt-2.5 flex flex-col gap-2.5 sm:flex-row">
            <ConfirmDialog
              trigger={
                <button className="btn btn-black w-full sm:w-auto" disabled={busy}>
                  Accept and refund
                </button>
              }
              title={`Cancel order #${order.order_id} and refund the buyer?`}
              text={`The buyer gets ${formatINR(order.subtotal + order.delivery_fee)} back. This can't be undone.`}
              confirmLabel="Yes, cancel and refund"
              onConfirm={() => answer(true)}
            />
            <button className="btn btn-white w-full sm:w-auto" disabled={busy} onClick={() => answer(false)}>
              Decline, I&apos;ll make it
            </button>
          </div>
        </div>
      )}

      {(next || CAN_CANCEL.includes(order.status)) && (
        // Phones: each button is full width, so it's easy to tap. From 640px they sit side by side.
        <div className="mt-4 flex flex-col gap-2.5 sm:flex-row sm:flex-wrap">
          {next && (
            <button className="btn btn-black w-full sm:w-auto" onClick={() => move(next.status)} disabled={busy}>
              {busy ? "Saving…" : next.label}
            </button>
          )}
          {CAN_CANCEL.includes(order.status) && (
            <ConfirmDialog
              trigger={
                <button className="btn btn-white w-full sm:w-auto" disabled={busy}>
                  Cancel order
                </button>
              }
              title={`Cancel order #${order.order_id}?`}
              text={`The buyer gets ${formatINR(order.subtotal + order.delivery_fee)} back automatically, and the items go back into your stock. This can't be undone.`}
              confirmLabel="Yes, cancel it"
              onConfirm={() => move("cancelled")}
            />
          )}
        </div>
      )}
    </article>
  );
}
