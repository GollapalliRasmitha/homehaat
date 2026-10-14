"use client";

import { useState } from "react";
import { toast } from "sonner";

import { errorMessage } from "@/lib/api/client";
import { cancelPart, requestCancel } from "@/lib/api/orders";
import type { Order, SellerOrder } from "@/lib/api/types";
import { formatINR } from "@/lib/format";
import { refundText } from "@/lib/refunds";

import { ConfirmDialog } from "./ConfirmDialog";

/**
 * The buyer's cancel controls and refund status for ONE maker's part of an order.
 * New: Cancel (at once). Preparing: Ask to cancel (the maker decides). After that: nothing, just the status.
 * The server checks every rule again (orders/cancel.py) and works out the refund amount itself.
 */
export function PartCancel({ part, onOrder }: { part: SellerOrder; onOrder: (o: Order) => void }) {
  const [busy, setBusy] = useState(false);
  const back = formatINR(part.subtotal + part.delivery_fee);

  async function run(action: () => Promise<Order>, done: (o: Order) => string) {
    setBusy(true);
    try {
      const order = await action();
      onOrder(order);
      toast(done(order));
    } catch (error) {
      toast(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  if (part.status === "cancelled") {
    const who =
      part.cancelled_by === "buyer"
        ? "You cancelled this part of your order."
        : part.cancelled_by === "system"
          ? "This maker couldn't fill this part of your order."
          : "The maker cancelled this part of your order.";
    return (
      <div className="my-3 rounded-[14px] bg-soft px-3.5 py-3 text-[15px]" role="status">
        <p className="font-semibold">{who}</p>
        {part.refund && <p className="text-muted">{refundText(part.refund, "buyer")}</p>}
      </div>
    );
  }

  return (
    <>
      {part.cancel_requested && (
        <p className="my-3 rounded-[14px] bg-soft px-3.5 py-3 text-[15px]" role="status">
          You asked the maker to cancel. <span className="text-muted">Waiting for their answer.</span>
        </p>
      )}
      {part.cancel_declined && (
        <p className="my-3 rounded-[14px] bg-soft px-3.5 py-3 text-[15px]" role="status">
          The maker can&apos;t cancel this one now. <span className="text-muted">They&apos;ve already started making it.</span>
        </p>
      )}
      {(part.can_cancel || part.can_request_cancel) && (
        <div className="mt-3">
          {part.can_cancel ? (
            <ConfirmDialog
              trigger={
                <button className="btn btn-white w-full sm:w-auto" disabled={busy}>
                  Cancel this part
                </button>
              }
              title={`Cancel your order from ${part.seller.name}?`}
              text={`You'll get ${back} back (the items and this maker's delivery fee). Your other makers' parts aren't affected. This can't be undone.`}
              confirmLabel="Yes, cancel it"
              onConfirm={() =>
                run(
                  () => cancelPart(part.id),
                  (o) => {
                    // Say what really happened to the refund (started, sent or delayed), not what we hope.
                    const refund = o.seller_orders.find((p) => p.id === part.id)?.refund;
                    return refund ? `Cancelled. ${refundText(refund, "buyer")}` : "Cancelled.";
                  },
                )
              }
            />
          ) : (
            <ConfirmDialog
              trigger={
                <button className="btn btn-white w-full sm:w-auto" disabled={busy}>
                  Ask to cancel
                </button>
              }
              title={`Ask ${part.seller.name} to cancel?`}
              text={`They've started preparing it, so they decide. If they agree, you'll get ${back} back.`}
              confirmLabel="Ask to cancel"
              onConfirm={() => run(() => requestCancel(part.id), () => "We've asked the maker")}
            />
          )}
        </div>
      )}
    </>
  );
}
