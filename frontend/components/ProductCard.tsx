import Link from "next/link";

import type { Product } from "@/lib/api/types";
import { deliveryText, formatINR } from "@/lib/format";

import { ProductImage } from "./ProductImage";

export function stockTag(stock: number): string | null {
  if (stock === 0) return "Sold out";
  if (stock <= 3) return `Only ${stock} left`;
  return null;
}

export function ProductCard({ product }: { product: Product }) {
  const tag = stockTag(product.stock);
  return (
    <article className="flex flex-col gap-3.5">
      <Link href={`/product/${product.id}`} className="relative block" aria-label={product.name}>
        <ProductImage product={product} className="rounded-[22px]" />
        {tag && (
          <span
            className={`absolute left-3.5 top-3.5 rounded-full px-3 py-1 text-[12.5px] font-semibold ${
              product.stock === 0 ? "bg-ink text-white" : "bg-white"
            }`}
          >
            {tag}
          </span>
        )}
      </Link>
      <div className="flex flex-col gap-0.5 px-0.5">
        <span className="text-sm font-medium text-muted">{product.seller.name}</span>
        <Link href={`/product/${product.id}`} className="text-lg font-semibold leading-snug tracking-[-0.02em] no-underline">
          {product.name}
        </Link>
        <span className="text-[14.5px] text-muted">{deliveryText(product.seller.delivery_days)}</span>
        <span className="price mt-2 text-[19px]">{formatINR(product.price_paise)}</span>
      </div>
    </article>
  );
}
