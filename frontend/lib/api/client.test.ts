import assert from "node:assert/strict";
import { test } from "node:test";

import { ApiError, errorMessage, friendlyMessage, RETRY_DELAYS_MS, shouldRetry } from "./client.ts";

test("uses Django's own message when there is one", () => {
  assert.equal(friendlyMessage(400, { detail: "Your bag is empty." }), "Your bag is empty.");
});

test("explains a missing connection or a server crash in plain words", () => {
  assert.match(friendlyMessage(0, {}), /Can't reach HomeHaat/);
  assert.match(friendlyMessage(500, {}), /server had a problem/);
});

test("a sleeping free server is explained, not called a crash", () => {
  for (const status of [502, 503, 504]) assert.match(friendlyMessage(status, {}), /waking up/);
  assert.equal(friendlyMessage(503, { detail: "AI is switched off." }), "AI is switched off."); // Django's own words win
});

test("asks again only while the server may be waking up", () => {
  assert.equal(shouldRetry(new ApiError(0, {}), 0), true); // no reply at all
  assert.equal(shouldRetry(new ApiError(502, {}), 0), true);
  assert.equal(shouldRetry(new ApiError(504, {}), RETRY_DELAYS_MS.length - 1), true);
  assert.equal(shouldRetry(new ApiError(504, {}), RETRY_DELAYS_MS.length), false); // gives up in the end
  assert.equal(shouldRetry(new ApiError(500, {}), 0), false); // a real crash: asking again won't help
  assert.equal(shouldRetry(new ApiError(400, { detail: "Your bag is empty." }), 0), false);
  assert.equal(shouldRetry(new ApiError(404, {}), 0), false);
  assert.equal(shouldRetry(new ApiError(503, { detail: "AI is busy." }), 0), false); // Django answered
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
