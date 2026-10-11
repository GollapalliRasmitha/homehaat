import Link from "next/link";

import { EmptyState } from "@/components/EmptyState";

export default function NotFound() {
  return (
    <EmptyState
      asPageTitle
      title="Page not found"
      text="This page doesn't exist, or it was removed."
      action={
        <Link href="/" className="btn btn-black">
          Go home
        </Link>
      }
    />
  );
}
