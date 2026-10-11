import { EmptyState } from "@/components/EmptyState";
import { PHOTOS } from "@/lib/photos";

// Custom requests ("photo cake for Saturday") arrive in Stage 5.
export default function SellerRequestsPage() {
  return (
    <EmptyState
      photoId={PHOTOS.crafts}
      title="No custom requests yet"
      text="Soon buyers will be able to ask you to make something special. You'll reply with a price here."
    />
  );
}
