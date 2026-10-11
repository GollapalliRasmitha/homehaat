"use client";

import { Share2 } from "lucide-react";
import { toast } from "sonner";

/** Uses the phone's share sheet when there is one; otherwise copies the link. */
export function ShareButton({ title }: { title: string }) {
  async function share() {
    const url = window.location.href;
    if (navigator.share) {
      try {
        await navigator.share({ title, url });
      } catch {
        // the buyer closed the share sheet: nothing to do
      }
      return;
    }
    try {
      await navigator.clipboard.writeText(url);
      toast("Link copied");
    } catch {
      toast(`Copy this link: ${url}`);
    }
  }
  return (
    <button type="button" className="btn btn-white" onClick={share}>
      <Share2 size={17} aria-hidden="true" />
      Share
    </button>
  );
}
