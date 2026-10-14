/**
 * Wake the free server before something that must not fail halfway (pressing Pay).
 *
 * Render's free server goes to sleep after 15 quiet minutes, and the first request after that waits up to about a
 * minute while it starts. Reading pages copes on its own (apiFetch asks again), but checkout is a POST that holds
 * stock, so we first make sure the server is up with the harmless GET /api/health/, and tell the buyer why it's
 * taking a moment. Only then is the order created.
 */

const AWAKE_FOR_MS = 5 * 60_000; // after a reply we trust it's awake for a while (it sleeps after 15 min)
let lastAwake = Number.NEGATIVE_INFINITY;

type Options = {
  onSlow?: () => void; // called once if waking takes more than a couple of seconds ("Waking up the server…")
  deadlineMs?: number; // give up after this long in total
  pauseMs?: number; // wait between tries
  fetcher?: (url: string, init: RequestInit) => Promise<Response>; // for tests
  now?: () => number; // for tests
};

/** true = the server answered; false = it didn't wake up in time (nothing was sent that changes anything). */
export async function wakeServer({
  onSlow,
  deadlineMs = 100_000,
  pauseMs = 3000,
  fetcher = (url, init) => fetch(url, init),
  now = Date.now,
}: Options = {}): Promise<boolean> {
  const started = now();
  if (started - lastAwake < AWAKE_FOR_MS) return true;
  const slow = onSlow ? setTimeout(onSlow, 2500) : undefined;
  try {
    while (now() - started < deadlineMs) {
      try {
        // One try may wait a long time on its own: the host holds the request while the server starts.
        const reply = await fetcher("/api/health/", { cache: "no-store", signal: AbortSignal.timeout(70_000) });
        if (reply.ok) {
          lastAwake = now();
          return true;
        }
      } catch {
        // no reply yet (or timed out): try again below
      }
      await new Promise((r) => setTimeout(r, pauseMs));
    }
    return false;
  } finally {
    clearTimeout(slow);
  }
}

/** Tests only: forget that the server was awake. */
export function forgetAwake() {
  lastAwake = Number.NEGATIVE_INFINITY;
}
