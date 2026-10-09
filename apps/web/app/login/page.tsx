"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { GraduationCap, Lock, Mail, School, Sparkles, User as UserIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { login, register } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [isRegister, setIsRegister] = useState(false);
  const [error, setError] = useState<string>();
  const [success, setSuccess] = useState<string>();
  const [isSubmitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(undefined);
    setSuccess(undefined);
    setSubmitting(true);

    const formData = new FormData(event.currentTarget);
    const email = String(formData.get("email") || "");
    const password = String(formData.get("password") || "");

    try {
      if (isRegister) {
        const displayName = String(formData.get("display_name") || "");
        const collegeName = String(formData.get("college_name") || "");
        const courseName = String(formData.get("course_name") || "");

        await register({
          email,
          password,
          display_name: displayName,
          college_name: collegeName || undefined,
          course_name: courseName || undefined,
        });
        setSuccess("Account created successfully! Redirecting to study dashboard…");
      } else {
        await login(email, password);
        setSuccess("Signed in successfully! Redirecting…");
      }

      setTimeout(() => {
        router.push("/dashboard");
      }, 600);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Authentication failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <Link href="/" className="inline-flex items-center gap-2 text-2xl font-bold tracking-tight text-slate-900">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-md shadow-indigo-200">
            <Sparkles className="h-5 w-5" />
          </div>
          <span>Study<span className="text-indigo-600">Flow</span></span>
        </Link>
        <h2 className="mt-6 text-2xl font-bold tracking-tight text-slate-900">
          {isRegister ? "Start your academic journey" : "Welcome back, scholar"}
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          {isRegister
            ? "Create an account to organize your semesters, subjects, topics, and exams."
            : "Sign in to manage your study plan and exam schedules."}
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
          {/* Tab switcher */}
          <div className="mb-6 flex rounded-lg bg-slate-100 p-1">
            <button
              type="button"
              onClick={() => {
                setIsRegister(false);
                setError(undefined);
              }}
              className={`flex-1 rounded-md py-2 text-xs font-semibold transition-all ${
                !isRegister
                  ? "bg-white text-indigo-600 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setIsRegister(true);
                setError(undefined);
              }}
              className={`flex-1 rounded-md py-2 text-xs font-semibold transition-all ${
                isRegister
                  ? "bg-white text-indigo-600 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Create Account
            </button>
          </div>

          <form onSubmit={onSubmit} className="space-y-4">
            {isRegister && (
              <>
                <div>
                  <label className="block text-xs font-medium text-slate-700">Full Name *</label>
                  <div className="mt-1 relative rounded-md shadow-sm">
                    <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
                      <UserIcon className="h-4 w-4" />
                    </div>
                    <input
                      name="display_name"
                      type="text"
                      required
                      placeholder="e.g. Adarsh Sagar"
                      className="block w-full rounded-lg border border-slate-300 pl-10 pr-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-700">Course / Degree</label>
                    <div className="mt-1 relative rounded-md shadow-sm">
                      <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
                        <GraduationCap className="h-4 w-4" />
                      </div>
                      <input
                        name="course_name"
                        type="text"
                        placeholder="e.g. MCA"
                        className="block w-full rounded-lg border border-slate-300 pl-10 pr-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-700">College / Univ</label>
                    <div className="mt-1 relative rounded-md shadow-sm">
                      <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
                        <School className="h-4 w-4" />
                      </div>
                      <input
                        name="college_name"
                        type="text"
                        placeholder="e.g. Tech Inst"
                        className="block w-full rounded-lg border border-slate-300 pl-10 pr-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                      />
                    </div>
                  </div>
                </div>
              </>
            )}

            <div>
              <label className="block text-xs font-medium text-slate-700">Email Address *</label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
                  <Mail className="h-4 w-4" />
                </div>
                <input
                  name="email"
                  type="email"
                  required
                  placeholder="student@college.edu"
                  className="block w-full rounded-lg border border-slate-300 pl-10 pr-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700">Password *</label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
                  <Lock className="h-4 w-4" />
                </div>
                <input
                  name="password"
                  type="password"
                  required
                  placeholder={isRegister ? "At least 12 characters" : "Your password"}
                  minLength={isRegister ? 12 : 1}
                  maxLength={128}
                  autoComplete={isRegister ? "new-password" : "current-password"}
                  className="block w-full rounded-lg border border-slate-300 pl-10 pr-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
              {isRegister && (
                <p className="mt-1 text-[11px] text-slate-500">
                  Use 12+ characters with at least one uppercase letter, lowercase letter, and number.
                </p>
              )}
            </div>

            {error && (
              <div className="rounded-lg bg-rose-50 border border-rose-200 p-3 text-sm text-rose-700">
                {error}
              </div>
            )}

            {success && (
              <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-3 text-sm text-emerald-700">
                {success}
              </div>
            )}

            <Button className="w-full mt-2" type="submit" disabled={isSubmitting}>
              {isSubmitting
                ? "Processing…"
                : isRegister
                ? "Create Account & Get Started"
                : "Sign in to StudyFlow"}
            </Button>
          </form>

          <div className="mt-6 border-t border-slate-100 pt-4 text-center">
            <p className="text-xs text-slate-500">
              {isRegister ? (
                <>
                  Already have an account?{" "}
                  <button
                    type="button"
                    onClick={() => setIsRegister(false)}
                    className="font-medium text-indigo-600 hover:text-indigo-500"
                  >
                    Sign in
                  </button>
                </>
              ) : (
                <>
                  New to StudyFlow?{" "}
                  <button
                    type="button"
                    onClick={() => setIsRegister(true)}
                    className="font-medium text-indigo-600 hover:text-indigo-500"
                  >
                    Create a free account
                  </button>
                </>
              )}
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
