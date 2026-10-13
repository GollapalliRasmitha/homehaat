import Link from "next/link";
import { notFound } from "next/navigation";

import { EmptyState } from "@/components/EmptyState";
import { ProductGrid, stockTag } from "@/components/ProductCard";
import { SectionHead } from "@/components/SectionHead";
import { getProduct, listProducts } from "@/lib/api/catalog";
import { ApiError, errorMessage } from "@/lib/api/client";
import type { Product } from "@/lib/api/types";
import { deliveryText, formatINR } from "@/lib/format";

import { AddToBag } from "./AddToBag";
import { Gallery } from "./Gallery";

export default async function ProductPage({ params }: PageProps<"/product/[id]">) {
  const { id } = await params;
  let product: Product;
  try {
    product = await getProduct(id);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    // Server down or crashed: say so in plain words instead of showing a crash screen.
    return (
      <EmptyState
        title="This product didn't load"
        text={errorMessage(error)}
        action={
          <Link href={`/product/${id}`} className="btn btn-black">
            Try again
          </Link>
        }
      />
    );
  }
  // "More from this seller" is extra: if it fails, the page still works without it.
  const more = (await listProducts({ seller: product.seller.slug, limit: 5 }).catch(() => []))
    .filter((p) => p.id !== product.id)
    .slice(0, 4);
  const tag = stockTag(product.stock);

  return (
    <>
      <div className="mb-4 text-sm text-muted">
        <Link href="/" className="text-muted">
          Home
        </Link>{" "}
        /{" "}
        <Link href={`/explore?category=${product.category.slug}`} className="text-muted">
          {product.category.name}
        </Link>{" "}
        / {product.name}
      </div>
      <div className="flex flex-wrap items-start gap-8 sm:gap-12">
        <Gallery product={product} />
        <div className="flex min-w-0 flex-[1_1_380px] flex-col gap-[18px]">
          <Link href={`/store/${product.seller.slug}`} className="text-[15px] font-medium text-muted no-underline hover:text-ink hover:underline">
            {product.seller.name}
            {product.seller.area && ` · ${product.seller.area}`}
          </Link>
          <h1 className="title">{product.name}</h1>
          <div className="flex flex-wrap items-center gap-3">
            <span className="price text-[30px]">{formatINR(product.price_paise)}</span>
            <span className={`status ${product.stock === 0 ? "st-cancelled" : tag ? "st-new" : "st-delivered"}`}>
              {tag ?? "In stock"}
            </span>
          </div>
          <p className="whitespace-pre-line text-[17px] text-muted">{product.description || "Not provided by seller"}</p>

          <AddToBag
            productId={product.id}
            productName={product.name}
            stock={product.stock}
            sellerSlug={product.seller.slug}
            takingOrders={product.seller.taking_orders}
          />

          <dl className="border-t border-line text-[15px]">
            {[
              ["Delivery", deliveryText(product.seller.delivery_days)],
              ["Delivery fee", `${formatINR(product.seller.delivery_fee_paise)} per order from this maker`],
              ["Payment", "One payment for your whole bag"],
            ].map(([label, value]) => (
              <div key={label} className="flex justify-between gap-3 border-b border-line py-3.5">
                <dt className="text-muted">{label}</dt>
                <dd className="text-right font-medium">{value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>

      {more.length > 0 && (
        <section className="pt-[72px]" aria-labelledby="more">
          <SectionHead id="more" title={`More from ${product.seller.name}`} link={{ href: `/store/${product.seller.slug}`, label: "Visit shop" }} />
          <ProductGrid products={more} />
        </section>
      )}
    </>
  );
}
