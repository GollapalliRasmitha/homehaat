import type { Product } from "@/lib/api/types";

import { CategoryArt, tintVar } from "./CategoryArt";

/** The seller's photo, or the category line drawing on its tint until they add one. Never a stock photo. */
export function ProductImage({
  product,
  src,
  className = "",
  zoomOnHover = false,
}: {
  product: Pick<Product, "name" | "image" | "category">;
  src?: string | null; // a specific photo (the gallery); defaults to the main one
  className?: string;
  zoomOnHover?: boolean; // used inside a `group` (the product card)
}) {
  const url = src === undefined ? product.image : src;
  const zoom = zoomOnHover ? "transition-transform duration-500 group-hover:scale-[1.04]" : "";
  return (
    <div
      className={`flex aspect-square items-center justify-center overflow-hidden ${className}`}
      style={{ background: tintVar(product.category.tint) }}
    >
      {url ? (
        // Seller uploads are served by Django (/media); resized copies + next/image come in Stage 7.
        // eslint-disable-next-line @next/next/no-img-element
        <img src={url} alt={product.name} loading="lazy" className={`size-full object-cover ${zoom}`} />
      ) : (
        <CategoryArt art={product.category.art} className={`w-[52%] ${zoom}`} />
      )}
    </div>
  );
}
