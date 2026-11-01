"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/context";
import { PageHeader } from "@/components/PageHeader";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { signIn, isConfigured } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    const { error: err } = await signIn(email, password);
    if (err) {
      setError(err);
      setLoading(false);
    } else {
      router.push("/app/twin");
    }
  };

  return (
    <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
      <PageHeader
        title="Sign in"
        subtitle="Access your CareerTwin intelligence system."
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
              className="rounded-sm border border-border-soft bg-background px-4 py-2 font-mono text-sm focus:border-accent outline-none transition-colors"
            />
          </label>
          {error && (
            <div className="rounded-sm border border-red/30 bg-red/10 p-4 text-red text-sm">
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={loading || !isConfigured}
            className="inline-flex items-center justify-center gap-2 rounded-sm border border-border-soft bg-panel px-6 py-3 font-medium text-sm transition-colors hover:bg-panel-hover disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
          <p className="text-mono-xs text-muted-soft text-center">
            No account?{" "}
            <Link href="/auth/signup" className="text-accent hover:underline">
              Sign up
            </Link>
          </p>
        </div>
      </form>
    </div>
  );
}
