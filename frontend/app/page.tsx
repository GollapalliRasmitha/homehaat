import Image from "next/image";
import Link from "next/link";

import { CategoryGrid } from "@/components/CategoryTile";
import { EmptyState } from "@/components/EmptyState";
import { HeroSearch } from "@/components/HeroSearch";
import { MakerGrid } from "@/components/MakerCard";
import { ProductGrid } from "@/components/ProductCard";
import { SectionHead } from "@/components/SectionHead";
import { ShowcaseCard } from "@/components/ShowcaseCard";
import { listCategories, listProducts, listStores } from "@/lib/api/catalog";
import { PHOTOS, unsplash } from "@/lib/photos";

const WEEK_MS = 7 * 24 * 60 * 60 * 1000;

/** Each section loads on its own: one failing API call shows that section's message, not a broken page. */
async function settle<T>(promise: Promise<T>): Promise<T | null> {
  try {
    return await promise;
  } catch {
    return null;
  }
}

export default async function HomePage() {
  const [categories, fresh, trending, makers] = await Promise.all([
    settle(listCategories()),
    settle(listProducts({ sort: "newest", limit: 8 })),
    settle(listProducts({ sort: "trending", limit: 4 })), // only products with real recent orders
    settle(listStores({ limit: 6 })),
  ]);

  // Say "this week" only if something really is from this week (no invented claims).
  const loadedAt = new Date().getTime();
  const reallyThisWeek = fresh?.some((p) => loadedAt - new Date(p.created_at).getTime() < WEEK_MS);
  const openShop = (
    <Link href="/sell" className="btn btn-black">
      Open your shop
    </Link>
  );

  return (
    <>
      <section className="flex flex-col items-center pb-14 pt-6 text-center sm:pb-20 sm:pt-12">
        <p className="eyebrow mb-6 sm:mb-8">Handmade by people near you</p>
        <h1 className="text-[clamp(48px,8.4vw,104px)] leading-[0.95] tracking-[-0.055em]">
          Made at home.
          <span className="serif mt-1.5 block text-[1.04em] leading-[1.02] tracking-[-0.03em]">Made for you.</span>
        </h1>
        <p className="mt-8 max-w-[620px] text-[clamp(17px,1.5vw,21px)] leading-[1.7] text-[#3b3b3b]">
          Cakes, pickles, art and tailoring from home makers in your neighbourhood. One bag, many makers, one payment.
        </p>
        <HeroSearch />
      </section>

      <div className="grid gap-5 min-[900px]:grid-cols-3">
        <ShowcaseCard href="/explore?category=cakes" title="Cakes & bakes" subtitle="For birthdays and Sundays" photoId={PHOTOS.cakes} tint="var(--blush)" priority />
        <ShowcaseCard href="/explore?category=pickles" title="Pickles & snacks" subtitle="From home kitchens" photoId={PHOTOS.pickles} tint="var(--sand)" priority />
        <ShowcaseCard href="/explore?category=art" title="Art & gifts" subtitle="Painted and made by hand" photoId={PHOTOS.art} tint="var(--stone)" priority />
      </div>

      <section className="pt-16" aria-labelledby="cats">
        <SectionHead id="cats" title="Browse by" accent="category" link={{ href: "/categories", label: "All categories" }} />
        {categories ? <CategoryGrid categories={categories} /> : <p className="text-muted">Categories couldn&apos;t load. Please refresh.</p>}
      </section>

      {trending && trending.length > 0 && (
        <section className="pt-[72px]" aria-labelledby="trending">
          <SectionHead id="trending" title="Trending" accent="nearby" link={{ href: "/explore", label: "See all" }} />
          <ProductGrid products={trending} />
        </section>
      )}

      <section className="pt-[72px]" aria-labelledby="fresh">
        <SectionHead
          id="fresh"
          title={reallyThisWeek ? "Fresh" : "Newest"}
          accent={reallyThisWeek ? "this week" : "finds"}
          link={fresh?.length ? { href: "/explore?sort=newest", label: "Explore" } : undefined}
        />
        {fresh === null ? (
          <EmptyState title="Couldn't load products" text="Our server had a problem. Please try again in a moment." />
        ) : fresh.length === 0 ? (
          <EmptyState
            photoId={PHOTOS.cakes}
            title="Handmade finds will appear here"
            text="No products yet. Makers add their cakes, pickles, art and more from their shop."
            action={openShop}
          />
        ) : (
          <ProductGrid products={fresh} />
        )}
      </section>

      <section className="mt-[72px] flex flex-wrap items-center gap-7 rounded-[30px] bg-ink p-[clamp(28px,5vw,64px)] text-white">
        <div className="flex min-w-0 flex-[1_1_380px] flex-col items-start gap-3.5">
          <span className="text-[13px] font-semibold uppercase tracking-[0.14em] text-[#bdbdbd]">Custom orders</span>
          <h2 className="text-[clamp(34px,4.4vw,58px)] leading-none">
            Can&apos;t find it?
            <br />
            <span className="serif text-[1.08em]">Ask a maker to make it.</span>
          </h2>
          <p className="max-w-[480px] text-lg text-[#cfcfcf]">
            A photo cake for Saturday, a blouse in your design, a painting of your home. Describe it, get a quote, and pay
            only when you approve.
          </p>
          {/* On black sections the primary button turns white (UI-UX.md). */}
          <Link href="/custom" className="btn btn-lg bg-white text-ink hover:bg-[#ededed]">
            Request a custom order
          </Link>
        </div>
        <div className="relative aspect-[4/3] min-w-[220px] flex-[0_1_360px] overflow-hidden rounded-[22px]">
          <Image src={unsplash(PHOTOS.crafts, 900)} alt="" fill sizes="360px" className="object-cover" />
        </div>
      </section>

      <section className="pt-[72px]" aria-labelledby="makers">
        <SectionHead
          id="makers"
          title="Makers"
          accent="near you"
          link={makers?.length ? { href: "/makers", label: "All makers" } : undefined}
        />
        {makers === null ? (
          <EmptyState title="Couldn't load makers" text="Our server had a problem. Please try again in a moment." />
        ) : makers.length === 0 ? (
          <EmptyState title="No makers yet" text="Be the first home maker on HomeHaat. It takes two minutes." action={openShop} />
        ) : (
          <MakerGrid stores={makers} />
        )}
      </section>
    </>
  );
}
