"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { LoadError } from "@/components/LoadError";
import { RequestCard } from "@/components/RequestCard";
import { listStores } from "@/lib/api/catalog";
import { listMyRequests } from "@/lib/api/requests";
import type { CustomRequest, PublicStore } from "@/lib/api/types";
import { PHOTOS } from "@/lib/photos";
import { useSession } from "@/lib/session";

import { BuyerRequestActions } from "./BuyerRequestActions";
import { RequestForm } from "./RequestForm";

export default function CustomOrdersPage() {
  // Suspense: the page reads ?maker= from the URL (the store page's "Request a custom order" button).
  return (
    <Suspense>
      <CustomOrders />
    </Suspense>
  );
}

function CustomOrders() {
  const { user, signedOut } = useSession();
  const initialMaker = useSearchParams().get("maker") ?? "";
  const [makers, setMakers] = useState<PublicStore[] | null>(null);
  const [requests, setRequests] = useState<CustomRequest[] | null>(null);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    listStores()
      .then(setMakers)
      .catch(setLoadError);
  }, [attempt]);

  useEffect(() => {
    if (!user) return;
    listMyRequests()
      .then(setRequests)
      .catch(setLoadError);
  }, [user, attempt]);

  // You can't send a request to your own shop.
  const askable = (makers ?? []).filter((m) => m.slug !== user?.store_slug);
  const replace = (r: CustomRequest) => setRequests((list) => (list ?? []).map((x) => (x.id === r.id ? r : x)));

  return (
    <>
      <h1 className="title">
        Custom <span className="serif">orders</span>
      </h1>
      <p className="mb-7 mt-1.5 max-w-[620px] text-muted">
        A photo cake for Saturday, a blouse in your design, a painting of your home. Describe it, the maker sends a
        price, and you pay only if you accept.
      </p>

      {loadError ? (
        <LoadError
          error={loadError}
          onRetry={() => {
            setLoadError(null);
            setAttempt((n) => n + 1);
          }}
        />
      ) : makers === null ? (
        <p className="text-muted">Loading…</p>
      ) : askable.length === 0 ? (
        <EmptyState
          photoId={PHOTOS.crafts}
          title="No makers to ask yet"
          text="When makers open shops, you can send them custom requests here."
          action={
            <Link href="/sell" className="btn btn-black">
              Open your shop
            </Link>
          }
        />
      ) : (
        <div className="flex flex-wrap items-start gap-7">
          <div className="min-w-0 flex-[999_1_480px]">
            {user ? (
              <RequestForm makers={askable} initialMaker={initialMaker} onSent={(r) => setRequests((list) => [r, ...(list ?? [])])} />
            ) : signedOut ? (
              <div className="panel flex flex-col items-start gap-3">
                <h2 className="text-[22px]">Sign in to send a request</h2>
                <p className="text-muted">The maker needs to know who to reply to.</p>
                <Link href={`/signin?next=${encodeURIComponent(`/custom${initialMaker ? `?maker=${initialMaker}` : ""}`)}`} className="btn btn-black">
                  Sign in
                </Link>
              </div>
            ) : (
              <p className="text-muted">Loading…</p>
            )}
          </div>

          {user && (
            <section className="flex min-w-0 flex-[1_1_340px] flex-col gap-3.5" aria-labelledby="mine">
              <h2 id="mine" className="text-[22px]">
                Your requests
              </h2>
              {requests === null ? (
                <p className="text-muted">Loading…</p>
              ) : requests.length === 0 ? (
                <div className="rounded-[24px] bg-soft px-5 py-8 text-center text-muted">No requests yet.</div>
              ) : (
                requests.map((r) => (
                  <RequestCard key={r.id} request={r} who="buyer">
                    <BuyerRequestActions request={r} onChange={replace} />
                  </RequestCard>
                ))
              )}
            </section>
          )}
        </div>
      )}
    </>
  );
}
