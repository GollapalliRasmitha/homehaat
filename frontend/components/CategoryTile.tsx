import Link from "next/link";

import { SafeImage } from "./SafeImage";

import type { Category } from "@/lib/api/types";
import { unsplash } from "@/lib/photos";

import { tintVar } from "./CategoryArt";

/** UI-UX.md category tile: a square photo (radius 20) with the name underneath; the photo zooms a little on hover. */
export function CategoryTile({ category, showCount = false }: { category: Category; showCount?: boolean }) {
  const count = category.product_count ?? 0;
  return (
    <Link href={`/explore?category=${category.slug}`} className="group flex flex-col gap-3 no-underline">
      <span className="relative block aspect-square overflow-hidden rounded-[20px]" style={{ background: tintVar(category.tint) }}>
        <SafeImage
          src={unsplash(category.photo_id, 500)}
          alt=""
          fill
          sizes="(max-width: 640px) 45vw, 200px"
          className="object-cover transition-transform duration-500 group-hover:scale-105"
        />
      </span>
      <span className="px-0.5 text-lg font-semibold tracking-[-0.02em]">
        {category.name}
        {showCount && (
          <span className="block text-sm font-normal text-muted">
            {count} {count === 1 ? "product" : "products"}
          </span>
        )}
      </span>
    </Link>
  );
}

export function CategoryGrid({ categories, showCount = false }: { categories: Category[]; showCount?: boolean }) {
  return (
    <div className="grid grid-cols-2 gap-3.5 sm:grid-cols-[repeat(auto-fill,minmax(180px,1fr))]">
      {categories.map((c) => (
        <CategoryTile key={c.slug} category={c} showCount={showCount} />
      ))}
    </div>
  );
}
