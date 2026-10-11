import assert from "node:assert/strict";
import { test } from "node:test";

import { fitWithin } from "./compress-image.ts";

test("big photos shrink to fit 1600 px, keeping their shape", () => {
  assert.deepEqual(fitWithin(4000, 3000), { width: 1600, height: 1200 });
  assert.deepEqual(fitWithin(3000, 4000), { width: 1200, height: 1600 });
});

test("small photos are never enlarged", () => {
  assert.deepEqual(fitWithin(800, 600), { width: 800, height: 600 });
});
