"use client";

import { Heart } from "lucide-react";
import { toast } from "sonner";

import { toggleWishlist, useWishlist } from "@/lib/wishlist";

/** The heart. "icon" = round white button on product photos; "large" = Save / Saved pill on the product page. */
export function WishlistButton({
  productId,
  productName,
  variant = "icon",
}: {
  productId: number;
  productName: string;
  variant?: "icon" | "large";
}) {
  const saved = useWishlist().includes(productId);

  function toggle(event: React.MouseEvent) {
    event.preventDefault(); // the heart sits on a link to the product: don't open it
    const nowSaved = toggleWishlist(productId);
    toast(nowSaved ? "Saved to your wishlist" : "Removed from your wishlist");
  }

  const heart = <Heart size={variant === "icon" ? 20 : 19} aria-hidden="true" fill={saved ? "currentColor" : "none"} />;
  if (variant === "large") {
    return (
      <button type="button" className="btn btn-white btn-lg" onClick={toggle} aria-pressed={saved}>
        {heart}
        {saved ? "Saved" : "Save"}
      </button>
    );
  }
  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={saved}
      aria-label={`${saved ? "Remove from" : "Save to"} wishlist: ${productName}`}
      className="absolute right-3.5 top-3.5 flex size-[42px] items-center justify-center rounded-full bg-white transition-transform active:scale-110"
    >
      {heart}
    </button>
  );
}
