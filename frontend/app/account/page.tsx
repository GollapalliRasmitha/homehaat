"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { signOut } from "@/lib/api/auth";
import { useSession } from "@/lib/session";

// Stage 1: a minimal account page. Profile, saved addresses and "Delete my account" come later.
export default function AccountPage() {
  const { user, loading, refresh } = useSession();
  const router = useRouter();

  if (loading) return <p className="text-muted">Loading…</p>;
  if (!user) {
    return (
      <div className="panel mx-auto flex max-w-[520px] flex-col gap-3">
        <h1 className="title text-[32px]">You&apos;re signed out</h1>
        <Link href="/signin?next=/account" className="btn btn-black self-start">
          Sign in
        </Link>
      </div>
    );
  }

  async function handleSignOut() {
    await signOut();
    await refresh();
    toast("Signed out");
    router.push("/");
  }

  return (
    <div className="panel mx-auto flex max-w-[560px] flex-col gap-3">
      <h1 className="title text-[32px]">Hi{user.name ? `, ${user.name.split(" ")[0]}` : ""}</h1>
      <p className="text-muted">{user.email}</p>
      <div className="flex flex-wrap gap-2.5">
        <Link href="/orders" className="btn btn-white">
          My orders
        </Link>
        <Link href={user.store_slug ? "/seller" : "/sell"} className="btn btn-white">
          {user.store_slug ? "My shop" : "Open your shop"}
        </Link>
        <button className="btn btn-white" onClick={handleSignOut}>
          Sign out
        </button>
      </div>
    </div>
  );
}
