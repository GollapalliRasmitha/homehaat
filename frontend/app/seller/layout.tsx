"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { LoadError } from "@/components/LoadError";
import { getMyStore } from "@/lib/api/seller";
import type { Store } from "@/lib/api/types";
import { SellerContext } from "@/lib/seller-context";
import { useSession } from "@/lib/session";

const TABS = [
  { href: "/seller", label: "Overview" },
  { href: "/seller/orders", label: "Orders" },
  { href: "/seller/products", label: "Products" },
  { href: "/seller/requests", label: "Custom requests" },
  { href: "/seller/reviews", label: "Reviews" },
  { href: "/seller/settings", label: "Store settings" },
];

/** SellerShell: every /seller page gets the shop name, the tabs, and the shop itself (useSeller()). */
export default function SellerLayout({ children }: { children: React.ReactNode }) {
  const { user, signedOut } = useSession();
  const router = useRouter();
  const pathname = usePathname();
  const [store, setStore] = useState<Store | null>(null);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (signedOut) return router.replace(`/signin?next=${pathname}`);
    if (!user) return; // still loading, or the server is unreachable (the banner says so)
    if (!user.store_slug) return router.replace("/sell");
    getMyStore()
      .then(setStore)
      .catch(setLoadError);
    // pathname is left out on purpose: switching tabs shouldn't reload the shop
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, signedOut, router, attempt]);

  if (loadError) {
    const retry = () => {
      setLoadError(null);
      setAttempt((n) => n + 1);
    };
    return <LoadError error={loadError} onRetry={retry} title="Couldn't load your shop" />;
  }
  if (!store) return <p className="text-muted">Loading your shop…</p>;

  const active = (href: string) => (href === "/seller" ? pathname === "/seller" : pathname.startsWith(href));
  return (
    <SellerContext.Provider value={{ store, setStore }}>
      <div className="flex flex-wrap items-center gap-3">
        <p className="eyebrow">My shop</p>
        {!store.is_active && <span className="status st-cancelled">Paused: buyers can&apos;t order</span>}
      </div>
      <h1 className="title mt-1">{store.name}</h1>
      <nav aria-label="Shop dashboard" className="mb-7 mt-5 flex flex-wrap gap-x-7 gap-y-1 border-b border-line">
        {TABS.map((tab) => (
          <Link
            key={tab.href}
            href={tab.href}
            aria-current={active(tab.href) ? "page" : undefined}
            className={`-mb-px border-b-2 py-3 text-base no-underline ${
              active(tab.href) ? "border-ink font-semibold text-ink" : "border-transparent font-medium text-muted hover:text-ink"
            }`}
          >
            {tab.label}
          </Link>
        ))}
      </nav>
      {children}
    </SellerContext.Provider>
  );
}
