"use client";

import { useState } from "react";

import { errorMessage } from "@/lib/api/client";
import { useSession } from "@/lib/session";

/** A thin bar under the header when the server can't be reached, with Try again. Hidden otherwise. */
export function ServerStatus() {
  const { serverError, refresh } = useSession();
  const [busy, setBusy] = useState(false);
  if (!serverError) return null;

  async function retry() {
    setBusy(true);
    await refresh();
    setBusy(false);
  }

  return (
    <div role="alert" className="border-b border-line bg-soft">
      <div className="wrap flex flex-wrap items-center justify-between gap-3 py-3 text-[15px]">
        <span>{errorMessage(serverError)}</span>
        <button className="btn btn-white h-10" onClick={retry} disabled={busy}>
          {busy ? "Trying…" : "Try again"}
        </button>
      </div>
    </div>
  );
}
