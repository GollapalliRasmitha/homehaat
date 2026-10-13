"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { Stars } from "@/components/Stars";
import { LoadError } from "@/components/LoadError";
import { getMyReviews } from "@/lib/api/seller";
import type { SellerReviews } from "@/lib/api/types";
import { PHOTOS } from "@/lib/photos";

export default function SellerReviewsPage() {
  const [data, setData] = useState<SellerReviews | null>(null);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    getMyReviews()
      .then(setData)
      .catch(setLoadError);
  }, [attempt]);

  if (loadError) {
    const retry = () => {
      setLoadError(null);
      setAttempt((n) => n + 1);
    };
    return <LoadError error={loadError} onRetry={retry} title="Couldn't load your reviews" />;
  }
  if (!data) return <p className="text-muted">Loading…</p>;
  if (data.count === 0) {
    return (
      <EmptyState
        photoId={PHOTOS.crafts}
        title="No reviews yet"
        text="Buyers can review your shop once their order is delivered. Their reviews will show here."
      />
    );
  }

  return (
    <>
      <p className="mb-5 text-lg">
        <b>{data.average}</b> <Stars rating={data.average ?? 0} /> <span className="text-muted">average from {data.count} {data.count === 1 ? "review" : "reviews"}</span>
      </p>
      <div className="flex flex-col gap-3">
        {data.reviews.map((r) => (
          <div key={r.id} className="panel">
            <Stars rating={r.rating} className="font-semibold" />{" "}
            <span className="text-muted">
              · {r.buyer_name} · {new Date(r.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}
            </span>
            {r.comment && <p className="mt-1.5">{r.comment}</p>}
          </div>
        ))}
      </div>
    </>
  );
}
