"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth/context";
import { PageHeader } from "@/components/PageHeader";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const { signUp, isConfigured } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    const { error: err } = await signUp(email, password);
    if (err) {
      setError(err);
      setLoading(false);
    } else {
      setSuccess(true);
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
        <PageHeader
          title="Check your email"
          subtitle="We've sent a confirmation link. Click it to activate your account."
        />
        <div className="mt-10">
          <Link
            href="/auth/login"
            className="inline-flex items-center gap-2 rounded-sm border border-border-soft bg-panel px-6 py-3 font-medium text-sm transition-colors hover:bg-panel-hover"
          >
            Go to sign in
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
      <PageHeader
        title="Create account"
        subtitle="Start building your CareerTwin."
      />

      {!isConfigured && (
        <div className="rounded-sm border border-border-soft bg-panel p-6 text-muted text-sm mb-6">
          Supabase is not configured. Set NEXT_PUBLIC_SUPABASE_URL and
          NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY to enable authentication.
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className="max-w-md rounded-sm border border-border-soft bg-panel p-8"
      >
        <div className="flex flex-col gap-4">
          <label className="flex flex-col gap-1">
            <span className="text-mono-xs font-medium text-muted">Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="rounded-sm border border-border-soft bg-background px-4 py-2 font-mono text-sm focus:border-accent outline-none transition-colors"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-mono-xs font-medium text-muted">Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              className="rounded-sm border border-border-soft bg-background px-4 py-2 font-mono text-sm focus:border-accent outline-none transition-colors"
            />
          </label>
          {error && (
            <div className="rounded-sm border border-red/30 bg-red/10 p-6 text-red text-sm">
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={loading || !isConfigured}
            className="inline-flex items-center justify-center gap-2 rounded-sm border border-border-soft bg-panel px-6 py-3 font-medium text-sm transition-colors hover:bg-panel-hover disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Creating account…" : "Create account"}
          </button>
          <p className="text-mono-xs text-muted-soft text-center">
            Already have an account?{" "}
            <Link href="/auth/login" className="text-accent hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </form>
    </div>
  );
}
