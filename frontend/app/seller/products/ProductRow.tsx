"use client";

import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { CategoryArt, tintVar } from "@/components/CategoryArt";
import { SafeImg } from "@/components/SafeImage";
import { errorMessage } from "@/lib/api/client";
import { deleteProduct, updateProduct } from "@/lib/api/seller";
import type { Category, SellerProduct } from "@/lib/api/types";
import { formatINR } from "@/lib/format";
import { deleteText, productStatus } from "@/lib/product-controls";

type Panel = "stock" | "delete" | null;

/**
 * One product on the Products tab: photo, name, "₹price · stock · sold", status pill and its buttons.
 * Back in stock and Delete open a small panel right under the row (one at a time).
 */
export function ProductRow({
  product: p,
  category,
  onChange,
  onRemoved,
}: {
  product: SellerProduct;
  category?: Category;
  onChange: (p: SellerProduct) => void;
  onRemoved: (id: number) => void;
}) {
  const [panel, setPanel] = useState<Panel>(null);
  const [busy, setBusy] = useState(false);
  const [qty, setQty] = useState("");
  const [qtyError, setQtyError] = useState("");
  const status = productStatus(p);
  const panelId = `product-${p.id}-panel`;

  async function save(fields: Parameters<typeof updateProduct>[1], message: string) {
    setBusy(true);
    try {
      onChange(await updateProduct(p.id, fields));
      toast(message);
      setPanel(null);
    } catch (error) {
      toast(`Couldn't change it. ${errorMessage(error)}`);
    } finally {
      setBusy(false);
    }
  }

  function putBackOnSale(event: React.FormEvent) {
    event.preventDefault();
    if (!/^\d+$/.test(qty.trim()) || Number(qty) < 1) {
      setQtyError("Enter how many you can make: 1 or more.");
      return;
    }
    save({ stock: Number(qty) }, `${p.name} is back on sale`);
  }

  async function remove() {
    setBusy(true);
    try {
      const result = await deleteProduct(p.id);
      onRemoved(p.id);
      toast(result.result === "archived" ? "Removed from your shop (kept in past orders)" : "Product deleted");
    } catch (error) {
      toast(`Couldn't delete it. ${errorMessage(error)}`);
      setBusy(false);
    }
  }

  const open = (which: Panel) => {
    setPanel(panel === which ? null : which);
    setQty("");
    setQtyError("");
  };
  const small = "btn h-10 px-4 text-[15px]";

  return (
    <div className="border-b border-line py-3.5 last:border-0">
      <div className="flex flex-wrap items-center gap-3.5">
        <div
          className="flex size-[64px] flex-none items-center justify-center overflow-hidden rounded-2xl"
          style={{ background: tintVar(category?.tint ?? "soft") }}
        >
          {p.image ? (
            <SafeImg
              src={p.image}
              alt=""
              className="size-full object-cover"
              fallback={<CategoryArt art={category?.art ?? "gift"} className="w-[60%]" />}
            />
          ) : (
            <CategoryArt art={category?.art ?? "gift"} className="w-[60%]" />
          )}
        </div>
        <div className="min-w-0 flex-[1_1_180px]">
          <b className="block truncate">{p.name}</b>
          <div className="text-sm text-muted">
            {formatINR(p.price_paise)} · {p.stock} in stock · {p.sold} sold
          </div>
        </div>
        <span className={`status ${status.className}`}>{status.label}</span>
        <div className="flex w-full flex-wrap gap-2 sm:w-auto">
          {p.stock > 0 ? (
            <button className={`${small} btn-white`} disabled={busy} onClick={() => save({ stock: 0 }, `${p.name} marked out of stock`)}>
              Mark out of stock
            </button>
          ) : (
            <button
              className={`${small} btn-black`}
              disabled={busy}
              aria-expanded={panel === "stock"}
              aria-controls={panelId}
              onClick={() => open("stock")}
            >
              Back in stock
            </button>
          )}
          <button
            className={`${small} btn-white`}
            disabled={busy}
            onClick={() => save({ is_active: !p.is_active }, p.is_active ? "Hidden from buyers" : "Shown to buyers again")}
            aria-label={`${p.is_active ? "Hide" : "Show"} ${p.name}`}
          >
            {p.is_active ? "Hide" : "Show"}
          </button>
          <Link href={`/seller/products/${p.id}`} className={`${small} btn-white`} aria-label={`Edit ${p.name}`}>
            Edit
          </Link>
          <button
            className={`${small} border border-error bg-white text-error hover:bg-error hover:text-white`}
            disabled={busy}
            aria-expanded={panel === "delete"}
            aria-controls={panelId}
            onClick={() => open("delete")}
            aria-label={`Delete ${p.name}`}
          >
            Delete
          </button>
        </div>
      </div>

      {panel === "stock" && (
        <form id={panelId} onSubmit={putBackOnSale} noValidate className="mt-3 flex flex-wrap items-end gap-2.5 rounded-[18px] bg-soft p-4">
          <div className="min-w-0 flex-[1_1_200px]">
            <label className="field-label" htmlFor={`${panelId}-qty`}>
              How many can you make?
            </label>
            <input
              id={`${panelId}-qty`}
              className="input"
              type="number"
              min={1}
              inputMode="numeric"
              value={qty}
              autoFocus
              aria-invalid={qtyError ? true : undefined}
              aria-describedby={qtyError ? `${panelId}-err` : undefined}
              onChange={(e) => {
                setQty(e.target.value);
                setQtyError("");
              }}
            />
            {qtyError && (
              <p id={`${panelId}-err`} className="field-error">
                {qtyError}
              </p>
            )}
          </div>
          <button className="btn btn-black" disabled={busy}>
            {busy ? "Saving…" : "Put back on sale"}
          </button>
          <button type="button" className="btn btn-white" onClick={() => setPanel(null)}>
            Cancel
          </button>
        </form>
      )}

      {panel === "delete" && (
        <div
          id={panelId}
          role="alertdialog"
          aria-labelledby={`${panelId}-title`}
          aria-describedby={`${panelId}-text`}
          className="mt-3 rounded-[18px] border border-error/40 bg-white p-4"
        >
          <b id={`${panelId}-title`} className="block">
            Delete “{p.name}”?
          </b>
          <p id={`${panelId}-text`} className="mt-1 text-[15px] text-muted">
            {deleteText(p.past_orders)}
          </p>
          <div className="mt-3 flex flex-wrap gap-2.5">
            <button className="btn border border-error bg-error text-white hover:opacity-90" disabled={busy} onClick={remove} autoFocus>
              {busy ? "Deleting…" : "Delete product"}
            </button>
            <button type="button" className="btn btn-white" onClick={() => setPanel(null)}>
              Keep it
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
