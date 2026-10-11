"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { listCategories } from "@/lib/api/catalog";
import { LoadError } from "@/components/LoadError";
import { ApiError, errorMessage } from "@/lib/api/client";
import { addProduct, getMyStore } from "@/lib/api/seller";
import type { Category } from "@/lib/api/types";
import { rupeesToPaise } from "@/lib/format";

// Stage 1: a plain form without photos. Stage 3 adds photos (up to 5) and editing.
export default function NewProductPage() {
  const router = useRouter();
  const [categories, setCategories] = useState<Category[]>([]);
  const [defaultCategory, setDefaultCategory] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0); // bump to load again

  useEffect(() => {
    Promise.all([listCategories(), getMyStore()])
      .then(([cats, store]) => {
        setCategories(cats);
        setDefaultCategory(store.main_category ?? cats[0]?.slug ?? null);
      })
      .catch((error) => {
        // No shop yet → go and open one. Anything else → explain it and offer Try again.
        if (error instanceof ApiError && error.status === 404) router.replace("/sell");
        else setLoadError(error);
      });
  }, [router, attempt]);

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

    setBusy(true);
    try {
      await addProduct({
        name: value("name"),
        description: value("description"),
        category: value("category"),
        price_paise: price!,
        stock: Number(stock),
      });
      toast("Product added to your shop");
      router.push("/seller");
    } catch (error) {
      if (error instanceof ApiError) {
        setErrors({
          name: error.fieldError("name") ?? "",
          price: error.fieldError("price_paise") ?? "",
          stock: error.fieldError("stock") ?? "",
        });
      }
      toast(`Couldn't save the product. ${errorMessage(error)}`);
    } finally {
      setBusy(false);
    }
  }

  if (loadError) {
    const retry = () => {
      setLoadError(null);
      setAttempt((n) => n + 1);
    };
    return <LoadError error={loadError} onRetry={retry} />;
  }
  if (!defaultCategory) return <p className="text-muted">Loading…</p>;

  return (
    <div className="mx-auto max-w-[760px]">
      <div className="mb-4 text-sm text-muted">
        <Link href="/seller" className="text-muted">
          My shop
        </Link>{" "}
        / Add a product
      </div>
      <h1 className="title">Add a product</h1>
      <form onSubmit={submit} noValidate className="panel mt-5 grid gap-3.5 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label className="field-label" htmlFor="name">
            Product name
          </label>
          <input id="name" name="name" className="input" maxLength={120} />
          {errors.name && <p className="field-error">{errors.name}</p>}
        </div>
        <div className="sm:col-span-2">
          <label className="field-label" htmlFor="category">
            Category
          </label>
          <select id="category" name="category" className="input" defaultValue={defaultCategory}>
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
          <textarea id="description" name="description" className="textarea" rows={3} />
        </div>
        <div>
          <label className="field-label" htmlFor="price">
            Price (₹)
          </label>
          <input id="price" name="price" className="input" inputMode="decimal" />
          {errors.price && <p className="field-error">{errors.price}</p>}
        </div>
        <div>
          <label className="field-label" htmlFor="stock">
            How many can you make?
          </label>
          <input id="stock" name="stock" className="input" inputMode="numeric" />
          {errors.stock && <p className="field-error">{errors.stock}</p>}
        </div>
        <div className="flex flex-wrap gap-2.5 sm:col-span-2">
          <button className="btn btn-black btn-lg" disabled={busy}>
            {busy ? "Saving…" : "Save and show in my shop"}
          </button>
          <Link href="/seller" className="btn btn-white btn-lg">
            Cancel
          </Link>
        </div>
      </form>
    </div>
  );
}
