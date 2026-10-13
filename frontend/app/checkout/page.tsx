"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { problemText } from "@/components/BagLine";
import { EmptyState } from "@/components/EmptyState";
import { ItemThumb } from "@/components/ItemThumb";
import { LoadError } from "@/components/LoadError";
import { AddressForm } from "@/components/AddressForm";
import { listAddresses } from "@/lib/api/auth";
import { ApiError, errorMessage } from "@/lib/api/client";
import { startCheckout } from "@/lib/api/orders";
import type { Address, SoldOutItem } from "@/lib/api/types";
import { useBag } from "@/lib/bag";
import { deliveryText, formatINR } from "@/lib/format";
import { payWithRazorpay, RazorpayLoadError, rememberPayment } from "@/lib/razorpay";
import { useSession } from "@/lib/session";

type Step = "address" | "review";

/** For "Please update this address (mobile number, pincode)". The exact messages show in the form. */
const FIELD_NAMES = {
  name: "name",
  phone: "mobile number",
  line1: "address",
  line2: "address line 2",
  city: "city",
  pincode: "pincode",
};

export default function CheckoutPage() {
  const { user, signedOut } = useSession();
  const router = useRouter();
  const { cart, failed: bagFailed, removeProducts, reload } = useBag();
  const [addresses, setAddresses] = useState<Address[] | null>(null);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0); // bump to load again
  const [addressId, setAddressId] = useState<number | null>(null);
  const [step, setStep] = useState<Step>("address");
  const [paying, setPaying] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [soldOut, setSoldOut] = useState<SoldOutItem[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null); // an old address being updated

  useEffect(() => {
    if (signedOut) router.replace("/signin?next=/checkout");
    if (!user) return;
    listAddresses()
      .then((a) => {
        setLoadError(null);
        setAddresses(a);
        setAddressId(a[0]?.id ?? null);
      })
      .catch(setLoadError);
  }, [user, signedOut, router, attempt]);

  function retry() {
    setLoadError(null);
    setAttempt((n) => n + 1);
    reload();
  }

  if (loadError || bagFailed) return <LoadError error={loadError} onRetry={retry} title="Couldn't load checkout" />;
  if (!cart || !addresses) return <p className="text-muted">Loading checkout…</p>;
  if (cart.groups.length === 0) {
    return (
      <EmptyState
        asPageTitle
        title="Your bag is empty"
        text="Add something to your bag before checking out."
        action={
          <Link href="/" className="btn btn-black">
            Start exploring
          </Link>
        }
      />
    );
  }

  const address = addresses.find((a) => a.id === addressId);
  const needsUpdate = (a: Address) => Object.keys(a.problems).length > 0;
  const replaceAddress = (saved: Address) => setAddresses(addresses.map((a) => (a.id === saved.id ? saved : a)));
  const makers = cart.groups.length;

  async function pay() {
    if (!addressId) return;
    setPaying(true);
    setFailure(null);
    setSoldOut([]);
    try {
      // 1. The server creates the order, splits it per seller, holds the stock and computes the total.
      const session = await startCheckout(addressId);
      // 2. The buyer pays in Razorpay's own window (it closes itself when the 15-minute hold ends).
      const outcome = await payWithRazorpay(session);
      if (outcome.kind === "success") {
        // 3. Never trust the browser: go to "Confirming payment…" and let the server check it.
        rememberPayment(session.order_id, outcome.response);
        router.push(`/checkout/confirming/${session.order_id}`);
        return;
      }
      if (outcome.kind === "failed") setFailure("Your payment didn't go through. You haven't been charged.");
      else toast("Payment cancelled. You haven't been charged.");
    } catch (error) {
      if (error instanceof ApiError && error.data.address_problems && address) {
        // The server found something wrong with this address: show what to fix, back on the address step.
        replaceAddress({ ...address, problems: error.data.address_problems as Address["problems"] });
        setStep("address");
        setEditingId(address.id);
      } else if (error instanceof ApiError && Array.isArray(error.data.sold_out)) {
        setSoldOut(error.data.sold_out as SoldOutItem[]);
        await reload();
      } else {
        // No money moves before Razorpay confirms, so any error here means nothing was charged.
        const reason = error instanceof RazorpayLoadError ? error.message : errorMessage(error);
        setFailure(`${reason} You haven't been charged.`);
      }
    }
    setPaying(false);
  }

  async function removeSoldOut() {
    await removeProducts(soldOut.map((item) => item.product_id));
    setSoldOut([]);
  }

  return (
    <div className="mx-auto max-w-[820px]">
      <h1 className="title">Checkout</h1>
      <ol className="my-6 flex flex-wrap items-center gap-2.5 text-sm font-semibold" aria-label="Checkout steps">
        {["Address", "Review", "Pay"].map((label, i) => {
          const on = i === 0 || step === "review";
          return (
            <li key={label} className={`flex items-center gap-2 ${on ? "text-ink" : "text-muted"}`}>
              <span
                className={`flex size-7 items-center justify-center rounded-full border ${
                  on ? "border-ink bg-ink text-white" : "border-line bg-white"
                }`}
              >
                {i + 1}
              </span>
              {label}
            </li>
          );
        })}
      </ol>

      {soldOut.length > 0 && (
        <div className="panel mb-4 flex flex-col items-start gap-2" role="alert">
          <p className="font-semibold">Some items sold out while you were shopping.</p>
          <ul className="list-disc pl-5 text-muted">
            {soldOut.map((item) => (
              <li key={item.product_id}>{item.name}</li>
            ))}
          </ul>
          <button className="btn btn-black mt-1" onClick={removeSoldOut}>
            Remove {soldOut.length === 1 ? "it" : "them"} from my bag
          </button>
        </div>
      )}

      {failure && (
        <div className="panel mb-4 flex flex-col items-start gap-3" role="alert">
          <p className="font-semibold">{failure}</p>
          <button className="btn btn-black" onClick={pay} disabled={paying}>
            Try again
          </button>
        </div>
      )}

      {step === "address" ? (
        <div className="panel">
          <h2 className="mb-3.5 text-[22px]">Deliver to</h2>
          {addresses.map((a) =>
            editingId === a.id ? (
              <div key={a.id} className="mb-2.5 rounded-2xl border border-ink p-3.5">
                <AddressForm
                  address={a}
                  onSaved={(saved) => {
                    replaceAddress(saved);
                    setAddressId(saved.id);
                    setEditingId(null);
                  }}
                  onCancel={() => setEditingId(null)}
                />
              </div>
            ) : (
              <div
                key={a.id}
                className={`mb-2.5 rounded-2xl border p-3.5 ${addressId === a.id ? "border-ink" : "border-line"}`}
              >
                <label className="flex cursor-pointer items-start gap-3">
                  <input type="radio" name="address" checked={addressId === a.id} onChange={() => setAddressId(a.id)} className="mt-1.5" />
                  <span className="min-w-0">
                    <b>{a.name}</b> · {a.phone}
                    <br />
                    <span className="text-muted">
                      {a.line1}
                      {a.line2 && `, ${a.line2}`}, {a.city} {a.pincode}
                    </span>
                  </span>
                </label>
                {needsUpdate(a) && (
                  <div className="mt-3 flex flex-col items-start gap-2.5 rounded-[14px] bg-soft px-3.5 py-3" role="status">
                    <p className="text-sm">
                      <b>Please update this address</b>{" "}
                      <span className="text-muted">
                        ({(Object.keys(a.problems) as (keyof typeof FIELD_NAMES)[]).map((k) => FIELD_NAMES[k]).join(", ")}).
                      </span>
                    </p>
                    <button
                      type="button"
                      className="btn btn-black"
                      onClick={() => {
                        setAddressId(a.id);
                        setEditingId(a.id);
                      }}
                    >
                      Update address
                    </button>
                  </div>
                )}
              </div>
            ),
          )}
          {addresses.length === 0 && (
            <AddressForm
              defaultName={user?.name ?? ""}
              onSaved={(saved) => {
                setAddresses([saved, ...addresses]);
                setAddressId(saved.id);
              }}
            />
          )}
          {address && needsUpdate(address) && editingId === null && (
            <p className="field-error">Update the selected address to continue.</p>
          )}
          <button
            className="btn btn-black btn-lg mt-4"
            disabled={!address || needsUpdate(address) || editingId !== null}
            onClick={() => setStep("review")}
          >
            Continue to review
          </button>
        </div>
      ) : (
        <div className="panel">
          <h2 className="text-[22px]">Review your order</h2>
          {address && (
            <p className="mb-3.5 mt-1.5 text-muted">
              Delivering to {address.name}, {address.line1}, {address.city} {address.pincode}
            </p>
          )}
          {cart.groups.map((group) => (
            <div key={group.seller.slug} className="border-t border-line py-3">
              <b>{group.seller.name}</b> <span className="text-muted">· {deliveryText(group.seller.delivery_days)}</span>
              {group.items.map((line) => (
                <div key={line.product.id} className="mt-2.5 flex items-center gap-3 text-[15px] text-muted">
                  <ItemThumb name={line.product.name} image={line.product.image} tint={line.product.category.tint} art={line.product.category.art} size={48} />
                  <span className="min-w-0 flex-1">
                    {line.qty} × {line.product.name}
                    {line.problem && <span className="ml-2 font-semibold text-error">{problemText(line)}</span>}
                  </span>
                  <span>{formatINR(line.line_total)}</span>
                </div>
              ))}
              <div className="mt-1.5 flex justify-between text-[15px] text-muted">
                <span>Delivery</span>
                <span>{formatINR(group.delivery_fee)}</span>
              </div>
            </div>
          ))}
          <div className="flex items-baseline justify-between border-t border-[#ddd] py-3.5">
            <span className="font-bold">Total</span>
            <b className="price text-[30px]">{formatINR(cart.grand_total)}</b>
          </div>
          <p className="mb-4 rounded-[14px] bg-soft px-3.5 py-3 text-sm">
            One payment. HomeHaat splits it into {makers} seller {makers === 1 ? "order" : "orders"}. We hold your
            items for 15 minutes while you pay.
          </p>
          <div className="flex flex-wrap items-center gap-2.5">
            <button className="btn btn-white" onClick={() => setStep("address")} disabled={paying}>
              Back
            </button>
            <button className="btn btn-black btn-lg" onClick={pay} disabled={paying || cart.has_problems}>
              {paying ? "Opening payment…" : `Pay ${formatINR(cart.grand_total)}`}
            </button>
            <span className="testpill">Test mode, no real money</span>
          </div>
        </div>
      )}
    </div>
  );
}
