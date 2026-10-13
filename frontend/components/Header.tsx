"use client";

import { Heart, Search, ShoppingBag } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useSession } from "@/lib/session";
import { useWishlist } from "@/lib/wishlist";

import { AccountMenu } from "./AccountMenu";
import { SellerBar } from "./SellerBar";

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

/** The only seller link in the shopping header: a small outlined pill. `className` sets where it shows. */
function SellPill({ hasShop, className }: { hasShop: boolean; className: string }) {
  return (
    <Link
      href={hasShop ? "/seller" : "/sell"}
      className={`flex-none items-center whitespace-nowrap rounded-full border border-ink font-semibold no-underline hover:bg-ink hover:text-white ${className}`}
    >
      {hasShop ? "Switch to selling" : "Sell on HomeHaat"}
    </Link>
  );
}

/**
 * Shopping mode (every page except /seller): logo · Explore · Categories · Makers · Custom orders, then
 * search, wishlist, bag and the account menu. On /seller pages the black SellerBar replaces it.
 *
 * Wide screens (1200px+): one 88px row: logo · links · Sell/My shop · icons · account pill (UI-UX.md).
 * Below 1200px: a compact first row (logo, icons, account button) and the links in one thin row below
 * that scrolls sideways. The single row needs ~1,000px of room, which only fits from 1200px; at e.g.
 * 1100px it pushed the account button off the screen. Long names are always shortened with "…".
 */
export function Header() {
  const { user, bagCount } = useSession();
  const saved = useWishlist().length;
  const pathname = usePathname();
  const hasShop = Boolean(user?.store_slug);
  const isActive = (href: string) => pathname === href || pathname.startsWith(href + "/");
  const linkClass = (href: string) =>
    `whitespace-nowrap border-b-[1.5px] font-medium no-underline hover:border-ink ${
      isActive(href) ? "border-ink" : "border-transparent"
    }`;

  if (pathname === "/seller" || pathname.startsWith("/seller/")) return <SellerBar />;

  return (
    <div className="border-b border-line bg-white">
      <header className="wrap flex h-[52px] items-center gap-x-3 sm:h-16 wide:h-[88px] wide:gap-x-6">
        <Link href="/" className="flex-none text-[22px] font-extrabold tracking-[-0.04em] no-underline sm:text-[25px]">
          homehaat
        </Link>

        <nav aria-label="Main" className="hidden min-w-0 flex-1 gap-x-6 wide:flex">
          {LINKS.map((link) => (
            <Link key={link.href} href={link.href} aria-current={isActive(link.href) ? "page" : undefined} className={`py-1.5 text-[17px] ${linkClass(link.href)}`}>
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="ml-auto flex min-w-0 items-center gap-0.5 sm:gap-1">
          <SellPill hasShop={hasShop} className="mr-2 hidden h-8 px-3.5 text-[13.5px] wide:inline-flex" />
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
          <AccountMenu />
        </div>
      </header>

      {/* Phones and tablets: the links in one row that scrolls sideways if it doesn't fit. */}
      <nav aria-label="Main" className="wrap flex items-center gap-x-5 overflow-x-auto no-scrollbar pb-1.5 text-[15px] leading-6 wide:hidden">
        {LINKS.map((link) => (
          <Link key={link.href} href={link.href} aria-current={isActive(link.href) ? "page" : undefined} className={`py-1 ${linkClass(link.href)}`}>
            {link.label}
          </Link>
        ))}
        <SellPill hasShop={hasShop} className="inline-flex h-7 px-3 text-[13px]" />
      </nav>
    </div>
  );
}
