"use client";

import { useState } from "react";

import { ProductImage } from "@/components/ProductImage";
import type { Product } from "@/lib/api/types";

/** Big photo + small thumbnails (up to 5). With no photos: the category drawing. */
export function Gallery({ product }: { product: Product }) {
  const [index, setIndex] = useState(0);
  const photos = product.images;
  return (
    <div className="flex min-w-0 max-w-full flex-[1_1_460px] flex-col gap-3">
      <ProductImage product={product} src={photos[index] ?? null} className="rounded-[28px]" />
      {photos.length > 1 && (
        <div className="flex flex-wrap gap-2.5" role="group" aria-label="Photos">
          {photos.map((url, i) => (
            <button
              key={url}
              type="button"
              onClick={() => setIndex(i)}
              aria-label={`Show photo ${i + 1} of ${photos.length}`}
              aria-pressed={i === index}
              className={`size-[72px] overflow-hidden rounded-2xl border-2 ${i === index ? "border-ink" : "border-transparent"}`}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={url} alt="" className="size-full object-cover" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
