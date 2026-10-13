"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AddressForm } from "@/components/AddressForm";
import { LoadError } from "@/components/LoadError";
import { listAddresses } from "@/lib/api/auth";
import type { Address } from "@/lib/api/types";
import { useSession } from "@/lib/session";

/** Buying · Saved addresses: see them, fix one that breaks the address rules, or add another. */
export default function SavedAddressesPage() {
  const { user, signedOut } = useSession();
  const router = useRouter();
  const [addresses, setAddresses] = useState<Address[] | null>(null);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const [editing, setEditing] = useState<number | "new" | null>(null);

  useEffect(() => {
    if (signedOut) return router.replace("/signin?next=/account/addresses");
    if (!user) return;
    listAddresses()
      .then(setAddresses)
      .catch(setLoadError);
  }, [user, signedOut, router, attempt]);

  if (loadError) {
    const retry = () => {
      setLoadError(null);
      setAttempt((n) => n + 1);
    };
    return <LoadError error={loadError} onRetry={retry} title="Couldn't load your addresses" />;
  }
  if (!addresses) return <p className="text-muted">Loading your addresses…</p>;

  const saved = (a: Address) => {
    setAddresses(addresses.some((x) => x.id === a.id) ? addresses.map((x) => (x.id === a.id ? a : x)) : [a, ...addresses]);
    setEditing(null);
  };

  return (
    <div className="mx-auto max-w-[760px]">
      <p className="eyebrow">Buying · Saved addresses</p>
      <h1 className="title mt-1">Saved addresses</h1>
      <p className="mt-1.5 text-muted">Used at checkout. Makers see the address only for orders you place with them.</p>

      <div className="mt-6 flex flex-col gap-3">
        {addresses.length === 0 && editing !== "new" && (
          <p className="panel text-muted">No saved addresses yet. You can add one here or at checkout.</p>
        )}
        {addresses.map((a) =>
          editing === a.id ? (
            <div key={a.id} className="panel">
              <AddressForm address={a} onSaved={saved} onCancel={() => setEditing(null)} />
            </div>
          ) : (
            <div key={a.id} className="panel flex flex-wrap items-start gap-3">
              <div className="min-w-0 flex-[1_1_240px]">
                <b>{a.name}</b> · {a.phone}
                <p className="text-muted">
                  {a.line1}
                  {a.line2 && `, ${a.line2}`}, {a.city} {a.pincode}
                </p>
                {Object.keys(a.problems).length > 0 && (
                  <p className="mt-1.5 text-sm font-semibold text-error">Please update this address before your next order.</p>
                )}
              </div>
              <button className="btn btn-white" onClick={() => setEditing(a.id)}>
                {Object.keys(a.problems).length > 0 ? "Update address" : "Edit"}
              </button>
            </div>
          ),
        )}
        {editing === "new" ? (
          <div className="panel">
            <AddressForm defaultName={user?.name ?? ""} onSaved={saved} onCancel={() => setEditing(null)} />
          </div>
        ) : (
          <button className="btn btn-black self-start" onClick={() => setEditing("new")}>
            Add an address
          </button>
        )}
      </div>
      <Link href="/account" className="mt-8 inline-block text-muted">
        ← Back to my account
      </Link>
    </div>
  );
}
