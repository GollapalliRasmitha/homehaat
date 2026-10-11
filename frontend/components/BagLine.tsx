import type { CartLine } from "@/lib/api/types";
import { formatINR } from "@/lib/format";

import { ProductImage } from "./ProductImage";

/** What to tell the buyer about a line that can't be bought as it is. */
export function problemText(line: CartLine): string | null {
  switch (line.problem) {
    case "sold_out":
      return "Sold out";
    case "not_enough":
      return `Only ${line.product.stock} left`;
    case "unavailable":
      return "No longer available";
    default:
      return null;
  }
}

export function BagLine({
  line,
  onQty,
  onRemove,
}: {
  line: CartLine;
  onQty: (qty: number) => void;
  onRemove: () => void;
}) {
  const problem = problemText(line);
  const max = Math.min(line.product.stock, 50);
  return (
    <div className="flex flex-wrap items-center gap-4 border-b border-line py-4 last:border-0">
      <ProductImage product={line.product} className="size-[84px] flex-none rounded-2xl" />
      <div className="min-w-0 flex-[1_1_180px]">
        <div className="font-bold">{line.product.name}</div>
        <div className="text-sm text-muted">{formatINR(line.product.price_paise)} each</div>
        {line.note && <div className="text-sm text-muted">Note: {line.note}</div>}
        {problem && <div className="mt-1 text-sm font-semibold text-error">{problem}</div>}
        <button className="py-2 text-sm text-muted underline" onClick={onRemove}>
          Remove
        </button>
      </div>
      <div className="inline-flex h-[46px] items-center rounded-full border border-line">
        <button
          className="h-11 w-[46px] rounded-full text-xl hover:bg-soft disabled:opacity-30"
          aria-label={`Decrease quantity of ${line.product.name}`}
          disabled={line.qty <= 1}
          onClick={() => onQty(line.qty - 1)}
        >
          −
        </button>
        <span className="min-w-7 text-center font-semibold tabular-nums">{line.qty}</span>
        <button
          className="h-11 w-[46px] rounded-full text-xl hover:bg-soft disabled:opacity-30"
          aria-label={`Increase quantity of ${line.product.name}`}
          disabled={line.qty >= max}
          onClick={() => onQty(line.qty + 1)}
        >
          +
        </button>
      </div>
      <span className="price min-w-[90px] text-right">{formatINR(line.line_total)}</span>
    </div>
  );
}
