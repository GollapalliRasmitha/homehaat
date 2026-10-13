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
  { href: "/seller/orders", label: "Shop orders" }, // never just "Orders": buyers have "My orders"
  { href: "/seller/products", label: "Products" },
  { href: "/seller/requests", label: "Custom requests" },
  { href: "/seller/reviews", label: "Reviews" },
  { href: "/seller/settings", label: "Settings" },
];

/**
 * SellerShell: under the black SellerBar, every /seller page gets the tabs, a "Selling · <page>" label
 * and the shop itself (useSeller()).
 */
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
  const page = TABS.find((tab) => active(tab.href)) ?? TABS[0];
  const openOrders = user?.open_orders ?? 0;
  return (
    <SellerContext.Provider value={{ store, setStore }}>
      <nav
        aria-label="Selling"
        className="-mt-2 mb-7 flex gap-x-6 overflow-x-auto no-scrollbar border-b border-line sm:-mt-6 sm:gap-x-7"
      >
        {TABS.map((tab) => (
          <Link
            key={tab.href}
            href={tab.href}
            aria-current={active(tab.href) ? "page" : undefined}
            className={`-mb-px whitespace-nowrap border-b-2 py-3 text-base no-underline ${
              active(tab.href) ? "border-ink font-semibold text-ink" : "border-transparent font-medium text-muted hover:text-ink"
            }`}
          >
            {tab.label}
            {tab.href === "/seller/orders" && openOrders > 0 && (
              <span className="ml-1.5 rounded-full bg-ink px-1.5 py-px text-[12px] font-bold text-white" aria-label={`, ${openOrders} open`}>
                {openOrders}
              </span>
            )}
          </Link>
        ))}
      </nav>
      <div className="mb-6 flex flex-wrap items-center gap-3">
        {/* The page's one h1, styled as a label: "Selling · Shop orders" can't be confused with "My orders". */}
        <h1 className="eyebrow">Selling · {page.label}</h1>
        {!store.is_active && <span className="status st-cancelled">Paused: buyers can&apos;t order</span>}
      </div>
      {children}
    </SellerContext.Provider>
  );
}
