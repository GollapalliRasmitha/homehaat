"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";

import { StoreForm } from "@/components/StoreForm";
import { useSession } from "@/lib/session";

export default function SellPage() {
  const { user, signedOut, refresh } = useSession();
  const router = useRouter();
  const justOpened = useRef(false); // we're about to go to "Add your first product": don't also go to /seller

  useEffect(() => {
    if (signedOut) router.replace("/signin?next=/sell");
    if (user?.store_slug && !justOpened.current) router.replace("/seller");
  }, [user, signedOut, router]);

  if (!user || user.store_slug) return <p className="text-muted">Loading…</p>;

  return (
    <div className="mx-auto max-w-[720px]">
      <h1 className="title">Open your shop</h1>
      <p className="mb-6 mt-1.5 text-muted">Tell buyers who you are and how you deliver. You can change all of this later.</p>
      <StoreForm
        onSaved={async () => {
          justOpened.current = true;
          await refresh(); // you're a seller now: the header shows "My shop"
          router.push("/seller/products/new");
        }}
      />
    </div>
  );
}
