"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { CategoryArt, tintVar } from "@/components/CategoryArt";
import { EmptyState } from "@/components/EmptyState";
import { LoadError } from "@/components/LoadError";
import { SafeImg } from "@/components/SafeImage";
import { listCategories } from "@/lib/api/catalog";
import { errorMessage } from "@/lib/api/client";
import { listMyProducts, updateProduct } from "@/lib/api/seller";
import type { Category, SellerProduct } from "@/lib/api/types";
import { formatINR } from "@/lib/format";
import { PHOTOS } from "@/lib/photos";

export default function SellerProductsPage() {
  const [products, setProducts] = useState<SellerProduct[] | null>(null);
  const [categories, setCategories] = useState<Record<string, Category>>({});
  const [loadError, setLoadError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    Promise.all([listMyProducts(), listCategories()])
      .then(([p, c]) => {
        setProducts(p);
        setCategories(Object.fromEntries(c.map((cat) => [cat.slug, cat])));
      })
      .catch(setLoadError);
  }, [attempt]);

  if (loadError) {
    const retry = () => {
      setLoadError(null);
      setAttempt((n) => n + 1);
    };
    return <LoadError error={loadError} onRetry={retry} title="Couldn't load your products" />;
  }
  if (!products) return <p className="text-muted">Loading your products…</p>;

  async function toggle(product: SellerProduct) {
    try {
      const updated = await updateProduct(product.id, { is_active: !product.is_active });
      setProducts(products!.map((p) => (p.id === updated.id ? updated : p)));
      toast(updated.is_active ? "Product is live" : "Product hidden from buyers");
    } catch (error) {
      toast(`Couldn't change it. ${errorMessage(error)}`);
    }
  }

  if (products.length === 0) {
    return (
      <EmptyState
        photoId={PHOTOS.cakes}
        title="Add your first product"
        text="Add a photo, a name, a price and how many you can make. Buyers can then find it."
        action={
          <Link href="/seller/products/new" className="btn btn-black btn-lg">
            Add a product
          </Link>
        }
      />
    );
  }

  return (
    <>
      <div className="mb-4 flex justify-end">
        <Link href="/seller/products/new" className="btn btn-black">
          Add a product
        </Link>
      </div>
      <div className="panel">
        {products.map((p) => {
          const cat = categories[p.category];
          return (
            <div key={p.id} className="flex flex-wrap items-center gap-3.5 border-b border-line py-3.5 last:border-0">
              <div
                className="flex size-[64px] flex-none items-center justify-center overflow-hidden rounded-2xl"
                style={{ background: tintVar(cat?.tint ?? "soft") }}
              >
                {p.image ? (
                  <SafeImg
                    src={p.image}
                    alt=""
                    className="size-full object-cover"
                    fallback={<CategoryArt art={cat?.art ?? "gift"} className="w-[60%]" />}
                  />
                ) : (
                  <CategoryArt art={cat?.art ?? "gift"} className="w-[60%]" />
                )}
              </div>
              <div className="min-w-0 flex-[1_1_200px]">
                <b>{p.name}</b>
                <div className="text-sm text-muted">
                  {formatINR(p.price_paise)} · {p.stock} in stock · {p.sold} sold
                </div>
              </div>
              <span className={`status ${p.is_active ? "st-delivered" : "st-cancelled"}`}>{p.is_active ? "Live" : "Hidden"}</span>
              <button
                className="btn btn-white h-10"
                onClick={() => toggle(p)}
                role="switch"
                aria-checked={p.is_active}
                aria-label={`Show ${p.name} to buyers`}
              >
                {p.is_active ? "Hide" : "Show"}
              </button>
              <Link href={`/seller/products/${p.id}`} className="btn btn-white h-10">
                Edit
              </Link>
            </div>
          );
        })}
      </div>
    </>
  );
}
