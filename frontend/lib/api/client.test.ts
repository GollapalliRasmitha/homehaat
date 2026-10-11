import assert from "node:assert/strict";
import { test } from "node:test";

import { ApiError, errorMessage, friendlyMessage } from "./client.ts";

test("uses Django's own message when there is one", () => {
  assert.equal(friendlyMessage(400, { detail: "Your bag is empty." }), "Your bag is empty.");
});

test("explains a missing connection or a server crash in plain words", () => {
  assert.match(friendlyMessage(0, {}), /Can't reach HomeHaat/);
  assert.match(friendlyMessage(500, {}), /server had a problem/);
  assert.match(friendlyMessage(502, {}), /server had a problem/);
});

test("shows the first form error instead of a vague message", () => {
  assert.equal(friendlyMessage(400, { name: ["Ensure this field has no more than 80 characters."] }), "Ensure this field has no more than 80 characters.");
});

test("falls back to a general message", () => {
  assert.equal(friendlyMessage(418, {}), "Something went wrong. Please try again.");
  assert.match(friendlyMessage(404, {}), /couldn't find/);
  assert.match(friendlyMessage(429, {}), /Too many tries/);
});

test("errorMessage never leaks technical text from unexpected errors", () => {
  assert.equal(errorMessage(new ApiError(500, {})), "Our server had a problem. Please try again in a moment.");
  assert.equal(errorMessage(new TypeError("Cannot read properties of undefined")), "Something went wrong. Please try again.");
});
