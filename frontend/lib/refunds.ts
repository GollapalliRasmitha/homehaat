/** Plain words for a refund's status, for the buyer's order page and the seller's order card (+ refunds.test.ts). */

import { formatINR } from "./format.ts"; // .ts extension: also loaded by Node's test runner

export interface RefundInfo {
  amount: number; // paise: that maker's items + their delivery fee, computed on the server
  status: "pending" | "processed" | "failed";
}

export function refundText(refund: RefundInfo, who: "buyer" | "seller"): string {
  const amount = formatINR(refund.amount);
  if (who === "buyer") {
    if (refund.status === "processed") return `Refund of ${amount} sent. It can take a few days to show in your account.`;
    if (refund.status === "failed") return `Refund of ${amount} is delayed. HomeHaat is retrying it automatically.`;
    return `Refund of ${amount} started. It usually takes 5–7 days to reach you.`;
  }
  if (refund.status === "processed") return `Refund of ${amount} to the buyer sent.`;
  if (refund.status === "failed") return `Refund of ${amount} to the buyer is delayed. HomeHaat is retrying it automatically.`;
  return `Refund of ${amount} to the buyer started (usually 5–7 days).`;
}
