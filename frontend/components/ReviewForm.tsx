"use client";

import { useState } from "react";
import { toast } from "sonner";

import { errorMessage } from "@/lib/api/client";
import { writeReview } from "@/lib/api/reviews";

import { StarInput, Stars } from "./Stars";

type Review = { rating: number; comment: string };

/**
 * On a delivered seller order: "Write a review", or "Your review" with Edit.
 * One review per maker, so writing again edits the same review.
 */
export function ReviewForm({
  sellerSlug,
  sellerName,
  review,
  onSaved,
}: {
  sellerSlug: string;
  sellerName: string;
  review: Review | null;
  onSaved: (review: Review) => void;
}) {
  const [open, setOpen] = useState(false);
  const [rating, setRating] = useState(review?.rating ?? 0);
  const [comment, setComment] = useState(review?.comment ?? "");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (!rating) {
      setError("Choose a rating from 1 to 5 stars.");
      return;
    }
    setBusy(true);
    try {
      const saved = await writeReview(sellerSlug, rating, comment.trim());
      toast(review ? "Review updated" : "Thanks for your review");
      onSaved({ rating: saved.rating, comment: saved.comment });
      setOpen(false);
    } catch (e) {
      toast(`Couldn't save your review. ${errorMessage(e)}`);
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-line pt-4">
        {review ? (
          <>
            <div className="min-w-0 flex-1">
              <span className="text-sm text-muted">Your review · </span>
              <Stars rating={review.rating} />
              {review.comment && <p className="mt-1 text-[15px]">{review.comment}</p>}
            </div>
            <button type="button" className="btn btn-white" onClick={() => setOpen(true)}>
              Edit review
            </button>
          </>
        ) : (
          <>
            <p className="min-w-0 flex-1 text-[15px] text-muted">Delivered. How was it?</p>
            <button type="button" className="btn btn-black" onClick={() => setOpen(true)}>
              Write a review
            </button>
          </>
        )}
      </div>
    );
  }

  return (
    <form onSubmit={save} noValidate className="mt-4 flex flex-col gap-3.5 border-t border-line pt-4">
      <h3 className="text-lg">
        Review <span className="serif">{sellerName}</span>
      </h3>
      <div>
        <StarInput
          value={rating}
          onChange={(n) => {
            setRating(n);
            setError("");
          }}
        />
        {error && <p className="field-error">{error}</p>}
      </div>
      <div>
        <label className="field-label" htmlFor={`review-${sellerSlug}`}>
          A few words (optional)
        </label>
        <textarea
          id={`review-${sellerSlug}`}
          className="textarea"
          rows={3}
          maxLength={1000}
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="What did you order, and how was it?"
        />
      </div>
      <p className="text-[13px] text-muted">Shown on the maker&apos;s shop page with your first name.</p>
      <div className="flex flex-wrap gap-2.5">
        <button className="btn btn-black" disabled={busy}>
          {busy ? "Saving…" : review ? "Save changes" : "Post review"}
        </button>
        <button type="button" className="btn btn-white" onClick={() => setOpen(false)}>
          Cancel
        </button>
      </div>
    </form>
  );
}
