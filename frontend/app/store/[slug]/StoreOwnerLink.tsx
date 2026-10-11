"use client";

import Link from "next/link";

import { useSession } from "@/lib/session";

/** The shop's owner sees "Manage my shop"; everyone else sees "Request a custom order". */
export function StoreOwnerLink({ slug }: { slug: string }) {
  const { user } = useSession();
  if (user?.store_slug === slug) {
    return (
      <Link href="/seller" className="btn btn-black">
        Manage my shop
      </Link>
    );
  }
  return (
    <Link href={`/custom?maker=${slug}`} className="btn btn-black">
      Request a custom order
    </Link>
  );
}
