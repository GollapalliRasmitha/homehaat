"use client";

import { ChevronDown } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";
import { toast } from "sonner";

import { signOut } from "@/lib/api/auth";
import { errorMessage } from "@/lib/api/client";
import { useSession } from "@/lib/session";

/**
 * The account button. Signed out: "Sign in". Signed in: a menu with two labelled groups,
 * BUYING (always) and SELLING · shop name (only with a shop), then Sign out.
 * A disclosure (button + list of links): Escape or a click outside closes it, and focus goes back to the button.
 */
export function AccountMenu({ dark = false }: { dark?: boolean }) {
  const { user, refresh } = useSession();
  const router = useRouter();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [seenPath, setSeenPath] = useState(pathname);
  const box = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const menuId = useId();

  // Following a link closes the menu (React's way to react to a new prop: during render).
  if (pathname !== seenPath) {
    setSeenPath(pathname);
    setOpen(false);
  }

  useEffect(() => {
    if (!open) return;
    const onPointer = (e: PointerEvent) => {
      if (!box.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        button.current?.focus();
      }
    };
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const pill = dark
    ? "border-white/35 bg-transparent text-white hover:border-white"
    : "btn-white";
  const size = "h-9 min-w-0 max-w-[110px] px-3 text-sm sm:h-12 sm:max-w-[160px] sm:px-5 sm:text-base";

  if (!user) {
    return (
      <Link href="/signin" className={`btn ${pill} ${size} ml-1 sm:ml-2`}>
        Sign in
      </Link>
    );
  }

  async function handleSignOut() {
    try {
      await signOut();
    } catch (error) {
      toast(`Couldn't sign out. ${errorMessage(error)}`);
      return;
    }
    setOpen(false);
    await refresh();
    toast("Signed out");
    router.push("/");
  }

  const item = "flex items-center justify-between gap-3 rounded-xl px-3 py-2.5 text-[15px] font-medium no-underline hover:bg-soft";
  const group = "px-3 pb-1 pt-2 text-[11.5px] font-bold uppercase tracking-[0.08em] text-muted";

  return (
    <div ref={box} className="relative ml-1 flex min-w-0 sm:ml-2">
      <button
        ref={button}
        type="button"
        className={`btn ${pill} ${size} gap-1 sm:gap-1.5`}
        aria-expanded={open}
        aria-controls={menuId}
        aria-label={`Account menu: ${user.name || user.email}`}
        onClick={() => setOpen((o) => !o)}
      >
        {/* A long name is shortened with "…" so it can never push the page wider than the screen. */}
        <span className="truncate">{user.name.split(" ")[0] || "Account"}</span>
        <ChevronDown size={16} aria-hidden className={`flex-none transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div
          id={menuId}
          className="absolute right-0 top-[calc(100%+8px)] z-50 w-[min(290px,calc(100vw-24px))] rounded-[18px] border border-line bg-white p-2 text-ink shadow-[0_12px_40px_rgba(0,0,0,0.12)]"
        >
          <p className="truncate px-3 pb-1 pt-1.5 text-sm text-muted">{user.email}</p>
          <nav aria-label="Buying">
            <p className={group}>Buying</p>
            <Link href="/orders" className={item}>
              My orders
            </Link>
            <Link href="/wishlist" className={item}>
              Wishlist
            </Link>
            <Link href="/custom#mine" className={item}>
              My custom requests
            </Link>
            <Link href="/account/addresses" className={item}>
              Saved addresses
            </Link>
          </nav>
          {user.store_slug && (
            <nav aria-label={`Selling: ${user.shop_name ?? "my shop"}`} className="mt-1 border-t border-line pt-1">
              <p className={`${group} truncate`}>
                Selling · <span className="normal-case tracking-normal">{user.shop_name}</span>
              </p>
              <Link href="/seller" className={item}>
                Seller dashboard
              </Link>
              <Link href="/seller/orders" className={item}>
                Shop orders
                {user.open_orders > 0 && (
                  <span
                    className="flex h-[20px] min-w-[20px] items-center justify-center rounded-full bg-ink px-1.5 text-[11.5px] font-bold text-white"
                    aria-label={`${user.open_orders} open`}
                  >
                    {user.open_orders}
                  </span>
                )}
              </Link>
              <Link href="/seller/products" className={item}>
                Products
              </Link>
              <Link href={`/store/${user.store_slug}`} className={item}>
                View my shop page
              </Link>
            </nav>
          )}
          <div className="mt-1 border-t border-line pt-1">
            <button type="button" className={`${item} w-full text-left`} onClick={handleSignOut}>
              Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
