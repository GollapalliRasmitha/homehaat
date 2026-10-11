import type { Cart } from "./api/types";

/**
 * The bag as it will look after changing one line's quantity, for an instant ("optimistic") update.
 * Integer paise only. The server's answer replaces this a moment later, so the server stays the source of truth.
 */
export function withQty(cart: Cart, productId: number, qty: number): Cart {
  const groups = cart.groups.map((group) => {
    const items = group.items.map((line) =>
      line.product.id === productId ? { ...line, qty, line_total: line.product.price_paise * qty } : line,
    );
    const items_total = items.reduce((sum, line) => sum + line.line_total, 0);
    return { ...group, items, items_total, subtotal: items_total + group.delivery_fee };
  });
  const items_total = groups.reduce((sum, g) => sum + g.items_total, 0);
  const delivery_total = groups.reduce((sum, g) => sum + g.delivery_fee, 0);
  return {
    ...cart,
    groups,
    count: groups.reduce((sum, g) => sum + g.items.reduce((s, line) => s + line.qty, 0), 0),
    items_total,
    delivery_total,
    grand_total: items_total + delivery_total,
  };
}
