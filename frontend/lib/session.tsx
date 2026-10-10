"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { getMe } from "./api/auth";
import { getCart } from "./api/cart";
import type { User } from "./api/types";

interface Session {
  user: User | null;
  loading: boolean;
  bagCount: number;
  /** Re-read the user and bag count from the server (after sign-in, add to bag, payment…). */
  refresh: () => Promise<void>;
}

const SessionContext = createContext<Session | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [bagCount, setBagCount] = useState(0);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const me = await getMe();
      setUser(me);
      setBagCount(me ? (await getCart()).count : 0);
    } catch {
      setUser(null);
      setBagCount(0);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Read the session once when the app loads. This is the standard way to
    // sync React state with an outside system (the server), so the lint rule doesn't apply.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh();
  }, [refresh]);

  return <SessionContext.Provider value={{ user, loading, bagCount, refresh }}>{children}</SessionContext.Provider>;
}

export function useSession(): Session {
  const session = useContext(SessionContext);
  if (!session) throw new Error("useSession must be used inside <SessionProvider>");
  return session;
}
