"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

import { listCategories } from "@/lib/api/catalog";
import { ApiError, errorMessage } from "@/lib/api/client";
import { openStore, removeCover, updateStore, uploadCover, type StoreFields } from "@/lib/api/seller";
import type { Category, Store } from "@/lib/api/types";
import { formatINR, rupeesToPaise } from "@/lib/format";

import { LoadError } from "./LoadError";
import { PhotoPicker, type PickedPhoto } from "./PhotoPicker";

// Must match Seller.Kind in backend/catalog/models.py
export const KINDS = [
  ["home_baker", "Home baker"],
  ["home_cook", "Home cook"],
  ["artist", "Artist"],
  ["tailor", "Tailor"],
  ["crafter", "Crafter"],
  ["jewellery_maker", "Jewellery maker"],
  ["other", "Other"],
];

/** "Asha's Kitchen!" -> "ashas-kitchen". The server checks it again and makes sure it's unique. */
export function toSlug(text: string): string {
  return text
    .toLowerCase()
    .replace(/['’]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 50);
}

/** Open your shop (no store yet) or Store settings (editing an existing store). */
export function StoreForm({ store, onSaved }: { store?: Store; onSaved: (store: Store) => void }) {
  const editing = Boolean(store);
  const [categories, setCategories] = useState<Category[] | null>(null);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const [name, setName] = useState(store?.name ?? "");
  const [slug, setSlug] = useState(store?.slug ?? "");
  const [slugTouched, setSlugTouched] = useState(editing); // once edited by hand, stop following the name
  const [cover, setCover] = useState<PickedPhoto[]>(store?.cover ? [{ key: "cover", url: store.cover }] : []);
  const [paused, setPaused] = useState(store ? !store.is_active : false);
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

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const f = new FormData(event.currentTarget);
    const value = (k: string) => String(f.get(k) ?? "").trim();
    const fee = rupeesToPaise(value("fee") || "0");
    const days = Number(value("days"));
    const found: Record<string, string> = {};
    if (!name.trim()) found.name = "Please enter a shop name.";
    if (slug && !/^[a-z0-9]+(-[a-z0-9]+)*$/.test(slug)) found.slug = "Use small letters, numbers and dashes, like asha-bakes.";
    if (fee === null) found.fee = "Enter an amount in rupees, like 40.";
    if (!Number.isInteger(days) || days < 0 || days > 30) found.days = "Enter a number of days from 0 to 30.";
    setErrors(found);
    if (Object.keys(found).length) return;

    const fields: StoreFields = {
      name: name.trim(),
      slug: slug || undefined,
      kind: value("kind"),
      main_category: value("category") || null,
      area: value("area"),
      bio: value("bio"),
      delivery_days: days,
      delivery_fee_paise: fee!,
      ...(editing ? { is_active: !paused } : {}),
    };

    setBusy(true);
    try {
      let saved = editing ? await updateStore(fields) : await openStore(fields);
      // The cover is uploaded after the shop is saved (it needs the shop to exist).
      const picked = cover[0];
      if (picked?.blob) saved = await uploadCover(picked.blob);
      else if (!picked && store?.cover) saved = await removeCover();
      toast(editing ? "Shop settings saved" : "Your shop is open");
      onSaved(saved);
    } catch (error) {
      if (error instanceof ApiError) {
        setErrors({
          name: error.fieldError("name") ?? "",
          slug: error.fieldError("slug") ?? "",
          fee: error.fieldError("delivery_fee_paise") ?? "",
          days: error.fieldError("delivery_days") ?? "",
        });
      }
      toast(`Couldn't save your shop. ${errorMessage(error)}`);
    } finally {
      setBusy(false);
    }
  }

  const err = (key: string) => errors[key] && <p className="field-error">{errors[key]}</p>;

  return (
    <form onSubmit={submit} noValidate className="panel grid gap-3.5 sm:grid-cols-2">
      <div className="sm:col-span-2">
        <label className="field-label" htmlFor="name">
          Shop name
        </label>
        <input
          id="name"
          className="input"
          placeholder="e.g. Your Name's Kitchen"
          maxLength={80}
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            if (!slugTouched) setSlug(toSlug(e.target.value));
          }}
        />
        {err("name")}
      </div>
      <div className="sm:col-span-2">
        <label className="field-label" htmlFor="slug">
          Shop link
        </label>
        <div className="flex items-center gap-2">
          <span className="text-muted">homehaat/store/</span>
          <input
            id="slug"
            className="input"
            maxLength={60}
            value={slug}
            aria-describedby="slug-help"
            onChange={(e) => {
              setSlugTouched(true);
              setSlug(e.target.value.toLowerCase().replace(/\s+/g, "-"));
            }}
          />
        </div>
        <p id="slug-help" className="mt-1 text-[13px] text-muted">
          Made from your shop name. You can change it; small letters, numbers and dashes only.
        </p>
        {err("slug")}
      </div>
      <div>
        <label className="field-label" htmlFor="kind">
          What do you make?
        </label>
        <select id="kind" name="kind" className="input" defaultValue={store?.kind ?? "home_baker"}>
          {KINDS.map(([v, l]) => (
            <option key={v} value={v}>
              {l}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="field-label" htmlFor="category">
          Main category
        </label>
        <select id="category" name="category" className="input" defaultValue={store?.main_category ?? categories[0]?.slug}>
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
        <input id="area" name="area" className="input" placeholder="e.g. Indiranagar, Bengaluru" maxLength={120} defaultValue={store?.area} />
      </div>
      <div>
        <label className="field-label" htmlFor="fee">
          Delivery fee (₹)
        </label>
        <input
          id="fee"
          name="fee"
          className="input"
          inputMode="decimal"
          defaultValue={store ? formatINR(store.delivery_fee_paise).replace("₹", "") : "40"}
        />
        {err("fee")}
      </div>
      <div>
        <label className="field-label" htmlFor="days">
          Delivers in (days)
        </label>
        <input id="days" name="days" className="input" inputMode="numeric" defaultValue={store?.delivery_days ?? 2} />
        {err("days")}
      </div>
      <div className="sm:col-span-2">
        <label className="field-label" htmlFor="bio">
          About your shop (optional)
        </label>
        <textarea id="bio" name="bio" className="textarea" rows={3} defaultValue={store?.bio} />
      </div>
      <div className="sm:col-span-2">
        <PhotoPicker photos={cover} onChange={setCover} max={1} label="Cover photo (optional)" />
      </div>
      {editing && (
        <label className="flex items-start gap-3 rounded-[14px] bg-soft p-3.5 sm:col-span-2">
          <input type="checkbox" checked={paused} onChange={(e) => setPaused(e.target.checked)} className="mt-1 size-4" />
          <span>
            <b>Pause my shop</b>
            <span className="block text-sm text-muted">
              Buyers won&apos;t see your products and can&apos;t order until you unpause. Orders already placed stay.
            </span>
          </span>
        </label>
      )}
      <button className="btn btn-black btn-lg sm:col-span-2" disabled={busy}>
        {busy ? "Saving…" : editing ? "Save changes" : "Open my shop"}
      </button>
    </form>
  );
}
