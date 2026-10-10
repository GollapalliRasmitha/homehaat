import type { SellerOrderStatus } from "./api/types";

export const STATUS_LABEL: Record<SellerOrderStatus, string> = {
  new: "New",
  preparing: "Preparing",
  out_for_delivery: "Out for delivery",
  delivered: "Delivered",
  cancelled: "Cancelled",
};
