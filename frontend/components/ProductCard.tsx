import Link from "next/link";

import type { Product } from "@/lib/api/types";
import { deliveryText, formatINR } from "@/lib/format";

import { ProductImage } from "./ProductImage";
import { QuickAdd } from "./QuickAdd";
import { WishlistButton } from "./WishlistButton";

export function stockTag(stock: number): string | null {
  if (stock === 0) return "Sold out";
  if (stock <= 3) return `Only ${stock} left`;
  return null;
}

/** UI-UX.md product card: no box; square photo with heart + tag, then maker, name, delivery, price and +. */
export function ProductCard({ product }: { product: Product }) {
  const tag = stockTag(product.stock);
  return (
    <article className="group flex flex-col gap-3.5 transition-transform duration-300 hover:-translate-y-1">
      <div className="relative">
        <Link href={`/product/${product.id}`} className="block" aria-label={product.name}>
          <ProductImage product={product} className="rounded-[22px]" zoomOnHover />
        </Link>
        {tag && (
          <span
            className={`absolute left-3.5 top-3.5 rounded-full px-3 py-1 text-[12.5px] font-semibold ${
              product.stock === 0 ? "bg-ink text-white" : "bg-white"
            }`}
          >
            {tag}
          </span>
        )}
        <WishlistButton productId={product.id} productName={product.name} />
      </div>
      <div className="flex flex-col gap-0.5 px-0.5">
        <Link href={`/store/${product.seller.slug}`} className="text-sm font-medium text-muted no-underline hover:text-ink hover:underline">
          {product.seller.name}
        </Link>
        <Link href={`/product/${product.id}`} className="text-lg font-semibold leading-snug tracking-[-0.02em] no-underline">
          {product.name}
        </Link>
        <span className="text-[14.5px] text-muted">{deliveryText(product.seller.delivery_days)}</span>
        <div className="mt-2 flex items-center justify-between gap-3">
          <span className="price text-[19px]">{formatINR(product.price_paise)}</span>
          <QuickAdd product={product} />
        </div>
      </div>
    </article>
  );
}

/** The responsive grid used for every list of product cards. */
export function ProductGrid({ products }: { products: Product[] }) {
  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-8 sm:grid-cols-[repeat(auto-fill,minmax(240px,1fr))] sm:gap-[22px]">
      {products.map((p) => (
        <ProductCard key={p.id} product={p} />
      ))}
    </div>
  );
}
