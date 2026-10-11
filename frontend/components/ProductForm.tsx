"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { listCategories } from "@/lib/api/catalog";
import { ApiError, errorMessage } from "@/lib/api/client";
import {
  addProduct,
  deleteProductPhoto,
  orderProductPhotos,
  updateProduct,
  uploadProductPhoto,
} from "@/lib/api/seller";
import type { Category, SellerProduct } from "@/lib/api/types";
import { formatINR, rupeesToPaise } from "@/lib/format";
import { useSeller } from "@/lib/seller-context";

import { LoadError } from "./LoadError";
import { PhotoPicker, type PickedPhoto } from "./PhotoPicker";

/** Add a product (no `product`) or edit one. Photos are saved after the product itself. */
export function ProductForm({ product }: { product?: SellerProduct }) {
  const router = useRouter();
  const { store } = useSeller();
  const [categories, setCategories] = useState<Category[] | null>(null);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const [photos, setPhotos] = useState<PickedPhoto[]>(
    product?.images.map((img) => ({ key: `saved-${img.id}`, id: img.id, url: img.url })) ?? [],
  );
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    listCategories()
      .then(setCategories)
      .catch(setLoadError);
  }, [attempt]);

  if (loadError) {
    const retry = () => {
      setLoadError(null);
      setAttempt((n) => n + 1);
    };
    return <LoadError error={loadError} onRetry={retry} />;
  }
  if (!categories) return <p className="text-muted">Loading…</p>;

  /** After the product is saved: delete removed photos, upload new ones, then save the order. */
  async function syncPhotos(productId: number) {
    const keptIds = new Set(photos.filter((p) => p.id).map((p) => p.id));
    for (const old of product?.images ?? []) {
      if (!keptIds.has(old.id)) await deleteProductPhoto(productId, old.id);
    }
    const ids: number[] = [];
    for (const photo of photos) {
      ids.push(photo.id ?? (await uploadProductPhoto(productId, photo.blob!)).id);
    }
    if (ids.length) await orderProductPhotos(productId, ids);
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const f = new FormData(event.currentTarget);
    const value = (k: string) => String(f.get(k) ?? "").trim();
    const price = rupeesToPaise(value("price"));
    const stock = value("stock");
    const found: Record<string, string> = {};
    if (!value("name")) found.name = "Please enter a name.";
    if (price === null || price < 100) found.price = "Enter a price of ₹1 or more.";
    if (!/^\d+$/.test(stock)) found.stock = "Enter a number, 0 or more.";
    setErrors(found);
    if (Object.keys(found).length) return;

    const fields = {
      name: value("name"),
      description: value("description"),
      category: value("category"),
      price_paise: price!,
      stock: Number(stock),
    };
    setBusy(true);
    let saved: SellerProduct | null = null;
    try {
      saved = product ? await updateProduct(product.id, fields) : await addProduct(fields);
    } catch (error) {
      if (error instanceof ApiError) {
        setErrors({
          name: error.fieldError("name") ?? "",
          price: error.fieldError("price_paise") ?? "",
          stock: error.fieldError("stock") ?? "",
        });
      }
      toast(`Couldn't save the product. ${errorMessage(error)}`);
      setBusy(false);
      return;
    }
    try {
      await syncPhotos(saved.id);
      toast(product ? "Product updated" : "Product added to your shop");
    } catch (error) {
      // The product itself is saved; only some photos didn't make it. Say so honestly.
      toast(`Product saved, but some photos didn't upload. ${errorMessage(error)}`);
    }
    setBusy(false);
    router.push("/seller/products");
  }

  const err = (key: string) => errors[key] && <p className="field-error">{errors[key]}</p>;
  const rupees = (paise: number) => formatINR(paise).replace("₹", "");

  return (
    <form onSubmit={submit} noValidate className="panel mx-auto flex max-w-[760px] flex-col gap-5">
      <h2 className="text-[26px]">{product ? "Edit product" : "Add a product"}</h2>
      <PhotoPicker photos={photos} onChange={setPhotos} />
      <p className="-mt-2 text-[13px] text-muted">
        No photo yet? Buyers will see a simple drawing of the category until you add one.
      </p>

      <div className="grid gap-3.5 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label className="field-label" htmlFor="name">
            Product name
          </label>
          <input id="name" name="name" className="input" maxLength={120} defaultValue={product?.name} />
          {err("name")}
        </div>
        <div className="sm:col-span-2">
          <label className="field-label" htmlFor="category">
            Category
          </label>
          <select
            id="category"
            name="category"
            className="input"
            defaultValue={product?.category ?? store.main_category ?? categories[0]?.slug}
          >
            {categories.map((c) => (
              <option key={c.slug} value={c.slug}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
        <div className="sm:col-span-2">
          <label className="field-label" htmlFor="description">
            Description
          </label>
          <textarea
            id="description"
            name="description"
            className="textarea"
            rows={4}
            defaultValue={product?.description}
            placeholder="What it is, size or weight, ingredients or materials, how long it keeps."
          />
        </div>
        <div>
          <label className="field-label" htmlFor="price">
            Price (₹)
          </label>
          <input id="price" name="price" className="input" inputMode="decimal" defaultValue={product ? rupees(product.price_paise) : ""} />
          {err("price")}
        </div>
        <div>
          <label className="field-label" htmlFor="stock">
            How many can you make?
          </label>
          <input id="stock" name="stock" className="input" inputMode="numeric" defaultValue={product?.stock} />
          {err("stock")}
        </div>
      </div>

      <div className="flex flex-wrap gap-2.5">
        <button className="btn btn-black btn-lg" disabled={busy}>
          {busy ? "Saving…" : product ? "Save changes" : "Save and show in my shop"}
        </button>
        <Link href="/seller/products" className="btn btn-white btn-lg">
          Cancel
        </Link>
      </div>
    </form>
  );
}
