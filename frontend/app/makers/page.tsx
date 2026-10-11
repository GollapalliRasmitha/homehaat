import Link from "next/link";

import { EmptyState } from "@/components/EmptyState";
import { MakerGrid } from "@/components/MakerCard";
import { listStores } from "@/lib/api/catalog";
import { errorMessage } from "@/lib/api/client";
import type { PublicStore } from "@/lib/api/types";

export default async function MakersPage() {
  let stores: PublicStore[] | null = null;
  let loadError: unknown = null;
  try {
    stores = await listStores();
  } catch (error) {
    loadError = error;
  }

  return (
    <>
      <div className="mb-4 text-sm text-muted">
        <Link href="/" className="text-muted">
          Home
        </Link>{" "}
        / Makers
      </div>
      <h1 className="title">
        Makers <span className="serif">near you</span>
      </h1>
      <p className="mb-7 mt-1.5 text-muted">Home bakers, cooks, artists, tailors and crafters.</p>

      {stores === null ? (
        <EmptyState title="Couldn't load makers" text={errorMessage(loadError)} />
      ) : stores.length === 0 ? (
        <EmptyState
          title="No makers yet"
          text="Be the first home maker on HomeHaat. It takes two minutes."
          action={
            <Link href="/sell" className="btn btn-black">
              Open your shop
            </Link>
          }
        />
      ) : (
        <MakerGrid stores={stores} />
      )}

      <div className="panel mt-7 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-[22px]">Make things at home?</h2>
          <p className="mt-1 text-muted">Open your shop in two minutes and start adding products.</p>
        </div>
        <Link href="/sell" className="btn btn-black">
          Open your shop
        </Link>
      </div>
    </>
  );
}
