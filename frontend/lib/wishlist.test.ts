import assert from "node:assert/strict";
import { test } from "node:test";

import { MAX_SAVED, toggleId } from "./wishlist.ts";

test("toggleId saves newest first and unsaves", () => {
  assert.deepEqual(toggleId([2, 1], 3), [3, 2, 1]);
  assert.deepEqual(toggleId([3, 2, 1], 2), [3, 1]);
});

test("toggleId keeps at most MAX_SAVED", () => {
  const full = Array.from({ length: MAX_SAVED }, (_, i) => i + 1);
  const next = toggleId(full, 999);
  assert.equal(next.length, MAX_SAVED);
  assert.equal(next[0], 999);
});
