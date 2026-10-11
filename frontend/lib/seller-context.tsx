"use client";

import { createContext, useContext } from "react";

import type { Store } from "./api/types";

/** The signed-in seller's shop, shared by every page of the seller dashboard (app/seller/layout.tsx). */
export interface SellerContextValue {
  store: Store;
  setStore: (store: Store) => void;
}

export const SellerContext = createContext<SellerContextValue | null>(null);

export function useSeller(): SellerContextValue {
  const value = useContext(SellerContext);
  if (!value) throw new Error("useSeller must be used inside the seller dashboard");
  return value;
}
