"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { login } from "@/lib/api";

export default function LoginPage() {
  const [error, setError] = useState<string>();
  const [isSubmitting, setSubmitting] = useState(false);
  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(undefined); setSubmitting(true);
    const data = new FormData(event.currentTarget);
    try { await login(String(data.get("email")), String(data.get("password"))); setError("Login succeeded. Dashboard setup is next."); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to sign in."); }
    finally { setSubmitting(false); }
  }
  return <main className="grid min-h-screen place-items-center px-6"><form onSubmit={onSubmit} className="w-full max-w-sm rounded-2xl border bg-white p-8 shadow-sm"><Link href="/" className="text-lg font-bold">Study<span className="text-indigo-600">Flow</span></Link><h1 className="mt-8 text-2xl font-bold">Welcome back</h1><p className="mt-2 text-sm text-slate-600">Sign in to continue learning.</p><label className="mt-6 block text-sm font-medium">Email<input name="email" type="email" required className="mt-2 w-full rounded-lg border px-3 py-2" /></label><label className="mt-4 block text-sm font-medium">Password<input name="password" type="password" required className="mt-2 w-full rounded-lg border px-3 py-2" /></label>{error && <p className="mt-4 text-sm text-rose-600">{error}</p>}<Button className="mt-6 w-full" type="submit" disabled={isSubmitting}>{isSubmitting ? "Signing in…" : "Sign in"}</Button><p className="mt-5 text-center text-sm text-slate-600">New here? Registration API is ready for onboarding.</p></form></main>;
}
