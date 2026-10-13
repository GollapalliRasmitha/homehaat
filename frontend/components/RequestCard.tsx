import type { CustomRequest, RequestStatus } from "@/lib/api/types";
import { formatDay, formatINR } from "@/lib/format";

import { SafeImg } from "./SafeImage";

const STATUS: Record<RequestStatus, { label: string; pill: string }> = {
  open: { label: "Open", pill: "st-new" },
  quoted: { label: "Quoted", pill: "st-preparing" },
  accepted: { label: "Accepted", pill: "st-delivered" },
  declined: { label: "Declined", pill: "st-cancelled" },
};

/** One custom request. `who` = whose page it's on; `children` = the buttons/forms for that side. */
export function RequestCard({
  request: r,
  who,
  children,
}: {
  request: CustomRequest;
  who: "buyer" | "seller";
  children?: React.ReactNode;
}) {
  const facts = [
    r.needed_by ? `Needed by ${formatDay(r.needed_by)}` : "No date given",
    r.budget_paise !== null ? `Budget ${formatINR(r.budget_paise)}` : "No budget given",
  ];
  return (
    <article className="panel flex flex-col gap-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <b className="text-lg">{who === "buyer" ? r.seller.name : `From ${r.buyer_name}`}</b>
          <div className="text-sm text-muted">
            Sent {new Date(r.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })} · {facts.join(" · ")}
          </div>
        </div>
        <span className={`status ${STATUS[r.status].pill}`}>{STATUS[r.status].label}</span>
      </div>

      <p className="whitespace-pre-line">{r.description}</p>

      {r.images.length > 0 && (
        <div className="flex flex-wrap gap-2.5" aria-label="Reference photos">
          {r.images.map((url, i) => (
            <a key={url} href={url} target="_blank" rel="noreferrer" className="block size-[88px] overflow-hidden rounded-[14px] bg-soft">
              <SafeImg src={url} alt={`Reference photo ${i + 1}`} className="size-full object-cover" />
            </a>
          ))}
        </div>
      )}

      {r.quote_paise !== null && (
        <div className="rounded-[14px] bg-soft px-3.5 py-3">
          <span className="text-sm text-muted">{who === "buyer" ? "The maker's price" : "Your quote"}</span>
          <div className="price text-[22px]">{formatINR(r.quote_paise)}</div>
          {r.seller_note && <p className="mt-1 text-[15px]">{r.seller_note}</p>}
          <p className="mt-1 text-[13px] text-muted">+ {formatINR(r.seller.delivery_fee_paise)} delivery at checkout</p>
        </div>
      )}

      {children}
    </article>
  );
}

export const REQUEST_STATUS = STATUS;
