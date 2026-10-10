import type { Product } from "@/lib/api/types";

import { CategoryArt, tintVar } from "./CategoryArt";

/** The seller's photo, or the category line drawing on its tint until they add one. */
export function ProductImage({ product, className = "" }: { product: Product; className?: string }) {
  return (
    <div
      className={`flex aspect-square items-center justify-center overflow-hidden ${className}`}
      style={{ background: tintVar(product.category.tint) }}
    >
      {product.image ? (
        // Seller uploads arrive in Stage 3 (next/image + resized copies in Stage 7).
        // eslint-disable-next-line @next/next/no-img-element
        <img src={product.image} alt={product.name} className="size-full object-cover" />
      ) : (
        <CategoryArt art={product.category.art} className="w-[52%]" />
      )}
    </div>
  );
}
