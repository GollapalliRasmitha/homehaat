"use client";

import { useState } from "react";
import { toast } from "sonner";

import { PhotoPicker, type PickedPhoto } from "@/components/PhotoPicker";
import { ApiError, errorMessage } from "@/lib/api/client";
import { createRequest, getMyRequest, uploadRequestPhoto } from "@/lib/api/requests";
import type { CustomRequest, PublicStore } from "@/lib/api/types";
import { rupeesToPaise, todayISO } from "@/lib/format";

/** "Describe what you need": maker, description, up to 3 photos, needed-by date, optional budget. */
export function RequestForm({
  makers,
  initialMaker,
  onSent,
}: {
  makers: PublicStore[];
  initialMaker: string;
  onSent: (r: CustomRequest) => void;
}) {
  const [maker, setMaker] = useState(makers.some((m) => m.slug === initialMaker) ? initialMaker : (makers[0]?.slug ?? ""));
  const [photos, setPhotos] = useState<PickedPhoto[]>([]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const f = new FormData(form);
    const value = (k: string) => String(f.get(k) ?? "").trim();
    const budgetText = value("budget");
    const budget = budgetText ? rupeesToPaise(budgetText) : null;
    const found: Record<string, string> = {};
    if (value("description").length < 20) found.description = "Please describe what you need in a sentence or two, so the maker can price it.";
    if (budgetText && budget === null) found.budget = "Enter an amount in rupees, like 1500.";
    if (value("needed_by") && value("needed_by") < todayISO()) found.needed_by = "Choose today or a later date.";
    setErrors(found);
    if (Object.keys(found).length) return;

    setBusy(true);
    try {
      const sent = await createRequest({
        seller: maker,
        description: value("description"),
        needed_by: value("needed_by") || null,
        budget_paise: budget,
      });
      let photoProblem = false;
      for (const photo of photos) {
        try {
          await uploadRequestPhoto(sent.id, photo.blob!);
        } catch {
          photoProblem = true;
        }
      }
      toast(photoProblem ? "Request sent, but some photos didn't upload." : "Request sent to the maker");
      form.reset();
      photos.forEach((p) => p.blob && URL.revokeObjectURL(p.url));
      setPhotos([]);
      // Show the request as it is now, with its photos (the first reply came before they were uploaded).
      onSent(photos.length ? await getMyRequest(sent.id).catch(() => sent) : sent);
    } catch (error) {
      if (error instanceof ApiError) {
        setErrors({
          description: error.fieldError("description") ?? "",
          needed_by: error.fieldError("needed_by") ?? "",
          budget: error.fieldError("budget_paise") ?? "",
          seller: error.fieldError("seller") ?? "",
        });
      }
      toast(`Couldn't send the request. ${errorMessage(error)}`);
    } finally {
      setBusy(false);
    }
  }

  const err = (key: string) => errors[key] && <p className="field-error">{errors[key]}</p>;
  return (
    <form onSubmit={submit} noValidate className="panel flex flex-col gap-4">
      <h2 className="text-[22px]">Ask a maker</h2>
      <div>
        <label className="field-label" htmlFor="maker">
          Maker
        </label>
        <select id="maker" className="input" value={maker} onChange={(e) => setMaker(e.target.value)}>
          {makers.map((m) => (
            <option key={m.slug} value={m.slug}>
              {m.name} · {m.kind_label}
            </option>
          ))}
        </select>
        {err("seller")}
      </div>
      <div>
        <label className="field-label" htmlFor="description">
          What do you need?
        </label>
        <textarea
          id="description"
          name="description"
          className="textarea"
          rows={5}
          maxLength={2000}
          placeholder="e.g. A 1 kg chocolate cake with a photo of our dog on top, eggless, for Saturday evening."
        />
        {err("description")}
      </div>
      <PhotoPicker photos={photos} onChange={setPhotos} max={3} label="Reference photos (optional)" />
      <div className="grid gap-3.5 sm:grid-cols-2">
        <div>
          <label className="field-label" htmlFor="needed_by">
            Needed by (optional)
          </label>
          <input id="needed_by" name="needed_by" type="date" min={todayISO()} className="input" />
          {err("needed_by")}
        </div>
        <div>
          <label className="field-label" htmlFor="budget">
            Budget in ₹ (optional)
          </label>
          <input id="budget" name="budget" inputMode="decimal" className="input" placeholder="e.g. 1500" />
          {err("budget")}
        </div>
      </div>
      <p className="text-[13px] text-muted">
        The maker replies with a price. Nothing is charged until you accept it and pay at checkout.
      </p>
      <button className="btn btn-black btn-lg" disabled={busy || !maker}>
        {busy ? "Sending…" : "Send request"}
      </button>
    </form>
  );
}
