"use client";

import { Search, ShoppingBag } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useSession } from "@/lib/session";

// Explore · Categories · Makers · Custom orders arrive in Stages 4–5.
const LINKS = [{ href: "/", label: "Explore" }];

export function Header() {
  const { user, bagCount } = useSession();
  const pathname = usePathname();

  return (
    <div className="border-b border-line bg-white">
      <header className="wrap flex min-h-[88px] flex-wrap items-center gap-x-8 gap-y-2 py-3">
        <Link href="/" className="text-[25px] font-extrabold tracking-[-0.04em] no-underline">
          homehaat
        </Link>
        <nav aria-label="Main" className="flex flex-1 gap-6">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`border-b-[1.5px] py-1.5 text-[17px] font-medium no-underline hover:border-ink ${
                pathname === link.href ? "border-ink" : "border-transparent"
              }`}
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-1">
          <Link
            href={user?.store_slug ? "/seller" : "/sell"}
            className="mr-4 hidden text-[17px] font-medium no-underline hover:underline sm:inline"
          >
            {user?.store_slug ? "My shop" : "Sell on HomeHaat"}
          </Link>
          <Link href="/" aria-label="Search" className="flex size-11 items-center justify-center rounded-full hover:bg-soft">
            <Search size={19} aria-hidden="true" />
          </Link>
          <Link
            href="/cart"
            aria-label={`Bag, ${bagCount} items`}
            className="relative flex size-11 items-center justify-center rounded-full hover:bg-soft"
          >
            <ShoppingBag size={19} aria-hidden="true" />
            {bagCount > 0 && (
              <span className="absolute right-0.5 top-1 flex h-[17px] min-w-[17px] items-center justify-center rounded-full bg-ink px-1 text-[10.5px] font-bold text-white">
                {bagCount}
              </span>
            )}
          </Link>
          <Link href={user ? "/account" : "/signin"} className="btn btn-white ml-3 h-12">
            {user ? (user.name.split(" ")[0] || "Account") : "Sign in"}
          </Link>
        </div>
      </header>
    </div>
  );
}
