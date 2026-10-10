"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { EmptyState } from "@/components/EmptyState";
import { addAddress, listAddresses } from "@/lib/api/auth";
import { getCart } from "@/lib/api/cart";
import { ApiError } from "@/lib/api/client";
import { startCheckout } from "@/lib/api/orders";
import type { Address, Cart } from "@/lib/api/types";
import { formatINR } from "@/lib/format";
import { payWithRazorpay, rememberPayment } from "@/lib/razorpay";
import { useSession } from "@/lib/session";

type Step = "address" | "review";

export default function CheckoutPage() {
  const { user, loading } = useSession();
  const router = useRouter();
  const [cart, setCart] = useState<Cart | null>(null);
  const [addresses, setAddresses] = useState<Address[] | null>(null);
  const [addressId, setAddressId] = useState<number | null>(null);
  const [step, setStep] = useState<Step>("address");
  const [paying, setPaying] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [soldOut, setSoldOut] = useState<string[]>([]);

  useEffect(() => {
    if (!loading && !user) router.replace("/signin?next=/checkout");
    if (!user) return;
    Promise.all([getCart(), listAddresses()]).then(([c, a]) => {
      setCart(c);
      setAddresses(a);
      setAddressId(a[0]?.id ?? null);
    });
  }, [user, loading, router]);

  if (!cart || !addresses) return <p className="text-muted">Loading checkout…</p>;
  if (cart.items.length === 0) {
    return (
      <EmptyState
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

  async function pay() {
    if (!addressId) return;
    setPaying(true);
    setFailure(null);
    setSoldOut([]);
    try {
      // 1. The server creates the order and computes the total itself.
      const session = await startCheckout(addressId);
      // 2. The buyer pays in Razorpay's own window.
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
      if (error instanceof ApiError && Array.isArray(error.data.sold_out)) setSoldOut(error.data.sold_out as string[]);
      else setFailure(error instanceof Error ? error.message : "Something went wrong. You haven't been charged.");
    }
    setPaying(false);
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
        <div className="panel mb-4" role="alert">
          <p className="font-semibold">Some items sold out while you were shopping.</p>
          <p className="text-muted">{soldOut.join(", ")}</p>
          <Link href="/cart" className="btn btn-white mt-3">
            Update your bag
          </Link>
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
          {addresses.map((a) => (
            <label
              key={a.id}
              className={`mb-2.5 flex cursor-pointer items-start gap-3 rounded-2xl border p-3.5 ${
                addressId === a.id ? "border-ink" : "border-line"
              }`}
            >
              <input type="radio" name="address" checked={addressId === a.id} onChange={() => setAddressId(a.id)} className="mt-1.5" />
              <span>
                <b>{a.name}</b> · {a.phone}
                <br />
                <span className="text-muted">
                  {a.line1}
                  {a.line2 && `, ${a.line2}`}, {a.city} {a.pincode}
                </span>
              </span>
            </label>
          ))}
          {addresses.length === 0 && (
            <AddressForm
              defaultName={user?.name ?? ""}
              onSaved={(saved) => {
                setAddresses([saved, ...addresses]);
                setAddressId(saved.id);
              }}
            />
          )}
          <button className="btn btn-black btn-lg mt-4" disabled={!addressId} onClick={() => setStep("review")}>
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
          <div className="border-t border-line py-3">
            <b>{cart.items[0].product.seller.name}</b>
            {cart.items.map((item) => (
              <div key={item.id} className="mt-1.5 flex justify-between text-[15px] text-muted">
                <span>
                  {item.qty} × {item.product.name}
                </span>
                <span>{formatINR(item.line_total)}</span>
              </div>
            ))}
            <div className="mt-1.5 flex justify-between text-[15px] text-muted">
              <span>Delivery</span>
              <span>{formatINR(cart.delivery_total)}</span>
            </div>
          </div>
          <div className="flex items-baseline justify-between border-t border-[#ddd] py-3.5">
            <span className="font-bold">Total</span>
            <b className="price text-[30px]">{formatINR(cart.grand_total)}</b>
          </div>
          <div className="flex flex-wrap items-center gap-2.5">
            <button className="btn btn-white" onClick={() => setStep("address")} disabled={paying}>
              Back
            </button>
            <button className="btn btn-black btn-lg" onClick={pay} disabled={paying}>
              {paying ? "Opening payment…" : `Pay ${formatINR(cart.grand_total)}`}
            </button>
            <span className="testpill">Test mode, no real money</span>
          </div>
        </div>
      )}
    </div>
  );
}

function AddressForm({ defaultName, onSaved }: { defaultName: string; onSaved: (a: Address) => void }) {
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const f = new FormData(event.currentTarget);
    const value = (k: string) => String(f.get(k) ?? "").trim();
    const data = {
      label: "",
      name: value("name"),
      phone: value("phone"),
      line1: value("line1"),
      line2: value("line2"),
      city: value("city"),
      pincode: value("pincode"),
    };
    // Quick checks in the browser; the server checks again (it never trusts the browser).
    const found: Record<string, string> = {};
    if (!data.name) found.name = "Please enter a name.";
    if (!/^\d{10}$/.test(data.phone)) found.phone = "Enter a 10-digit phone number.";
    if (!data.line1) found.line1 = "Please enter your address.";
    if (!data.city) found.city = "Please enter your city.";
    if (!/^\d{6}$/.test(data.pincode)) found.pincode = "Enter a 6-digit pincode.";
    setErrors(found);
    if (Object.keys(found).length) return;

    setBusy(true);
    try {
      onSaved(await addAddress(data));
      toast("Address saved");
    } catch (error) {
      if (error instanceof ApiError) {
        setErrors(Object.fromEntries(Object.keys(data).map((k) => [k, error.fieldError(k) ?? ""]).filter(([, v]) => v)));
      }
      toast("Couldn't save the address.");
    } finally {
      setBusy(false);
    }
  }

  const field = (name: string, label: string, props: React.InputHTMLAttributes<HTMLInputElement> = {}, full = false) => (
    <div className={full ? "sm:col-span-2" : ""}>
      <label className="field-label" htmlFor={`a-${name}`}>
        {label}
      </label>
      <input id={`a-${name}`} name={name} className="input" aria-describedby={errors[name] ? `a-${name}-err` : undefined} {...props} />
      {errors[name] && (
        <p id={`a-${name}-err`} className="field-error">
          {errors[name]}
        </p>
      )}
    </div>
  );

  return (
    <form onSubmit={submit} noValidate className="grid gap-3.5 sm:grid-cols-2">
      <p className="text-muted sm:col-span-2">Add the address where you want your order delivered.</p>
      {field("name", "Name", { defaultValue: defaultName, autoComplete: "name" })}
      {field("phone", "Phone", { inputMode: "numeric", maxLength: 10, autoComplete: "tel-national" })}
      {field("line1", "Address", { autoComplete: "address-line1" }, true)}
      {field("line2", "Address line 2 (optional)", { autoComplete: "address-line2" }, true)}
      {field("city", "City", { autoComplete: "address-level2" })}
      {field("pincode", "Pincode", { inputMode: "numeric", maxLength: 6, autoComplete: "postal-code" })}
      <div className="sm:col-span-2">
        <button className="btn btn-white" disabled={busy}>
          {busy ? "Saving…" : "Save address"}
        </button>
      </div>
    </form>
  );
}
