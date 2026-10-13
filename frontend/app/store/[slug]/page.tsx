import { MapPin } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { tintVar } from "@/components/CategoryArt";
import { EmptyState } from "@/components/EmptyState";
import { Monogram } from "@/components/Monogram";
import { SafeImage, SafeImg } from "@/components/SafeImage";
import { ShareButton } from "@/components/ShareButton";
import { getStore, getStoreReviews, listProducts } from "@/lib/api/catalog";
import { ApiError, errorMessage } from "@/lib/api/client";
import type { Product, PublicStore, StoreReview } from "@/lib/api/types";
import { deliveryText, formatINR } from "@/lib/format";
import { PHOTOS, unsplash } from "@/lib/photos";

import { StoreOwnerLink } from "./StoreOwnerLink";
import { StoreTabs } from "./StoreTabs";

export default async function StorePage({ params }: PageProps<"/store/[slug]">) {
  const { slug } = await params;
  let store: PublicStore, products: Product[], reviews: StoreReview[];
  try {
    [store, products, reviews] = await Promise.all([getStore(slug), listProducts({ seller: slug }), getStoreReviews(slug)]);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound(); // unknown or paused shop
    return (
      <EmptyState
        title="This shop didn't load"
        text={errorMessage(error)}
        action={
          <Link href={`/store/${slug}`} className="btn btn-black">
            Try again
          </Link>
        }
      />
    );
  }

  // Cover: the seller's own upload, or their main category's photo until they add one.
  const fallbackPhoto = store.main_category?.photo_id ?? PHOTOS.crafts;
  const rating = store.rating === null ? "No reviews yet" : `${store.rating} ★ (${store.review_count})`;

  return (
    <>
      <div className="mb-4 text-sm text-muted">
        <Link href="/" className="text-muted">
          Home
        </Link>{" "}
        /{" "}
        <Link href="/makers" className="text-muted">
          Makers
        </Link>{" "}
        / {store.name}
      </div>

      <div
        className="relative h-[180px] overflow-hidden rounded-[28px] sm:h-[260px]"
        style={{ background: tintVar(store.main_category?.tint ?? "soft") }}
      >
        {/* If a photo fails to load, the tint behind it shows: never a broken-image icon.
            The cover is a wide, short strip, so "center 35%" keeps more of the subject than plain center. */}
        {store.cover ? (
          <SafeImg
            src={store.cover}
            alt=""
            className="size-full object-cover object-[center_35%]"
            fallback={<SafeImage src={unsplash(fallbackPhoto, 1600)} alt="" fill sizes="100vw" className="object-cover object-[center_35%]" />}
          />
        ) : (
          <SafeImage src={unsplash(fallbackPhoto, 1600)} alt="" fill priority sizes="100vw" className="object-cover object-[center_35%]" />
        )}
      </div>

      {!store.taking_orders && (
        <p className="mt-5 rounded-[14px] bg-soft px-4 py-3 text-[15px]" role="status">
          <b>Not taking orders right now.</b> <span className="text-muted">This maker is on a break. Please check back soon.</span>
        </p>
      )}

      <div className="flex flex-wrap items-center gap-x-[26px] gap-y-[18px] pt-7">
        <Monogram name={store.name} slug={store.slug} size={84} />
        <div className="min-w-0 flex-[1_1_320px]">
          <span className="inline-flex items-center gap-1.5 text-[14.5px] text-muted">
            <MapPin size={16} aria-hidden="true" />
            {[store.kind_label, store.area || "Area not provided by seller"].join(" · ")}
          </span>
          <h1 className="title mt-1">{store.name}</h1>
          {store.bio && <p className="mt-2 max-w-[620px] text-muted">{store.bio}</p>}
          <dl className="mt-2.5 flex flex-wrap gap-x-[30px] gap-y-2">
            {[
              ["Delivery", `${deliveryText(store.delivery_days)} · ${formatINR(store.delivery_fee_paise)}`],
              ["Products", String(store.product_count)],
              ["Reviews", rating],
            ].map(([label, value]) => (
              <div key={label} className="flex flex-col">
                <dt className="text-[13px] text-muted">{label}</dt>
                <dd className="font-semibold">{value}</dd>
              </div>
            ))}
          </dl>
        </div>
        <div className="flex flex-wrap gap-2.5">
          <StoreOwnerLink slug={store.slug} />
          <ShareButton title={store.name} />
        </div>
      </div>

      <StoreTabs products={products} reviews={reviews} storeSlug={store.slug} />
    </>
  );
}
