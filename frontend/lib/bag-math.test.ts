import assert from "node:assert/strict";
import { test } from "node:test";

import type { Cart } from "./api/types.ts";
import { withQty } from "./bag-math.ts";

const line = (id: number, price: number, qty: number) =>
  ({ id, qty, note: "", problem: null, line_total: price * qty, product: { id, price_paise: price } }) as Cart["groups"][0]["items"][0];

const cart: Cart = {
  groups: [
    { seller: {} as never, items: [line(1, 45000, 1), line(2, 5000, 2)], items_total: 55000, delivery_fee: 4000, subtotal: 59000 },
    { seller: {} as never, items: [line(3, 12000, 1)], items_total: 12000, delivery_fee: 3000, subtotal: 15000 },
  ],
  count: 4,
  items_total: 67000,
  delivery_total: 7000,
  grand_total: 74000,
  has_problems: false,
};

test("withQty updates the line, its seller group and the totals in paise", () => {
  const next = withQty(cart, 1, 3);
  assert.equal(next.groups[0].items[0].line_total, 135000);
  assert.equal(next.groups[0].items_total, 145000);
  assert.equal(next.groups[0].subtotal, 149000);
  assert.equal(next.groups[1].items_total, 12000); // the other seller's group is unchanged
  assert.equal(next.count, 6);
  assert.equal(next.grand_total, 145000 + 12000 + 7000);
});

test("withQty does not change the original bag", () => {
  withQty(cart, 1, 3);
  assert.equal(cart.groups[0].items[0].qty, 1);
  assert.equal(cart.grand_total, 74000);
});
