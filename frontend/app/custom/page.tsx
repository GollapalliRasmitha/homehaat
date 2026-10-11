import Link from "next/link";

import { EmptyState } from "@/components/EmptyState";
import { PHOTOS } from "@/lib/photos";

// Custom requests (describe it → the maker quotes → accept and pay) are built in Stage 5.
export default function CustomOrdersPage() {
  return (
    <>
      <h1 className="title">
        Custom <span className="serif">orders</span>
      </h1>
      <p className="mb-7 mt-1.5 max-w-[620px] text-muted">
        A photo cake for Saturday, a blouse in your design, a painting of your home. Describe it, the maker sends a
        price, and you pay only if you accept.
      </p>
      <EmptyState
        photoId={PHOTOS.crafts}
        title="Custom requests open soon"
        text="Soon you'll be able to send a request to any maker from their shop page. Until then, browse what they've made."
        action={
          <Link href="/makers" className="btn btn-black">
            See makers
          </Link>
        }
      />
    </>
  );
}
