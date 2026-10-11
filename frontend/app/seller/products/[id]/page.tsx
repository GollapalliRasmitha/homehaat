"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { LoadError } from "@/components/LoadError";
import { ProductForm } from "@/components/ProductForm";
import { ApiError } from "@/lib/api/client";
import { getMyProduct } from "@/lib/api/seller";
import type { SellerProduct } from "@/lib/api/types";

export default function EditProductPage() {
  const { id } = useParams<{ id: string }>();
  const [product, setProduct] = useState<SellerProduct | null>(null);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    getMyProduct(id)
      .then(setProduct)
      .catch(setLoadError);
  }, [id, attempt]);

  if (loadError instanceof ApiError && loadError.status === 404) {
    return (
      <EmptyState
        title="Product not found"
        text="It may have been removed, or it belongs to another shop."
        action={
          <Link href="/seller/products" className="btn btn-black">
            Back to my products
          </Link>
        }
      />
    );
  }
  if (loadError) {
    const retry = () => {
      setLoadError(null);
      setAttempt((n) => n + 1);
    };
    return <LoadError error={loadError} onRetry={retry} title="Couldn't load this product" />;
  }
  if (!product) return <p className="text-muted">Loading…</p>;
  return <ProductForm product={product} />;
}
