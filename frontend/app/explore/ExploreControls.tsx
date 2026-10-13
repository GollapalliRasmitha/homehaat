"use client";

import { Search } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";

import type { Category } from "@/lib/api/types";
import { type ExploreFilters, filtersToQuery, priceRangeError, SORTS } from "@/lib/explore";

const chip = (on: boolean) =>
  `h-[42px] rounded-full border px-[18px] text-[15px] font-medium whitespace-nowrap ${
    on ? "border-ink bg-ink text-white" : "border-line bg-white hover:border-ink"
  }`;

/** Search box, sort, In stock only, price range and category chips. Every change updates the URL. */
export function ExploreControls({ filters, categories }: { filters: ExploreFilters; categories: Category[] }) {
  const router = useRouter();
  const pathname = usePathname();
  const [pending, startTransition] = useTransition();
  const [q, setQ] = useState(filters.q);
  const [min, setMin] = useState(filters.minRupees);
  const [max, setMax] = useState(filters.maxRupees);
  const [priceError, setPriceError] = useState<string | null>(null);
  const [typedQ, setTypedQ] = useState(filters.q); // the last search WE sent from this box
  const [seen, setSeen] = useState(filters); // the filters from the URL we last showed

  // The URL changed from elsewhere (Clear filters, back button): show its values in the boxes.
  // (React's recommended way to update state from new props: during render, not in an effect.)
  if (filters !== seen) {
    setSeen(filters);
    if (filters.q !== typedQ) {
      setQ(filters.q);
      setTypedQ(filters.q);
    }
    setMin(filters.minRupees);
    setMax(filters.maxRupees);
  }

  // Any change of search or filter starts again at page 1.
  const go = (change: Partial<ExploreFilters>) => {
    if (change.q !== undefined) {
      setTypedQ(change.q);
      // Still on the default sort? Then follow the new default: "Best match" when searching, "Newest" when not.
      const wasDefault = filters.sort === (filters.q ? "relevance" : "newest");
      if (wasDefault && change.sort === undefined) change = { ...change, sort: change.q ? "relevance" : "newest" };
    }
    startTransition(() => router.replace(`${pathname}${filtersToQuery({ ...filters, page: 1, ...change })}`, { scroll: false }));
  };

  // Typing searches after a short pause, instead of on every key press.
  useEffect(() => {
    if (q.trim() === filters.q) return;
    const timer = setTimeout(() => go({ q: q.trim() }), 350);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  return (
    <div className="mb-7 mt-5 flex flex-col gap-3" aria-busy={pending}>
      <div className="flex flex-wrap items-center gap-2.5">
        <label className="flex h-[50px] min-w-0 flex-[1_1_280px] items-center gap-2.5 rounded-full border border-line bg-white px-5 focus-within:border-ink">
          <span className="sr-only">Search products and makers</span>
          <Search size={18} aria-hidden="true" className="text-muted" />
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search cakes, pickles, art…"
            className="min-w-0 flex-1 bg-transparent outline-none"
          />
        </label>
        <label className="sr-only" htmlFor="sort">
          Sort by
        </label>
        <select
          id="sort"
          value={filters.sort}
          onChange={(e) => go({ sort: e.target.value as ExploreFilters["sort"] })}
          className="h-[42px] rounded-full border border-line bg-white px-3.5 text-[15px] font-medium"
        >
          {SORTS.filter(([v]) => v !== "relevance" || filters.q).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <button className={chip(filters.inStock)} aria-pressed={filters.inStock} onClick={() => go({ inStock: !filters.inStock })}>
          In stock only
        </button>
      </div>

      <form
        className="flex flex-wrap items-center gap-2 text-[15px]"
        onSubmit={(e) => {
          e.preventDefault();
          const problem = priceRangeError(min, max);
          setPriceError(problem);
          if (!problem) go({ minRupees: min.trim(), maxRupees: max.trim() });
        }}
      >
        <span className="font-medium">Price (₹)</span>
        <label className="sr-only" htmlFor="min">
          Lowest price in rupees
        </label>
        <input
          id="min"
          inputMode="numeric"
          placeholder="Min"
          value={min}
          onChange={(e) => {
            setMin(e.target.value);
            setPriceError(null);
          }}
          aria-invalid={priceError ? true : undefined}
          aria-describedby={priceError ? "price-error" : undefined}
          className="input h-[42px] w-24 rounded-full px-4"
        />
        <span aria-hidden="true">–</span>
        <label className="sr-only" htmlFor="max">
          Highest price in rupees
        </label>
        <input
          id="max"
          inputMode="numeric"
          placeholder="Max"
          value={max}
          onChange={(e) => {
            setMax(e.target.value);
            setPriceError(null);
          }}
          aria-invalid={priceError ? true : undefined}
          aria-describedby={priceError ? "price-error" : undefined}
          className="input h-[42px] w-24 rounded-full px-4"
        />
        <button className="btn btn-white h-[42px] px-[18px]">Apply</button>
        {priceError && (
          <p id="price-error" className="field-error mt-0 w-full" role="alert">
            {priceError}
          </p>
        )}
      </form>

      {/* Category chips scroll sideways on a phone instead of making the page wider. */}
      <div className="-mx-4 flex gap-2.5 overflow-x-auto no-scrollbar px-4 pb-1 sm:mx-0 sm:flex-wrap sm:px-0" role="group" aria-label="Category">
        <button className={chip(!filters.category)} aria-pressed={!filters.category} onClick={() => go({ category: "" })}>
          All
        </button>
        {categories.map((c) => (
          <button key={c.slug} className={chip(filters.category === c.slug)} aria-pressed={filters.category === c.slug} onClick={() => go({ category: c.slug })}>
            {c.name}
          </button>
        ))}
      </div>
    </div>
  );
}
