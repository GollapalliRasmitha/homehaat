/**
 * Money is always integer paise (₹450 = 45000). These are the ONLY places
 * that turn paise into text or text into paise. No floating-point maths.
 */

const grouping = new Intl.NumberFormat("en-IN"); // Indian grouping: 1,00,000

/** 45000 -> "₹450", 4550 -> "₹45.50", 10000000 -> "₹1,00,000" */
export function formatINR(paise: number): string {
  if (!Number.isInteger(paise)) throw new Error(`formatINR expects integer paise, got ${paise}`);
  const sign = paise < 0 ? "-" : "";
  const abs = Math.abs(paise);
  const rupees = Math.floor(abs / 100); // whole rupees (integer division)
  const rest = abs % 100; // leftover paise, 0–99
  const decimals = rest ? "." + String(rest).padStart(2, "0") : "";
  return `${sign}₹${grouping.format(rupees)}${decimals}`;
}

/**
 * "2026-10-18" -> "Sun, 18 Oct". Read as a local calendar date (not UTC midnight),
 * so it can't shift by a day in a different time zone.
 */
export function formatDay(isoDate: string): string {
  const [y, m, d] = isoDate.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });
}

/** Today as "YYYY-MM-DD" in the buyer's own time zone (for <input type="date" min=…>). */
export function todayISO(now = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

/** 0 -> "Delivers today", 1 -> "Delivers tomorrow", 3 -> "Delivers in 3 days" */
export function deliveryText(days: number): string {
  if (days === 0) return "Delivers today";
  if (days === 1) return "Delivers tomorrow";
  return `Delivers in ${days} days`;
}

/**
 * What a seller types ("450", "450.5", "1,200.75") -> integer paise.
 * Returns null for anything that isn't a valid amount. Works on the text,
 * so 0.1 + 0.2 style float errors can't happen.
 */
export function rupeesToPaise(text: string): number | null {
  const cleaned = text.replace(/[₹,\s]/g, "");
  const match = /^(\d{1,7})(?:\.(\d{1,2}))?$/.exec(cleaned);
  if (!match) return null;
  const [, rupees, decimals = ""] = match;
  return Number(rupees) * 100 + Number(decimals.padEnd(2, "0"));
}
