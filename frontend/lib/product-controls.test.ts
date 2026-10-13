import assert from "node:assert/strict";
import { test } from "node:test";

import { deleteText, productStatus } from "./product-controls.ts";

test("status pill: hidden beats out of stock, then live", () => {
  assert.equal(productStatus({ is_active: false, stock: 0 }).label, "Hidden");
  assert.equal(productStatus({ is_active: false, stock: 5 }).label, "Hidden");
  assert.equal(productStatus({ is_active: true, stock: 0 }).label, "Out of stock");
  assert.equal(productStatus({ is_active: true, stock: 3 }).label, "Live");
});

test("delete wording says what will happen", () => {
  assert.match(deleteText(0), /deleted completely/);
  assert.equal(
    deleteText(1),
    "It's in 1 past order, so we'll remove it from your shop and search but keep it in that order's history. This can't be undone.",
  );
  assert.match(deleteText(3), /^It's in 3 past orders, .* those orders' history\. This can't be undone\.$/);
});
