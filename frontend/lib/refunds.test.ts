import assert from "node:assert/strict";
import { test } from "node:test";

import { refundText } from "./refunds.ts";

test("buyer sees what is happening to their money", () => {
  assert.equal(refundText({ amount: 74000, status: "pending" }, "buyer"), "Refund of ₹740 started. It usually takes 5–7 days to reach you.");
  assert.equal(
    refundText({ amount: 74000, status: "processed" }, "buyer"),
    "Refund of ₹740 sent. It can take a few days to show in your account.",
  );
  assert.equal(
    refundText({ amount: 74000, status: "failed" }, "buyer"),
    "Refund of ₹740 is delayed. HomeHaat is retrying it automatically.",
  );
});

test("seller sees the same facts about the buyer's refund", () => {
  assert.equal(refundText({ amount: 33050, status: "pending" }, "seller"), "Refund of ₹330.50 to the buyer started (usually 5–7 days).");
  assert.equal(refundText({ amount: 33050, status: "processed" }, "seller"), "Refund of ₹330.50 to the buyer sent.");
  assert.equal(
    refundText({ amount: 33050, status: "failed" }, "seller"),
    "Refund of ₹330.50 to the buyer is delayed. HomeHaat is retrying it automatically.",
  );
});
