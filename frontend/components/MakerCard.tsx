import Link from "next/link";

import type { PublicStore } from "@/lib/api/types";

import { Monogram } from "./Monogram";

/** UI-UX.md maker card: soft background, monogram, then name, kind, area and product count. */
export function MakerCard({ store }: { store: PublicStore }) {
  const facts = [store.kind_label, store.area, `${store.product_count} ${store.product_count === 1 ? "product" : "products"}`]
    .filter(Boolean)
    .join(" · ");
  return (
    <Link
      href={`/store/${store.slug}`}
      className="flex items-center gap-4 rounded-[22px] bg-soft p-5 no-underline transition-transform duration-300 hover:-translate-y-1"
    >
      <Monogram name={store.name} slug={store.slug} />
      <span className="flex min-w-0 flex-col gap-0.5">
        <span className="text-[17px] font-semibold">{store.name}</span>
        <span className="text-[14.5px] text-muted">{facts}</span>
      </span>
    </Link>
  );
}

export function MakerGrid({ stores }: { stores: PublicStore[] }) {
  return (
    <div className="grid gap-[22px] sm:grid-cols-[repeat(auto-fill,minmax(300px,1fr))]">
      {stores.map((s) => (
        <MakerCard key={s.slug} store={s} />
      ))}
    </div>
  );
}
