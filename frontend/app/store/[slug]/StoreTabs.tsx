"use client";

import { useId, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { ProductGrid } from "@/components/ProductCard";
import type { Product, StoreReview } from "@/lib/api/types";
import { PHOTOS } from "@/lib/photos";
import { useSession } from "@/lib/session";

/**
 * Products grouped by category in tabs, plus a Reviews tab.
 * Proper ARIA tabs: arrow keys move between tabs, and screen readers hear "tab 2 of 4".
 */
export function StoreTabs({ products, reviews, storeSlug }: { products: Product[]; reviews: StoreReview[]; storeSlug: string }) {
  const base = useId();
  const isMine = useSession().user?.store_slug === storeSlug;
  // One tab per category this shop sells in, the ones with most products first.
  const countIn = (slug: string) => products.filter((p) => p.category.slug === slug).length;
  const categories = [...new Map(products.map((p) => [p.category.slug, p.category])).values()].sort(
    (a, b) => countIn(b.slug) - countIn(a.slug) || a.name.localeCompare(b.name),
  );
  const tabs = [
    { key: "all", label: `All products (${products.length})` },
    ...(categories.length > 1 ? categories.map((c) => ({ key: c.slug, label: c.name })) : []),
    { key: "reviews", label: `Reviews (${reviews.length})` },
  ];
  const [active, setActive] = useState("all");

  function onKeyDown(event: React.KeyboardEvent, index: number) {
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (!step) return;
    const next = tabs[(index + step + tabs.length) % tabs.length];
    setActive(next.key);
    document.getElementById(`${base}-tab-${next.key}`)?.focus();
  }

  const shown = active === "all" ? products : products.filter((p) => p.category.slug === active);
  return (
    <section className="pt-10">
      <div role="tablist" aria-label="Shop sections" className="mb-7 flex gap-x-7 overflow-x-auto no-scrollbar border-b border-line">
        {tabs.map((tab, i) => (
          <button
            key={tab.key}
            id={`${base}-tab-${tab.key}`}
            role="tab"
            aria-selected={active === tab.key}
            aria-controls={`${base}-panel`}
            tabIndex={active === tab.key ? 0 : -1}
            onClick={() => setActive(tab.key)}
            onKeyDown={(e) => onKeyDown(e, i)}
            className={`-mb-px h-12 whitespace-nowrap border-b-2 text-base ${
              active === tab.key ? "border-ink font-semibold text-ink" : "border-transparent font-medium text-muted hover:text-ink"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div id={`${base}-panel`} role="tabpanel" aria-labelledby={`${base}-tab-${active}`}>
        {active === "reviews" ? (
          reviews.length === 0 ? (
            <EmptyState photoId={PHOTOS.crafts} title="No reviews yet" text="Buyers can review this maker after their order is delivered." />
          ) : (
            <div className="flex flex-col gap-3">
              {reviews.map((r) => (
                <div key={r.id} className="panel">
                  <b aria-label={`${r.rating} out of 5 stars`}>{"★".repeat(r.rating) + "☆".repeat(5 - r.rating)}</b>{" "}
                  <span className="text-muted">· {r.buyer_name}</span>
                  {r.comment && <p className="mt-1.5">{r.comment}</p>}
                </div>
              ))}
            </div>
          )
        ) : shown.length === 0 ? (
          <EmptyState
            photoId={PHOTOS.cakes}
            title="No products yet"
            text={isMine ? "Add your first product from your shop dashboard." : "This maker hasn't added products yet."}
          />
        ) : (
          <ProductGrid products={shown} />
        )}
      </div>
    </section>
  );
}
