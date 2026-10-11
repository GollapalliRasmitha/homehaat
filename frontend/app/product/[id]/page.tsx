import Link from "next/link";
import { notFound } from "next/navigation";

import { EmptyState } from "@/components/EmptyState";
import { stockTag } from "@/components/ProductCard";
import { ProductImage } from "@/components/ProductImage";
import { getProduct } from "@/lib/api/catalog";
import { ApiError, errorMessage } from "@/lib/api/client";
import { deliveryText, formatINR } from "@/lib/format";

import { AddToBag } from "./AddToBag";

export default async function ProductPage({ params }: PageProps<"/product/[id]">) {
  const { id } = await params;
  let product;
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
  const tag = stockTag(product.stock);

  return (
    <>
      <div className="mb-4 text-sm text-muted">
        <Link href="/" className="text-muted">
          Home
        </Link>{" "}
        / {product.category.name} / {product.name}
      </div>
      <div className="flex flex-wrap items-start gap-12">
        <ProductImage product={product} className="min-w-0 max-w-full flex-[1_1_420px] rounded-[28px]" />
        <div className="flex min-w-0 flex-[1_1_360px] flex-col gap-4">
          <span className="text-[15px] font-medium text-muted">
            {product.seller.name}
            {product.seller.area && ` · ${product.seller.area}`}
          </span>
          <h1 className="title">{product.name}</h1>
          <div className="flex flex-wrap items-center gap-3">
            <span className="price text-[30px]">{formatINR(product.price_paise)}</span>
            <span className={`status ${product.stock === 0 ? "st-cancelled" : tag ? "st-new" : "st-delivered"}`}>
              {tag ?? "In stock"}
            </span>
          </div>
          <p className="text-[17px] text-muted">{product.description || "Not provided by seller"}</p>

          <AddToBag productId={product.id} stock={product.stock} sellerSlug={product.seller.slug} />

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
    </>
  );
}
