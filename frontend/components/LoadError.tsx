"use client";

import { errorMessage } from "@/lib/api/client";

import { EmptyState } from "./EmptyState";

/** Shown when a page couldn't load its data: the reason in plain words, and a Try again button. */
export function LoadError({ error, onRetry, title = "Couldn't load this page" }: { error: unknown; onRetry: () => void; title?: string }) {
  return (
    <div role="alert">
      <EmptyState
        title={title}
        text={errorMessage(error)}
        action={
          <button className="btn btn-black" onClick={onRetry}>
            Try again
          </button>
        }
      />
    </div>
  );
}
