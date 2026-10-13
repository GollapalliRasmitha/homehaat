"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { LoadError } from "@/components/LoadError";
import { listCategories } from "@/lib/api/catalog";
import { listMyProducts } from "@/lib/api/seller";
import type { Category, SellerProduct } from "@/lib/api/types";
import { PHOTOS } from "@/lib/photos";

import { ProductRow } from "./ProductRow";

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
        {products.map((p) => (
          <ProductRow
            key={p.id}
            product={p}
            category={categories[p.category]}
            onChange={(updated) => setProducts(products.map((x) => (x.id === updated.id ? updated : x)))}
            onRemoved={(id) => setProducts(products.filter((x) => x.id !== id))}
          />
        ))}
      </div>
    </>
  );
}
