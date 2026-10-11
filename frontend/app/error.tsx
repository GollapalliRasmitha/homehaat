"use client";

import Link from "next/link";
import { useEffect } from "react";

import { EmptyState } from "@/components/EmptyState";
import { errorMessage } from "@/lib/api/client";

/**
 * Safety net: if any page still throws while rendering (on the server or in the browser),
 * show a friendly panel inside the normal layout instead of a crash screen.
 */
export default function PageError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error); // keeps the technical details for debugging
  }, [error]);

  // Errors from server pages arrive without their class, so we can only trust our own message wording.
  const message = error.name === "ApiError" ? errorMessage(error) : "Something went wrong. Please try again.";
  return (
    <div role="alert">
      <EmptyState
        title="This page didn't load"
        text={message}
        action={
          <div className="flex flex-wrap justify-center gap-2.5">
            <button className="btn btn-black" onClick={reset}>
              Try again
            </button>
            <Link href="/" className="btn btn-white">
              Go home
            </Link>
          </div>
        }
      />
    </div>
  );
}
