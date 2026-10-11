"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { LoadError } from "@/components/LoadError";
import { ProductGrid } from "@/components/ProductCard";
import { listProducts } from "@/lib/api/catalog";
import type { Product } from "@/lib/api/types";
import { PHOTOS } from "@/lib/photos";
import { useWishlist } from "@/lib/wishlist";

export default function WishlistPage() {
  const ids = useWishlist();
  const [products, setProducts] = useState<Product[] | null>(null);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const key = ids.join(",");

  useEffect(() => {
    // Ask the server for the saved products: hidden, sold-out-and-removed or paused ones simply don't come back.
    const request = key ? listProducts({ ids: key }) : Promise.resolve([]);
    request.then(setProducts).catch(setLoadError);
  }, [key, attempt]);

  if (loadError) {
    const retry = () => {
      setLoadError(null);
      setAttempt((n) => n + 1);
    };
    return <LoadError error={loadError} onRetry={retry} title="Couldn't load your wishlist" />;
  }
  if (!products) return <p className="text-muted">Loading…</p>;

  // Keep the order you saved them in (newest first); unsaving removes the card at once.
  const byId = new Map(products.map((p) => [p.id, p]));
  const shown = ids.map((id) => byId.get(id)).filter((p): p is Product => Boolean(p));

  return (
    <>
      <h1 className="title mb-7">Wishlist</h1>
      {shown.length === 0 ? (
        <EmptyState
          photoId={PHOTOS.crafts}
          title="Nothing saved yet"
          text="Tap the heart on any product to save it here."
          action={
            <Link href="/explore" className="btn btn-black">
              Explore
            </Link>
          }
        />
      ) : (
        <ProductGrid products={shown} />
      )}
      <p className="mt-6 text-sm text-muted">Your wishlist is saved in this browser.</p>
    </>
  );
}
