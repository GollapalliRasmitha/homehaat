"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { getOrder, verifyPayment } from "@/lib/api/orders";
import { takeRememberedPayment } from "@/lib/razorpay";
import { useSession } from "@/lib/session";

const POLL_EVERY_MS = 2000;
const GIVE_UP_AFTER_MS = 90_000;

/**
 * "Confirming payment…". The browser never decides that an order is paid.
 * It asks the server to verify (local backup path), then keeps asking the
 * server for the order until the server says "paid".
 */
export default function ConfirmingPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const router = useRouter();
  const { refresh } = useSession();
  const [state, setState] = useState<"waiting" | "failed" | "slow">("waiting");

  useEffect(() => {
    let stopped = false;
    const started = Date.now();

    async function run() {
      const response = takeRememberedPayment(orderId);
      if (response) await verifyPayment(response).catch(() => undefined); // the webhook may still confirm it

      while (!stopped) {
        const order = await getOrder(orderId).catch(() => null);
        if (order?.payment_status === "paid") {
          await refresh(); // bag count goes back to 0
          router.replace(`/orders/${orderId}`);
          return;
        }
        if (order?.payment_status === "failed") return setState("failed");
        if (Date.now() - started > GIVE_UP_AFTER_MS) return setState("slow");
        await new Promise((r) => setTimeout(r, POLL_EVERY_MS));
      }
    }
    run();
    return () => {
      stopped = true;
    };
  }, [orderId, router, refresh]);

  return (
    <div className="mx-auto flex max-w-[620px] flex-col items-center gap-3 rounded-[24px] bg-soft px-5 py-16 text-center" aria-live="polite">
      {state === "waiting" && (
        <>
          <div className="size-11 animate-spin rounded-full border-[3px] border-line border-t-ink" role="img" aria-label="Loading" />
          <h1 className="text-[26px]">Confirming payment…</h1>
          <p className="text-muted">Please keep this page open. It usually takes a few seconds.</p>
        </>
      )}
      {state === "failed" && (
        <>
          <h1 className="text-[26px]">Your payment didn&apos;t go through</h1>
          <p className="text-muted">You haven&apos;t been charged.</p>
          <Link href="/checkout" className="btn btn-black">
            Try again
          </Link>
        </>
      )}
      {state === "slow" && (
        <>
          <h1 className="text-[26px]">This is taking longer than usual</h1>
          <p className="text-muted">If money left your account, your order will show as paid shortly.</p>
          <Link href={`/orders/${orderId}`} className="btn btn-black">
            Check your order
          </Link>
        </>
      )}
    </div>
  );
}
