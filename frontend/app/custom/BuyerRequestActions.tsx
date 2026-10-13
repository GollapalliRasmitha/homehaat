"use client";

import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/ConfirmDialog";
import { errorMessage } from "@/lib/api/client";
import { acceptQuote, addQuoteToBag, declineQuote } from "@/lib/api/requests";
import type { CustomRequest } from "@/lib/api/types";
import { useSession } from "@/lib/session";

/** The buyer's buttons under a request: what they can do depends on its status. */
export function BuyerRequestActions({ request: r, onChange }: { request: CustomRequest; onChange: (r: CustomRequest) => void }) {
  const { refresh } = useSession();
  const [busy, setBusy] = useState(false);

  async function run(action: () => Promise<CustomRequest>, message: string) {
    setBusy(true);
    try {
      onChange(await action());
      await refresh(); // the bag count in the header
      toast(message);
    } catch (error) {
      toast(`Couldn't do that. ${errorMessage(error)}`);
    } finally {
      setBusy(false);
    }
  }

  if (r.status === "open") return <p className="text-sm text-muted">Waiting for the maker&apos;s price.</p>;
  if (r.status === "declined") return <p className="text-sm text-muted">This request is closed.</p>;
  if (r.status === "accepted") {
    if (r.ordered) return <p className="text-sm text-muted">Accepted and in an order. See My orders for its progress.</p>;
    return (
      <div className="flex flex-wrap items-center gap-2.5">
        {r.in_bag ? (
          <Link href="/cart" className="btn btn-black">
            In your bag: check out
          </Link>
        ) : (
          <button className="btn btn-black" disabled={busy} onClick={() => run(() => addQuoteToBag(r.id), "Added to your bag")}>
            Add to bag again
          </button>
        )}
      </div>
    );
  }
  // quoted
  return (
    <div className="flex flex-wrap gap-2.5">
      <button className="btn btn-black" disabled={busy} onClick={() => run(() => acceptQuote(r.id), "Quote accepted and added to your bag")}>
        {busy ? "Saving…" : "Accept and add to bag"}
      </button>
      <ConfirmDialog
        trigger={
          <button className="btn btn-white" disabled={busy}>
            Decline
          </button>
        }
        title="Decline this price?"
        text="The request will be closed. You can always send the maker a new request."
        confirmLabel="Yes, decline"
        cancelLabel="Keep it"
        onConfirm={() => run(() => declineQuote(r.id), "Quote declined")}
      />
    </div>
  );
}
