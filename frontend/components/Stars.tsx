"use client";

import { useId } from "react";

/** A rating shown as five stars, read out as "4 out of 5 stars". */
export function Stars({ rating, className = "" }: { rating: number; className?: string }) {
  const full = Math.round(rating);
  return (
    <span role="img" aria-label={`${rating} out of 5 stars`} className={`tracking-[1px] ${className}`}>
      {"★".repeat(full)}
      <span className="text-muted/35">{"★".repeat(5 - full)}</span>
    </span>
  );
}

const WORDS = ["", "Poor", "Okay", "Good", "Very good", "Loved it"];

/**
 * Choosing 1–5 stars. Real radio buttons underneath, so arrow keys work and screen readers say
 * "4 stars, Very good, 4 of 5".
 */
export function StarInput({ value, onChange }: { value: number; onChange: (n: number) => void }) {
  const name = useId();
  return (
    <fieldset>
      <legend className="field-label">Your rating</legend>
      <div className="flex items-center gap-1">
        {[1, 2, 3, 4, 5].map((n) => (
          <label key={n} className="cursor-pointer text-[30px] leading-none">
            <input
              type="radio"
              name={name}
              value={n}
              checked={value === n}
              onChange={() => onChange(n)}
              className="peer sr-only"
              aria-label={`${n} ${n === 1 ? "star" : "stars"}, ${WORDS[n]}`}
            />
            <span
              aria-hidden
              className={`block rounded-md px-0.5 peer-focus-visible:outline-2 peer-focus-visible:outline-ink ${
                n <= value ? "text-ink" : "text-muted/35 hover:text-muted"
              }`}
            >
              ★
            </span>
          </label>
        ))}
        <span className="ml-2 text-sm text-muted" aria-hidden>
          {WORDS[value]}
        </span>
      </div>
    </fieldset>
  );
}
