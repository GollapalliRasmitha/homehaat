/**
 * Delivery address rules for India, the same as the server's (backend/accounts/address_rules.py).
 * The form uses them for instant messages next to each field; the server checks again and decides.
 */

export type AddressFields = { name: string; phone: string; line1: string; line2: string; city: string; pincode: string };
export type AddressProblems = Partial<Record<keyof AddressFields, string>>;

export const ADDRESS_MESSAGES: Required<AddressProblems> = {
  name: "Please enter the name of the person receiving the order.",
  phone: "Enter a 10-digit mobile number starting with 6, 7, 8 or 9.",
  line1: "Please write your house number and street in words (at least 3 letters).",
  line2: "Leave this empty, or write it in words.",
  city: "Please enter your city name (at least 3 letters).",
  pincode: "Enter a 6-digit pincode (it doesn't start with 0).",
};

/** Letters in any script ("Bengaluru", "बेंगलुरु"); symbols and digits don't count. */
const letters = (text: string) => (text.match(/\p{L}/gu) ?? []).length;

/** "+91 98765 43210", "098765-43210" -> "9876543210". Anything else comes back unchanged (and is then refused). */
export function normalizePhone(phone: string): string {
  const digits = phone.replace(/[\s\-()]/g, "");
  for (const prefix of ["+91", "91", "0"]) {
    if (digits.startsWith(prefix) && digits.length === prefix.length + 10) return digits.slice(prefix.length);
  }
  return /^\d+$/.test(digits) ? digits : phone.trim();
}

export function addressProblems(a: AddressFields): AddressProblems {
  const p: AddressProblems = {};
  const phone = normalizePhone(a.phone);
  if (letters(a.name.trim()) < 2) p.name = ADDRESS_MESSAGES.name;
  if (!/^[6-9]\d{9}$/.test(phone) || new Set(phone).size === 1) p.phone = ADDRESS_MESSAGES.phone;
  if (letters(a.line1) < 3) p.line1 = ADDRESS_MESSAGES.line1;
  if (a.line2.trim() && !/[\p{L}\p{N}]/u.test(a.line2)) p.line2 = ADDRESS_MESSAGES.line2;
  if (letters(a.city) < 3) p.city = ADDRESS_MESSAGES.city;
  if (!/^[1-9]\d{5}$/.test(a.pincode.trim())) p.pincode = ADDRESS_MESSAGES.pincode;
  return p;
}
