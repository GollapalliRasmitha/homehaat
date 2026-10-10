import type { CheckoutSession, RazorpaySuccess } from "./api/types";

// Razorpay Checkout.js is loaded from Razorpay's own site only on the checkout page.
const SCRIPT_URL = "https://checkout.razorpay.com/v1/checkout.js";

interface RazorpayInstance {
  open(): void;
  on(event: "payment.failed", handler: () => void): void;
}
declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => RazorpayInstance;
  }
}

function loadScript(): Promise<void> {
  if (window.Razorpay) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = SCRIPT_URL;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Couldn't load Razorpay. Check your internet connection."));
    document.body.appendChild(script);
  });
}

export type PaymentOutcome = { kind: "success"; response: RazorpaySuccess } | { kind: "failed" } | { kind: "closed" };

/** Opens the Razorpay window and resolves when the buyer pays, fails or closes it. */
export async function payWithRazorpay(session: CheckoutSession): Promise<PaymentOutcome> {
  await loadScript();
  return new Promise((resolve) => {
    let failed = false;
    const rzp = new window.Razorpay!({
      key: session.key_id,
      order_id: session.razorpay_order_id, // the amount is fixed on Razorpay's side by this order
      amount: session.amount,
      currency: session.currency,
      name: "HomeHaat",
      description: `Order #${session.order_id}`,
      prefill: session.prefill,
      theme: { color: "#111111" },
      handler: (response: RazorpaySuccess) => resolve({ kind: "success", response }),
      modal: { ondismiss: () => resolve(failed ? { kind: "failed" } : { kind: "closed" }) },
    });
    // Razorpay lets the buyer retry inside the window, so we only report failure if they then close it.
    rzp.on("payment.failed", () => {
      failed = true;
    });
    rzp.open();
  });
}

/** Saved for the "Confirming payment…" page, which forwards it to /api/payments/verify/. */
export function rememberPayment(orderId: number, response: RazorpaySuccess) {
  try {
    sessionStorage.setItem(`hh-payment-${orderId}`, JSON.stringify(response));
  } catch {
    // Storage blocked: the webhook still confirms the payment.
  }
}

export function takeRememberedPayment(orderId: number | string): RazorpaySuccess | null {
  try {
    const key = `hh-payment-${orderId}`;
    const value = sessionStorage.getItem(key);
    sessionStorage.removeItem(key);
    return value ? (JSON.parse(value) as RazorpaySuccess) : null;
  } catch {
    return null;
  }
}
