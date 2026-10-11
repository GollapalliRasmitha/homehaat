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
    <span className="absolute right-0 top-0.5 flex h-[17px] min-w-[17px] items-center justify-center rounded-full bg-ink px-1 text-[10.5px] font-bold text-white sm:right-0.5 sm:top-1">
      {count}
    </span>
  );
}

const iconLink = "relative flex size-10 flex-none items-center justify-center rounded-full hover:bg-soft sm:size-11";

/**
 * Desktop (900px+): one 88px row: logo · links · Sell · icons · account pill (UI-UX.md).
 * Phones: a compact first row (logo, icons, small account button) and the links in one thin row
 * below that scrolls sideways, so the page content starts high and nothing is wider than the screen.
 */
export function Header() {
  const { user, bagCount } = useSession();
  const saved = useWishlist().length;
  const pathname = usePathname();
  const sell = user?.store_slug ? { href: "/seller", label: "My shop" } : { href: "/sell", label: "Sell on HomeHaat" };
  const isActive = (href: string) => pathname === href || pathname.startsWith(href + "/");
  const linkClass = (href: string) =>
    `whitespace-nowrap border-b-[1.5px] font-medium no-underline hover:border-ink ${
      isActive(href) ? "border-ink" : "border-transparent"
    }`;

  return (
    <div className="border-b border-line bg-white">
      <header className="wrap flex h-[52px] items-center gap-x-3 sm:h-16 min-[900px]:h-[88px] min-[900px]:gap-x-8">
        <Link href="/" className="flex-none text-[22px] font-extrabold tracking-[-0.04em] no-underline sm:text-[25px]">
          homehaat
        </Link>

        <nav aria-label="Main" className="hidden flex-1 gap-x-[30px] min-[900px]:flex">
          {LINKS.map((link) => (
            <Link key={link.href} href={link.href} aria-current={isActive(link.href) ? "page" : undefined} className={`py-1.5 text-[17px] ${linkClass(link.href)}`}>
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="ml-auto flex min-w-0 items-center gap-0.5 sm:gap-1">
          <Link href={sell.href} className="mr-3 hidden whitespace-nowrap text-[17px] font-medium no-underline hover:underline hover:underline-offset-4 min-[900px]:inline">
            {sell.label}
          </Link>
          <Link href="/explore" aria-label="Search" className={`${iconLink} hidden min-[400px]:flex`}>
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
          <Link
            href={user ? "/account" : "/signin"}
            aria-label={user ? `Account: ${user.name || user.email}` : undefined}
            className="btn btn-white ml-1 h-9 min-w-0 max-w-[96px] px-3 text-sm sm:ml-2 sm:h-12 sm:max-w-[160px] sm:px-5 sm:text-base"
          >
            {/* A long name is shortened with "…" so it can never push the page wider than the screen. */}
            <span className="truncate">{user ? user.name.split(" ")[0] || "Account" : "Sign in"}</span>
          </Link>
        </div>
      </header>

      {/* Phones and tablets: the links in one row that scrolls sideways if it doesn't fit. */}
      <nav aria-label="Main" className="wrap flex gap-x-5 overflow-x-auto no-scrollbar pb-1.5 text-[15px] leading-6 min-[900px]:hidden">
        {[...LINKS, sell].map((link) => (
          <Link key={link.href} href={link.href} aria-current={isActive(link.href) ? "page" : undefined} className={`py-1 ${linkClass(link.href)}`}>
            {link.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
