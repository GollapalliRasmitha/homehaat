import Link from "next/link";

import { EmptyState } from "@/components/EmptyState";
import { MakerCard } from "@/components/MakerCard";
import { ProductGrid } from "@/components/ProductCard";
import { listCategories, listStores, searchProducts } from "@/lib/api/catalog";
import { errorMessage } from "@/lib/api/client";
import type { Category, PublicStore, SearchPage } from "@/lib/api/types";
import { filtersToApi, filtersToQuery, readFilters } from "@/lib/explore";
import { PHOTOS } from "@/lib/photos";

import { ExploreControls } from "./ExploreControls";

/** Search & category page. All filters come from the URL, so results can be shared and bookmarked. */
export default async function ExplorePage({ searchParams }: PageProps<"/explore">) {
  const raw = await searchParams;
  const params = new URLSearchParams(
    Object.entries(raw).flatMap(([k, v]) => (typeof v === "string" ? [[k, v]] : Array.isArray(v) ? [[k, v[0]]] : [])),
  );
  const filters = readFilters(params);

  let found: SearchPage | null = null;
  let categories: Category[] = [];
  let makers: PublicStore[] = [];
  let loadError: unknown = null;
  try {
    [found, categories, makers] = await Promise.all([
      searchProducts(filtersToApi(filters)),
      listCategories(),
      filters.q ? listStores({ q: filters.q, limit: 4 }) : Promise.resolve([]), // "products and sellers"
    ]);
  } catch (error) {
    loadError = error;
  }

  const products = found?.results ?? [];
  const count = found?.count ?? 0;
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
      {found && (
        <p className="mt-1.5 text-muted" aria-live="polite">
          {count} {count === 1 ? "product" : "products"}
          {found.pages > 1 && ` · page ${found.page} of ${found.pages}`}
        </p>
      )}
      {found?.suggestion && (
        <p className="mt-2 text-[17px]">
          Did you mean{" "}
          <Link href={`/explore${filtersToQuery({ ...filters, q: found.suggestion, page: 1 })}`} className="font-semibold underline">
            {found.suggestion}
          </Link>
          ?
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
        <>
          <ProductGrid products={products} />
          {found && found.pages > 1 && (
            <nav aria-label="Pages of results" className="mt-10 flex items-center justify-center gap-3">
              {found.page > 1 ? (
                <Link href={`/explore${filtersToQuery({ ...filters, page: found.page - 1 })}`} className="btn btn-white" rel="prev">
                  Previous
                </Link>
              ) : (
                <span className="btn btn-white pointer-events-none opacity-40" aria-hidden>
                  Previous
                </span>
              )}
              <span className="text-[15px] text-muted" aria-current="page">
                Page {found.page} of {found.pages}
              </span>
              {found.page < found.pages ? (
                <Link href={`/explore${filtersToQuery({ ...filters, page: found.page + 1 })}`} className="btn btn-white" rel="next">
                  Next
                </Link>
              ) : (
                <span className="btn btn-white pointer-events-none opacity-40" aria-hidden>
                  Next
                </span>
              )}
            </nav>
          )}
        </>
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
