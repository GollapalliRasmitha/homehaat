import assert from "node:assert/strict";
import { test } from "node:test";

import { addLine, countLines, removeLines, setLineQty } from "./guest-bag.ts";

test("addLine adds a new product", () => {
  const { lines, added } = addLine([], 7, 2, "Eggless", 5);
  assert.deepEqual(lines, [{ product_id: 7, qty: 2, note: "Eggless" }]);
  assert.equal(added, 2);
});

test("addLine adds to an existing line and keeps the old note if none is given", () => {
  const { lines } = addLine([{ product_id: 7, qty: 1, note: "Eggless" }], 7, 2, "", 5);
  assert.deepEqual(lines, [{ product_id: 7, qty: 3, note: "Eggless" }]);
});

test("addLine never goes above the stock", () => {
  const { lines, added } = addLine([{ product_id: 7, qty: 4, note: "" }], 7, 3, "", 5);
  assert.equal(lines[0].qty, 5);
  assert.equal(added, 1); // only one more fitted
});

test("addLine does nothing for a sold-out product", () => {
  const { lines, added } = addLine([], 7, 1, "", 0);
  assert.deepEqual(lines, []);
  assert.equal(added, 0);
});

test("setLineQty keeps quantities between 1 and 50", () => {
  const lines = [{ product_id: 7, qty: 2, note: "" }];
  assert.equal(setLineQty(lines, 7, 0)[0].qty, 1);
  assert.equal(setLineQty(lines, 7, 99)[0].qty, 50);
});

test("removeLines and countLines", () => {
  const lines = [
    { product_id: 1, qty: 2, note: "" },
    { product_id: 2, qty: 3, note: "" },
  ];
  assert.equal(countLines(lines), 5);
  assert.deepEqual(removeLines(lines, [1]), [{ product_id: 2, qty: 3, note: "" }]);
});
