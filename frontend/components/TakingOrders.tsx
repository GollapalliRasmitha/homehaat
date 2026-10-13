"use client";

import { useState } from "react";
import { toast } from "sonner";

import { errorMessage } from "@/lib/api/client";
import { updateStore } from "@/lib/api/seller";
import { useSeller } from "@/lib/seller-context";

/**
 * Overview: "Taking orders" on/off (the shop's is_active, which used to be "Pause my shop" in settings).
 * Off = paused: buyers can still open the shop and its products, but nothing can be ordered.
 */
export function TakingOrders() {
  const { store, setStore } = useSeller();
  const [busy, setBusy] = useState(false);
  const on = store.is_active;

  async function toggle() {
    setBusy(true);
    try {
      const saved = await updateStore({ is_active: !on });
      setStore(saved); // the "Paused" badge updates at once
      toast(saved.is_active ? "You're taking orders again" : "Paused: buyers can't order until you switch it back on");
    } catch (error) {
      toast(`Couldn't change it. ${errorMessage(error)}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="flex items-start gap-4 rounded-[22px] border border-line p-5" aria-labelledby="taking-orders">
      <div className="min-w-0 flex-1">
        <h2 id="taking-orders" className="text-lg font-semibold">
          Taking orders
        </h2>
        <p id="taking-orders-help" className="mt-0.5 text-[15px] text-muted">
          {on ? "On. " : "Off: buyers can't order right now. "}
          Pause for holidays or busy weeks. Buyers can still see your shop.
        </p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={on}
        aria-labelledby="taking-orders"
        aria-describedby="taking-orders-help"
        onClick={toggle}
        disabled={busy}
        className={`relative mt-0.5 h-[30px] w-[52px] flex-none rounded-full transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink disabled:opacity-60 ${
          on ? "bg-ink" : "bg-line"
        }`}
      >
        <span
          aria-hidden
          className={`absolute top-[3px] size-6 rounded-full bg-white shadow transition-[left] ${on ? "left-[25px]" : "left-[3px]"}`}
        />
      </button>
    </section>
  );
}
