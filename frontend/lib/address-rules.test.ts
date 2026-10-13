import assert from "node:assert/strict";
import { test } from "node:test";

import { addressProblems, normalizePhone } from "./address-rules.ts";

const GOOD = { name: "Asha Rao", phone: "9876543210", line1: "12 MG Road", line2: "", city: "Bengaluru", pincode: "560001" };

test("a good address has no problems", () => {
  assert.deepEqual(addressProblems(GOOD), {});
});

test("pincode: 6 digits, not starting with 0", () => {
  for (const bad of ["56000", "5600011", "060001", "abcdef", ""]) assert.ok(addressProblems({ ...GOOD, pincode: bad }).pincode, bad);
  assert.deepEqual(addressProblems({ ...GOOD, pincode: "110001" }), {});
});

test("phone: Indian mobile starting 6-9, typed in common ways", () => {
  for (const bad of ["5876543210", "987654321", "98765abcde", "9999999999", ""]) {
    assert.ok(addressProblems({ ...GOOD, phone: bad }).phone, bad);
  }
  for (const typed of ["+91 98765 43210", "098765-43210", "91 9876543210"]) assert.equal(normalizePhone(typed), "9876543210");
  assert.deepEqual(addressProblems({ ...GOOD, phone: "+91 70123 45678" }), {});
});

test("address line and city need real letters, in any script", () => {
  for (const bad of ["!!!", "12/34", "#@*", "ab"]) assert.ok(addressProblems({ ...GOOD, line1: bad }).line1, bad);
  for (const bad of ["???", "123", "x"]) assert.ok(addressProblems({ ...GOOD, city: bad }).city, bad);
  assert.deepEqual(addressProblems({ ...GOOD, city: "बेंगलुरु", line1: "Flat 4B, 2nd Cross" }), {});
  assert.ok(addressProblems({ ...GOOD, line2: "%%%" }).line2);
  assert.ok(addressProblems({ ...GOOD, name: "@@" }).name);
});
