"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { listCategories } from "@/lib/api/catalog";
import { LoadError } from "@/components/LoadError";
import { ApiError, errorMessage } from "@/lib/api/client";
import { openStore } from "@/lib/api/seller";
import type { Category } from "@/lib/api/types";
import { rupeesToPaise } from "@/lib/format";
import { useSession } from "@/lib/session";

// Must match Seller.Kind in backend/catalog/models.py
const KINDS = [
  ["home_baker", "Home baker"],
  ["home_cook", "Home cook"],
  ["artist", "Artist"],
  ["tailor", "Tailor"],
  ["crafter", "Crafter"],
  ["jewellery_maker", "Jewellery maker"],
  ["other", "Other"],
];

// Stage 1: a plain "Open your shop" form. Stage 3 adds the slug editor, cover photo and more.
export default function SellPage() {
  const { user, signedOut, refresh } = useSession();
  const router = useRouter();
  const [categories, setCategories] = useState<Category[]>([]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0); // bump to load again

  useEffect(() => {
    if (signedOut) router.replace("/signin?next=/sell");
    if (user?.store_slug) router.replace("/seller");
  }, [user, signedOut, router]);

  useEffect(() => {
    listCategories()
      .then((cats) => {
        setLoadError(null);
        setCategories(cats);
      })
      .catch(setLoadError);
  }, [attempt]);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const f = new FormData(event.currentTarget);
    const value = (k: string) => String(f.get(k) ?? "").trim();
    const fee = rupeesToPaise(value("fee") || "0");
    const days = Number(value("days"));
    const found: Record<string, string> = {};
    if (!value("name")) found.name = "Please enter a shop name.";
    if (fee === null) found.fee = "Enter an amount in rupees, like 40.";
    if (!Number.isInteger(days) || days < 0 || days > 30) found.days = "Enter a number of days from 0 to 30.";
    setErrors(found);
    if (Object.keys(found).length) return;

    setBusy(true);
    try {
      await openStore({
        name: value("name"),
        kind: value("kind"),
        main_category: value("category") || null,
        area: value("area"),
        bio: value("bio"),
        delivery_days: days,
        delivery_fee_paise: fee!,
      });
      await refresh();
      toast("Your shop is open");
      router.push("/seller");
    } catch (error) {
      // Show the server's form errors next to their fields, and a toast saying what happened.
      if (error instanceof ApiError) {
        setErrors({
          name: error.fieldError("name") ?? "",
          fee: error.fieldError("delivery_fee_paise") ?? "",
          days: error.fieldError("delivery_days") ?? "",
        });
      }
      toast(`Couldn't open your shop. ${errorMessage(error)}`);
    } finally {
      setBusy(false);
    }
  }

  if (loadError) return <LoadError error={loadError} onRetry={() => { setLoadError(null); setAttempt((n) => n + 1); }} />;

  return (
    <div className="mx-auto max-w-[720px]">
      <h1 className="title">Open your shop</h1>
      <p className="mb-6 mt-1.5 text-muted">Tell buyers who you are and how you deliver. You can change this later.</p>
      <form onSubmit={submit} noValidate className="panel grid gap-3.5 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label className="field-label" htmlFor="name">
            Shop name
          </label>
          <input id="name" name="name" className="input" placeholder="e.g. Your Name's Kitchen" />
          {errors.name && <p className="field-error">{errors.name}</p>}
        </div>
        <div>
          <label className="field-label" htmlFor="kind">
            What do you make?
          </label>
          <select id="kind" name="kind" className="input">
            {KINDS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="field-label" htmlFor="category">
            Main category
          </label>
          <select id="category" name="category" className="input">
            {categories.map((c) => (
              <option key={c.slug} value={c.slug}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
        <div className="sm:col-span-2">
          <label className="field-label" htmlFor="area">
            Area
          </label>
          <input id="area" name="area" className="input" placeholder="e.g. Indiranagar, Bengaluru" />
        </div>
        <div>
          <label className="field-label" htmlFor="fee">
            Delivery fee (₹)
          </label>
          <input id="fee" name="fee" className="input" inputMode="decimal" defaultValue="40" />
          {errors.fee && <p className="field-error">{errors.fee}</p>}
        </div>
        <div>
          <label className="field-label" htmlFor="days">
            Delivers in (days)
          </label>
          <input id="days" name="days" className="input" inputMode="numeric" defaultValue="2" />
          {errors.days && <p className="field-error">{errors.days}</p>}
        </div>
        <div className="sm:col-span-2">
          <label className="field-label" htmlFor="bio">
            About your shop (optional)
          </label>
          <textarea id="bio" name="bio" className="textarea" rows={3} />
        </div>
        <button className="btn btn-black btn-lg sm:col-span-2" disabled={busy}>
          {busy ? "Opening…" : "Open my shop"}
        </button>
      </form>
    </div>
  );
}
