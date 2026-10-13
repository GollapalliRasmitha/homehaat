"use client";

import { useEffect, useId, useState } from "react";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/ConfirmDialog";
import { EmptyState } from "@/components/EmptyState";
import { LoadError } from "@/components/LoadError";
import { REQUEST_STATUS, RequestCard } from "@/components/RequestCard";
import { errorMessage } from "@/lib/api/client";
import { declineRequest, listShopRequests, sendQuote } from "@/lib/api/requests";
import type { CustomRequest, RequestStatus } from "@/lib/api/types";
import { rupeesToPaise } from "@/lib/format";
import { PHOTOS } from "@/lib/photos";

const FILTERS: (RequestStatus | "all")[] = ["all", "open", "quoted", "accepted", "declined"];

export default function SellerRequestsPage() {
  const [requests, setRequests] = useState<CustomRequest[] | null>(null);
  const [filter, setFilter] = useState<RequestStatus | "all">("all");
  const [loadError, setLoadError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    listShopRequests()
      .then(setRequests)
      .catch(setLoadError);
  }, [attempt]);

  if (loadError) {
    const retry = () => {
      setLoadError(null);
      setAttempt((n) => n + 1);
    };
    return <LoadError error={loadError} onRetry={retry} title="Couldn't load your requests" />;
  }
  if (!requests) return <p className="text-muted">Loading…</p>;
  if (requests.length === 0) {
    return (
      <EmptyState
        photoId={PHOTOS.crafts}
        title="No custom requests yet"
        text="Buyers can ask you to make something special from your shop page. You'll reply with a price here."
      />
    );
  }

  const count = (f: RequestStatus | "all") => (f === "all" ? requests.length : requests.filter((r) => r.status === f).length);
  const shown = filter === "all" ? requests : requests.filter((r) => r.status === filter);
  const replace = (r: CustomRequest) => setRequests(requests.map((x) => (x.id === r.id ? r : x)));

  return (
    <>
      <div className="no-scrollbar -mx-4 mb-6 flex gap-2.5 overflow-x-auto px-4 sm:mx-0 sm:flex-wrap sm:px-0" role="group" aria-label="Show requests">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            aria-pressed={filter === f}
            className={`h-[42px] whitespace-nowrap rounded-full border px-[18px] text-[15px] font-medium ${
              filter === f ? "border-ink bg-ink text-white" : "border-line bg-white hover:border-ink"
            }`}
          >
            {f === "all" ? "All" : REQUEST_STATUS[f].label} ({count(f)})
          </button>
        ))}
      </div>
      {shown.length === 0 ? (
        <p className="rounded-[24px] bg-soft px-5 py-8 text-center text-muted">Nothing here. Choose another filter.</p>
      ) : (
        <div className="flex flex-col gap-3.5">
          {shown.map((r) => (
            <RequestCard key={r.id} request={r} who="seller">
              <SellerActions request={r} onChange={replace} />
            </RequestCard>
          ))}
        </div>
      )}
    </>
  );
}

function SellerActions({ request: r, onChange }: { request: CustomRequest; onChange: (r: CustomRequest) => void }) {
  const id = useId();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (r.status === "quoted") return <p className="text-sm text-muted">Waiting for the buyer to accept or decline.</p>;
  if (r.status === "accepted")
    return (
      <p className="text-sm text-muted">
        {r.ordered ? "Accepted and ordered: you'll find it under Orders once it's paid." : "Accepted: the buyer is checking out."}
      </p>
    );
  if (r.status === "declined") return <p className="text-sm text-muted">Closed.</p>;

  async function run(action: () => Promise<CustomRequest>, message: string) {
    setBusy(true);
    try {
      onChange(await action());
      toast(message);
    } catch (e) {
      toast(`Couldn't do that. ${errorMessage(e)}`);
    } finally {
      setBusy(false);
    }
  }

  async function quote(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const f = new FormData(event.currentTarget);
    const price = rupeesToPaise(String(f.get("price") ?? ""));
    if (price === null || price < 100) return setError("Enter a price of ₹1 or more.");
    setError("");
    await run(() => sendQuote(r.id, price, String(f.get("note") ?? "").trim()), "Quote sent");
  }

  // open: the seller's turn
  return (
    <form onSubmit={quote} noValidate className="grid gap-3 border-t border-line pt-3.5 sm:grid-cols-[180px_1fr]">
      <div>
        <label className="field-label" htmlFor={`${id}-price`}>
          Your price (₹)
        </label>
        <input id={`${id}-price`} name="price" className="input" inputMode="decimal" aria-describedby={error ? `${id}-err` : undefined} />
        {error && (
          <p id={`${id}-err`} className="field-error">
            {error}
          </p>
        )}
      </div>
      <div>
        <label className="field-label" htmlFor={`${id}-note`}>
          Note (optional)
        </label>
        <input id={`${id}-note`} name="note" className="input" maxLength={300} placeholder="e.g. Includes the edible photo. Ready Saturday 4 pm." />
      </div>
      <div className="flex flex-wrap gap-2.5 sm:col-span-2">
        <button className="btn btn-black" disabled={busy}>
          {busy ? "Sending…" : "Send quote"}
        </button>
        <ConfirmDialog
          trigger={
            <button type="button" className="btn btn-white" disabled={busy}>
              Decline
            </button>
          }
          title="Decline this request?"
          text="The buyer will see that you can't make it. This can't be undone."
          confirmLabel="Yes, decline"
          cancelLabel="Keep it"
          onConfirm={() => run(() => declineRequest(r.id), "Request declined")}
        />
      </div>
    </form>
  );
}
