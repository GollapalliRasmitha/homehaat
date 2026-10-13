"use client";

import { useState } from "react";
import { toast } from "sonner";

import { addAddress, updateAddress } from "@/lib/api/auth";
import { ApiError, errorMessage } from "@/lib/api/client";
import type { Address } from "@/lib/api/types";
import { type AddressFields, type AddressProblems, addressProblems, normalizePhone } from "@/lib/address-rules";

const FIELDS: (keyof AddressFields)[] = ["name", "phone", "line1", "line2", "city", "pincode"];

/**
 * Add a delivery address, or update one (`address`) that was saved before the address rules.
 * Each broken rule shows its own message under its field: when leaving the field, and on Save.
 */
export function AddressForm({
  address,
  defaultName = "",
  onSaved,
  onCancel,
}: {
  address?: Address;
  defaultName?: string;
  onSaved: (a: Address) => void;
  onCancel?: () => void;
}) {
  // Start by showing what's wrong with an old address, so the buyer sees exactly what to fix.
  const [errors, setErrors] = useState<AddressProblems>(address?.problems ?? {});
  const [busy, setBusy] = useState(false);

  const read = (form: HTMLFormElement): AddressFields => {
    const f = new FormData(form);
    const value = (k: string) => String(f.get(k) ?? "").trim();
    return Object.fromEntries(FIELDS.map((k) => [k, value(k)])) as AddressFields;
  };

  /** Leaving a field: show (or clear) just that field's message. */
  function checkField(event: React.FocusEvent<HTMLFormElement>) {
    const name = (event.target as Element).getAttribute("name") as keyof AddressFields;
    if (!FIELDS.includes(name)) return;
    const data = read(event.currentTarget);
    if (!data[name] && !errors[name]) return; // don't scold an empty field the buyer hasn't reached yet
    setErrors((e) => ({ ...e, [name]: addressProblems(data)[name] }));
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = read(event.currentTarget);
    // Quick checks in the browser; the server checks the same rules again (it never trusts the browser).
    const found = addressProblems(data);
    setErrors(found);
    if (Object.keys(found).length) return;

    setBusy(true);
    const body = { ...data, phone: normalizePhone(data.phone), label: address?.label ?? "" };
    try {
      onSaved(address ? await updateAddress(address.id, body) : await addAddress(body));
      toast(address ? "Address updated" : "Address saved");
    } catch (error) {
      if (error instanceof ApiError) {
        setErrors(Object.fromEntries(FIELDS.map((k) => [k, error.fieldError(k) ?? ""]).filter(([, v]) => v)));
      }
      toast(`Couldn't save the address. ${errorMessage(error)}`);
    } finally {
      setBusy(false);
    }
  }

  const field = (
    name: keyof AddressFields,
    label: string,
    props: React.InputHTMLAttributes<HTMLInputElement> = {},
    full = false,
  ) => (
    <div className={full ? "sm:col-span-2" : ""}>
      <label className="field-label" htmlFor={`a-${name}`}>
        {label}
      </label>
      <input
        id={`a-${name}`}
        name={name}
        className="input"
        defaultValue={address ? address[name] : name === "name" ? defaultName : ""}
        aria-invalid={errors[name] ? true : undefined}
        aria-describedby={errors[name] ? `a-${name}-err` : undefined}
        {...props}
      />
      {errors[name] && (
        <p id={`a-${name}-err`} className="field-error">
          {errors[name]}
        </p>
      )}
    </div>
  );

  return (
    <form onSubmit={submit} onBlur={checkField} noValidate className="grid gap-3.5 sm:grid-cols-2">
      <p className="text-muted sm:col-span-2">
        {address
          ? "Please update the details marked below, so the maker can deliver to you."
          : "Add the address where you want your order delivered."}
      </p>
      {field("name", "Name", { autoComplete: "name" })}
      {field("phone", "Mobile number", { inputMode: "tel", maxLength: 16, autoComplete: "tel-national", placeholder: "98765 43210" })}
      {field("line1", "Address", { autoComplete: "address-line1", placeholder: "House number, street, area" }, true)}
      {field("line2", "Address line 2 (optional)", { autoComplete: "address-line2", placeholder: "Landmark" }, true)}
      {field("city", "City", { autoComplete: "address-level2" })}
      {field("pincode", "Pincode", { inputMode: "numeric", maxLength: 6, autoComplete: "postal-code" })}
      <div className="flex flex-wrap gap-2.5 sm:col-span-2">
        <button className="btn btn-black" disabled={busy}>
          {busy ? "Saving…" : "Save address"}
        </button>
        {onCancel && (
          <button type="button" className="btn btn-white" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}
