"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { signIn, signUp } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";
import { useSession } from "@/lib/session";

/** Only allow going back to a page on our own site (stops "?next=https://evil.example"). */
function safeNext(value: string | null): string {
  return value && value.startsWith("/") && !value.startsWith("//") ? value : "/";
}

export function AuthForm({ mode }: { mode: "signin" | "signup" }) {
  const router = useRouter();
  const next = safeNext(useSearchParams().get("next"));
  const { refresh } = useSession();
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email"));
    const password = String(form.get("password"));
    setBusy(true);
    setError(null);
    try {
      const user =
        mode === "signup" ? await signUp({ email, password, name: String(form.get("name")) }) : await signIn({ email, password });
      await refresh();
      toast(`Welcome${user.name ? ", " + user.name.split(" ")[0] : ""}`);
      router.push(next);
    } catch (e) {
      setError(e instanceof ApiError ? e : new ApiError(0, {}));
    } finally {
      setBusy(false);
    }
  }

  const other = mode === "signup" ? "/signin" : "/signup";
  return (
    <form onSubmit={submit} noValidate className="panel mx-auto flex max-w-[520px] flex-col gap-4">
      <h1 className="title text-[32px]">{mode === "signup" ? "Create your account" : "Sign in"}</h1>
      {mode === "signup" && (
        <div>
          <label className="field-label" htmlFor="name">
            Your name
          </label>
          <input id="name" name="name" className="input" autoComplete="name" />
        </div>
      )}
      <div>
        <label className="field-label" htmlFor="email">
          Email
        </label>
        <input id="email" name="email" type="email" className="input" autoComplete="email" required />
        {error?.fieldError("email") && <p className="field-error">{error.fieldError("email")}</p>}
      </div>
      <div>
        <label className="field-label" htmlFor="password">
          Password
        </label>
        <input
          id="password"
          name="password"
          type="password"
          className="input"
          autoComplete={mode === "signup" ? "new-password" : "current-password"}
          minLength={8}
          required
        />
        {error?.fieldError("password") && <p className="field-error">{error.fieldError("password")}</p>}
      </div>
      {error && !error.fieldError("email") && !error.fieldError("password") && (
        <p className="field-error" role="alert">
          {error.message}
        </p>
      )}
      <button className="btn btn-black btn-lg" disabled={busy}>
        {busy ? "Please wait…" : mode === "signup" ? "Create account" : "Sign in"}
      </button>
      <p className="text-center text-sm text-muted">
        {mode === "signup" ? "Already have an account? " : "New to HomeHaat? "}
        <Link href={`${other}?next=${encodeURIComponent(next)}`}>{mode === "signup" ? "Sign in" : "Create an account"}</Link>
      </p>
    </form>
  );
}
