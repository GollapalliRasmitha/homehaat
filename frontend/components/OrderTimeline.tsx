import type { SellerOrderStatus } from "@/lib/api/types";
import { STATUS_LABEL } from "@/lib/status";

const STEPS: SellerOrderStatus[] = ["new", "preparing", "out_for_delivery", "delivered"];

/** UI-UX.md: one status timeline per maker, 4 bars that turn black as the order moves on. */
export function OrderTimeline({ status }: { status: SellerOrderStatus }) {
  if (status === "cancelled") return null;
  const reached = STEPS.indexOf(status);
  return (
    <ol className="my-4 grid grid-cols-4 gap-2" aria-label={`Order status: ${STATUS_LABEL[status]}`}>
      {STEPS.map((step, i) => {
        const done = i <= reached;
        return (
          <li key={step} className={`flex flex-col gap-1.5 text-[13px] ${done ? "font-semibold text-ink" : "text-muted"}`}>
            <span className={`h-1 rounded-full ${done ? "bg-ink" : "bg-line"}`} aria-hidden="true" />
            {STATUS_LABEL[step]}
            {i === reached && <span className="sr-only">(current step)</span>}
          </li>
        );
      })}
    </ol>
  );
}
