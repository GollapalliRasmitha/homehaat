import assert from "node:assert/strict";
import { test } from "node:test";

import { filtersToApi, filtersToQuery, readFilters } from "./explore.ts";

test("reads filters from the URL with safe defaults", () => {
  const f = readFilters(new URLSearchParams("q=cake&category=cakes&in_stock=1&min=200&sort=nonsense"));
  assert.deepEqual(f, { q: "cake", category: "cakes", sort: "relevance", inStock: true, minRupees: "200", maxRupees: "", page: 1 });
  assert.equal(readFilters(new URLSearchParams("")).sort, "newest"); // no search -> newest first
});

test("round-trips through the URL and leaves out defaults", () => {
  const f = readFilters(new URLSearchParams("q=pickle&sort=price_asc&max=500"));
  assert.equal(filtersToQuery(f), "?q=pickle&sort=price_asc&max=500");
  assert.equal(filtersToQuery(readFilters(new URLSearchParams("q=pickle"))), "?q=pickle"); // relevance is the default
  assert.equal(filtersToQuery(readFilters(new URLSearchParams(""))), "");
});

test("sends prices to the API in paise and drops invalid ones", () => {
  const api = filtersToApi(readFilters(new URLSearchParams("min=200&max=abc&in_stock=1")));
  assert.deepEqual(api, { sort: "newest", in_stock: "1", min_price: "20000", page: "1" });
});

test("the page number is in the URL, and bad page numbers become page 1", () => {
  const f = readFilters(new URLSearchParams("q=candle&page=3"));
  assert.equal(f.page, 3);
  assert.equal(filtersToQuery(f), "?q=candle&page=3");
  assert.equal(filtersToApi(f).page, "3");
  for (const bad of ["0", "-2", "abc", "1.5", ""]) assert.equal(readFilters(new URLSearchParams(`page=${bad}`)).page, 1);
  assert.equal(filtersToQuery({ ...f, page: 1 }), "?q=candle"); // page 1 is the default, left out
});
