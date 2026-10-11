import Link from "next/link";

import { EmptyState } from "@/components/EmptyState";
import { MakerCard } from "@/components/MakerCard";
import { ProductGrid } from "@/components/ProductCard";
import { listCategories, listProducts, listStores } from "@/lib/api/catalog";
import { errorMessage } from "@/lib/api/client";
import type { Category, Product, PublicStore } from "@/lib/api/types";
import { filtersToApi, readFilters } from "@/lib/explore";
import { PHOTOS } from "@/lib/photos";

import { ExploreControls } from "./ExploreControls";

/** Search & category page. All filters come from the URL, so results can be shared and bookmarked. */
export default async function ExplorePage({ searchParams }: PageProps<"/explore">) {
  const raw = await searchParams;
  const params = new URLSearchParams(
    Object.entries(raw).flatMap(([k, v]) => (typeof v === "string" ? [[k, v]] : Array.isArray(v) ? [[k, v[0]]] : [])),
  );
  const filters = readFilters(params);

  let products: Product[] = [];
  let categories: Category[] = [];
  let makers: PublicStore[] = [];
  let loadError: unknown = null;
  try {
    [products, categories, makers] = await Promise.all([
      listProducts(filtersToApi(filters)),
      listCategories(),
      filters.q ? listStores({ q: filters.q, limit: 4 }) : Promise.resolve([]), // "products and sellers"
    ]);
  } catch (error) {
    loadError = error;
  }

  const category = categories.find((c) => c.slug === filters.category);
  const anyFilter = filters.q || filters.category || filters.inStock || filters.minRupees || filters.maxRupees;

  return (
    <>
      <div className="mb-4 text-sm text-muted">
        <Link href="/" className="text-muted">
          Home
        </Link>{" "}
        / Explore
      </div>
      <h1 className="title">
        {filters.q ? (
          <>
            Results for <span className="serif">“{filters.q}”</span>
          </>
        ) : category ? (
          category.name
        ) : (
          <>
            Explore <span className="serif">handmade</span>
          </>
        )}
      </h1>
      {!loadError && (
        <p className="mt-1.5 text-muted" aria-live="polite">
          {products.length} {products.length === 1 ? "product" : "products"}
          {products.length === 60 && " (showing the first 60)"}
        </p>
      )}

      <ExploreControls filters={filters} categories={categories} />

      {makers.length > 0 && (
        <section aria-labelledby="makers-found" className="mb-10">
          <h2 id="makers-found" className="mb-4 text-[22px]">
            Makers
          </h2>
          <div className="grid gap-3.5 sm:grid-cols-2">
            {makers.map((s) => (
              <MakerCard key={s.slug} store={s} />
            ))}
          </div>
        </section>
      )}

      {loadError ? (
        <EmptyState
          title="Couldn't load products"
          text={errorMessage(loadError)}
          action={
            <Link href="/explore" className="btn btn-black">
              Try again
            </Link>
          }
        />
      ) : products.length > 0 ? (
        <ProductGrid products={products} />
      ) : anyFilter ? (
        <EmptyState
          title="No products match"
          text="Try another word, or clear the filters."
          action={
            <Link href="/explore" className="btn btn-white">
              Clear filters
            </Link>
          }
        />
      ) : (
        <EmptyState
          photoId={PHOTOS.cakes}
          title="No products yet"
          text="When makers add products, you'll find them here."
          action={
            <Link href="/sell" className="btn btn-black">
              Open your shop
            </Link>
          }
        />
      )}
    </>
  );
}
