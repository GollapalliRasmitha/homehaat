import Link from "next/link";

import { EmptyState } from "@/components/EmptyState";
import { ProductCard } from "@/components/ProductCard";
import { listProducts } from "@/lib/api/catalog";
import type { Product } from "@/lib/api/types";
import { PHOTOS } from "@/lib/photos";

// Stage 1: a simple product list. The full home page (showcase, categories, makers) is Stage 4.
export default async function HomePage() {
  let products: Product[] | null = null;
  try {
    products = await listProducts();
  } catch {
    products = null; // the API is down: show an error state instead of crashing
  }

  return (
    <>
      <section className="flex flex-col items-center pb-16 pt-6 text-center">
        <p className="eyebrow mb-6">Handmade by people near you</p>
        <h1 className="text-[clamp(44px,7vw,88px)] leading-[0.95] tracking-[-0.055em]">
          Made at home.
          <span className="serif mt-1.5 block">Made for you.</span>
        </h1>
        <p className="mt-7 max-w-[620px] text-lg leading-relaxed text-[#3b3b3b]">
          Cakes, pickles, art and tailoring from home makers in your neighbourhood. One bag, many makers, one
          payment.
        </p>
      </section>

      <section aria-labelledby="fresh">
        <h2 id="fresh" className="mb-7 text-[clamp(30px,3.6vw,46px)] leading-tight">
          Fresh <span className="serif">this week</span>
        </h2>
        {products === null ? (
          <EmptyState
            title="Couldn't load products"
            text="Our server had a problem. Please try again in a moment."
            action={
              <Link href="/" className="btn btn-black">
                Try again
              </Link>
            }
          />
        ) : products.length === 0 ? (
          <EmptyState
            photoId={PHOTOS.cakes}
            title="Handmade finds will appear here"
            text="No products yet. Makers add their cakes, pickles, art and more from their shop."
            action={
              <Link href="/sell" className="btn btn-black">
                Open your shop
              </Link>
            }
          />
        ) : (
          <div className="grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-[22px]">
            {products.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        )}
      </section>
    </>
  );
}
