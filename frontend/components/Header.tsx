"use client";

import { Heart, Search, ShoppingBag } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useSession } from "@/lib/session";
import { useWishlist } from "@/lib/wishlist";

const LINKS = [
  { href: "/explore", label: "Explore" },
  { href: "/categories", label: "Categories" },
  { href: "/makers", label: "Makers" },
  { href: "/custom", label: "Custom orders" },
];

/** A small black count badge, shown only when the count is above 0 (UI-UX.md). */
function CountBadge({ count }: { count: number }) {
  if (count <= 0) return null;
  return (
    <span className="absolute right-0.5 top-1 flex h-[17px] min-w-[17px] items-center justify-center rounded-full bg-ink px-1 text-[10.5px] font-bold text-white">
      {count}
    </span>
  );
}

const iconLink = "relative flex size-11 items-center justify-center rounded-full hover:bg-soft";

export function Header() {
  const { user, bagCount } = useSession();
  const saved = useWishlist().length;
  const pathname = usePathname();

  return (
    <div className="border-b border-line bg-white">
      {/* Under 900px the links move to their own row below the logo (UI-UX.md §8). */}
      <header className="wrap flex flex-wrap items-center gap-x-8 gap-y-1 py-3.5 min-[900px]:h-[88px] min-[900px]:flex-nowrap min-[900px]:py-0">
        <Link href="/" className="text-[25px] font-extrabold tracking-[-0.04em] no-underline">
          homehaat
        </Link>
        <nav aria-label="Main" className="order-3 flex basis-full flex-wrap gap-x-5 gap-y-0.5 min-[900px]:order-none min-[900px]:basis-auto min-[900px]:flex-1 min-[900px]:gap-x-[30px]">
          {LINKS.map((link) => {
            const active = pathname === link.href || pathname.startsWith(link.href + "/");
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={`border-b-[1.5px] py-1.5 text-base font-medium no-underline hover:border-ink min-[900px]:text-[17px] ${
                  active ? "border-ink" : "border-transparent"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
        <div className="ml-auto flex items-center gap-1">
          <Link
            href={user?.store_slug ? "/seller" : "/sell"}
            className="mr-3 hidden text-[17px] font-medium no-underline hover:underline hover:underline-offset-4 sm:inline"
          >
            {user?.store_slug ? "My shop" : "Sell on HomeHaat"}
          </Link>
          <Link href="/explore" aria-label="Search" className={iconLink}>
            <Search size={19} aria-hidden="true" />
          </Link>
          <Link href="/wishlist" aria-label={`Wishlist, ${saved} saved`} className={iconLink}>
            <Heart size={19} aria-hidden="true" />
            <CountBadge count={saved} />
          </Link>
          <Link href="/cart" aria-label={`Bag, ${bagCount} ${bagCount === 1 ? "item" : "items"}`} className={iconLink}>
            <ShoppingBag size={19} aria-hidden="true" />
            <CountBadge count={bagCount} />
          </Link>
          <Link href={user ? "/account" : "/signin"} className="btn btn-white ml-2 h-12 px-5 sm:ml-3">
            {user ? user.name.split(" ")[0] || "Account" : "Sign in"}
          </Link>
        </div>
      </header>
    </div>
  );
}
