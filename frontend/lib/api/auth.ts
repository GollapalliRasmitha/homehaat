import { apiFetch } from "./client";
import type { Address, NewAddress, User } from "./types";

export const getMe = () => apiFetch<{ user: User | null }>("/auth/me/").then((r) => r.user);

export const signUp = (body: { email: string; password: string; name: string }) =>
  apiFetch<User>("/auth/signup/", { method: "POST", body });

export const signIn = (body: { email: string; password: string }) =>
  apiFetch<User>("/auth/signin/", { method: "POST", body });

export const signOut = () => apiFetch<{ ok: true }>("/auth/signout/", { method: "POST" });

export const listAddresses = () => apiFetch<Address[]>("/addresses/");

export const addAddress = (body: NewAddress) => apiFetch<Address>("/addresses/", { method: "POST", body });
