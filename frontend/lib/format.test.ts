// Run with: npm test  (uses Node's built-in test runner, no extra tools)
import assert from "node:assert/strict";
import { test } from "node:test";

import { formatINR, rupeesToPaise } from "./format.ts";

test("formatINR shows whole rupees without decimals", () => {
  assert.equal(formatINR(45000), "₹450");
  assert.equal(formatINR(0), "₹0");
  assert.equal(formatINR(106000), "₹1,060");
});

test("formatINR uses Indian digit grouping", () => {
  assert.equal(formatINR(10000000), "₹1,00,000");
  assert.equal(formatINR(1234567800), "₹1,23,45,678");
});

test("formatINR shows paise when there are any", () => {
  assert.equal(formatINR(4550), "₹45.50");
  assert.equal(formatINR(4505), "₹45.05");
  assert.equal(formatINR(1), "₹0.01");
});

test("formatINR refuses floats", () => {
  assert.throws(() => formatINR(450.5));
});

test("rupeesToPaise converts typed amounts exactly", () => {
  assert.equal(rupeesToPaise("450"), 45000);
  assert.equal(rupeesToPaise("450.5"), 45050);
  assert.equal(rupeesToPaise("0.10"), 10);
  assert.equal(rupeesToPaise("₹1,200.75"), 120075);
  assert.equal(rupeesToPaise(" 40 "), 4000);
});

test("rupeesToPaise rejects nonsense", () => {
  for (const bad of ["", "abc", "-5", "1.234", "1e3", "12.", "."]) {
    assert.equal(rupeesToPaise(bad), null, bad);
  }
});
