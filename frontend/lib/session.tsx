"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { toast } from "sonner";

import { getMe } from "./api/auth";
import { getCart, mergeGuestCart } from "./api/cart";
import type { User } from "./api/types";
import { clearGuestBag, countLines, readGuestBag } from "./guest-bag";

interface Session {
  user: User | null;
  loading: boolean;
  bagCount: number;
  /** The server couldn't be reached last time we asked (we don't know if you're signed in). */
  serverError: unknown;
  /** True only when the server confirmed nobody is signed in: safe to send people to Sign in. */
  signedOut: boolean;
  /** Re-read the user and bag count (after add to bag, payment…). */
  refresh: () => Promise<void>;
  /** Call right after sign-in or sign-up: moves the guest bag into the account, then refreshes. */
  signedIn: () => Promise<void>;
}

const SessionContext = createContext<Session | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [bagCount, setBagCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [serverError, setServerError] = useState<unknown>(null);

  const refresh = useCallback(async () => {
    try {
      const me = await getMe();
      setUser(me);
      // Signed in: the bag is on the server. Guest: it's in this browser.
      setBagCount(me ? (await getCart()).count : countLines(readGuestBag()));
      setServerError(null);
    } catch (error) {
      // Couldn't reach the server. Don't pretend you're signed out: keep what we knew and say what happened.
      setServerError(error);
    } finally {
      setLoading(false);
    }
  }, []);

  const signedIn = useCallback(async () => {
    const guestLines = readGuestBag();
    if (guestLines.length) {
      try {
        const { skipped } = await mergeGuestCart(guestLines);
        clearGuestBag();
        if (skipped.length) toast(`Not added to your bag: ${skipped.join(", ")}`);
      } catch {
        // keep the guest bag so nothing is lost; the next sign-in tries again
      }
    }
    await refresh();
  }, [refresh]);

  useEffect(() => {
    // Read the session once when the app loads. This is the standard way to
    // sync React state with an outside system (the server), so the lint rule doesn't apply.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh();
  }, [refresh]);

  return (
    <SessionContext.Provider
      value={{ user, loading, bagCount, serverError, signedOut: !loading && !user && !serverError, refresh, signedIn }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useSession(): Session {
  const session = useContext(SessionContext);
  if (!session) throw new Error("useSession must be used inside <SessionProvider>");
  return session;
}
