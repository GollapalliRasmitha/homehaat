"use client";

import Link from "next/link";

import { useSession } from "@/lib/session";

import { AccountMenu } from "./AccountMenu";

/**
 * Selling mode: on every /seller page this black bar replaces the shopping header, so it's always clear
 * which side of HomeHaat you're on. Phones: row 1 = SELLING pill, shop name, account; row 2 = back link.
 * "View my shop page" shows here from 1024px (below that it would squeeze the shop name; it's in the account menu).
 */
export function SellerBar() {
  const { user } = useSession();
  const back = (
    <Link href="/" className="whitespace-nowrap text-[15px] font-medium text-white no-underline hover:underline hover:underline-offset-4">
      ← Back to shopping
    </Link>
  );
  return (
    <div className="bg-ink text-white">
      <header className="wrap flex h-[56px] items-center gap-x-3 md:h-[72px] md:gap-x-4">
        <Link href="/seller" className="hidden flex-none text-[22px] font-extrabold tracking-[-0.04em] text-white no-underline md:inline sm:text-[24px]">
          homehaat
        </Link>
        <span className="flex-none rounded-full bg-white px-2.5 py-1 text-[11.5px] font-bold uppercase tracking-[0.1em] text-ink">
          Selling
        </span>
        <span className="min-w-0 truncate text-[15px] font-semibold md:text-[17px]">{user?.shop_name ?? ""}</span>
        <div className="ml-auto flex flex-none items-center gap-x-5">
          <span className="hidden md:inline">{back}</span>
          {user?.store_slug && (
            <Link
              href={`/store/${user.store_slug}`}
              className="hidden whitespace-nowrap text-[15px] font-medium text-white no-underline hover:underline hover:underline-offset-4 lg:inline"
            >
              View my shop page
            </Link>
          )}
          <AccountMenu dark />
        </div>
      </header>
      <div className="wrap pb-2.5 md:hidden">{back}</div>
    </div>
  );
}
