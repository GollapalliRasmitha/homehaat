/** Pure helpers for the seller's Products tab (unit-tested in product-controls.test.ts). */

/** What buyers see: Hidden (switched off), Out of stock (stock 0) or Live. */
export function productStatus(p: { is_active: boolean; stock: number }) {
  if (!p.is_active) return { label: "Hidden", className: "st-cancelled" };
  if (p.stock === 0) return { label: "Out of stock", className: "st-preparing" };
  return { label: "Live", className: "st-delivered" };
}

/** The Delete confirmation: archived (kept in order history) if it was ever ordered, otherwise deleted. */
export function deleteText(pastOrders: number) {
  if (pastOrders === 0) {
    return "It has never been ordered, so it will be deleted completely, with its photos. This can't be undone.";
  }
  const orders = pastOrders === 1 ? "1 past order" : `${pastOrders} past orders`;
  const history = pastOrders === 1 ? "that order's history" : "those orders' history";
  return `It's in ${orders}, so we'll remove it from your shop and search but keep it in ${history}. This can't be undone.`;
}
