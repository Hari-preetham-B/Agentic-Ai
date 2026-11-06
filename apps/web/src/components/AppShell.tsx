"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Navigation } from "@/components/Navigation";
import { useAuth } from "@/lib/auth/context";
import { ActiveProfileProvider, useActiveProfile } from "@/lib/profile/context";

function LoadingFrame({ label }: { label: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-6">
      <div className="flex flex-col items-center gap-4">
        <span className="font-mono text-[11px] tracking-[0.2em] text-muted">
          CAREERTWIN
        </span>
        <span className="h-px w-24 animate-pulse bg-border-soft" />
        <span className="font-mono text-[10px] uppercase tracking-wider text-muted-soft">
          {label}
        </span>
      </div>
    </div>
  );
}

function AuthRequired() {
  return (
    <div className="mx-auto flex min-h-[70vh] max-w-3xl flex-col justify-center px-6 py-16">
      <span className="mb-4 font-mono text-[10px] uppercase tracking-[0.2em] text-accent">
        Authentication required
      </span>
      <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">
        Your career twin is private.
      </h1>
      <p className="mt-4 max-w-xl text-base leading-relaxed text-muted">
        Sign in to access your CareerTwin, career analysis, skill gaps,
        roadmap, interview lab and evidence centre. Your data is isolated to
        your account.
      </p>
      <div className="mt-8 flex flex-wrap gap-3">
        <Link
          href="/auth/login"
          className="rounded-sm border border-accent bg-accent px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-accent-hover"
        >
          Sign in
        </Link>
        <Link
          href="/auth/signup"
          className="rounded-sm border border-border-soft bg-panel px-5 py-3 text-sm font-medium transition-colors hover:bg-panel-hover"
        >
          Create account
        </Link>
      </div>
    </div>
  );
}

function NoProfile() {
  return (
    <div className="mx-auto flex min-h-[70vh] max-w-3xl flex-col justify-center px-6 py-16">
      <span className="mb-4 font-mono text-[10px] uppercase tracking-[0.2em] text-accent">
        No profile yet
      </span>
      <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">
        Build your CareerTwin.
      </h1>
      <p className="mt-4 max-w-xl text-base leading-relaxed text-muted">
        Add your education, skills, projects, experience and career goals. A
        confirmed profile unlocks career fit, skill-gap mathematics, a
        dependency-aware roadmap, adaptive interviews and evidence
        verification.
      </p>
      <Link
        href="/onboarding/start"
        className="mt-8 w-fit rounded-sm border border-accent bg-accent px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-accent-hover"
      >
        Start onboarding
      </Link>
    </div>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  const { user, loading: authLoading, authMode } = useAuth();
  const { loading: profileLoading, profile, error } = useActiveProfile();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => setMenuOpen(false), 0);
    return () => window.clearTimeout(timer);
  }, [pathname]);

  if (authLoading) return <LoadingFrame label="Checking session" />;
  if (!user) return <AuthRequired />;
  if (profileLoading) return <LoadingFrame label="Resolving profile" />;

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-border bg-background/95 px-4 backdrop-blur lg:hidden">
        <button
          onClick={() => setMenuOpen(true)}
          className="flex h-9 w-9 flex-col items-center justify-center gap-1.5 rounded-sm border border-border-soft"
          aria-label="Open navigation"
          aria-expanded={menuOpen}
        >
          <span className="h-px w-4 bg-foreground" />
          <span className="h-px w-4 bg-foreground" />
          <span className="h-px w-4 bg-foreground" />
        </button>
        <span className="font-mono text-[11px] font-bold tracking-[0.18em]">
          CAREERTWIN
        </span>
        <span
          className="h-1.5 w-1.5 rounded-full bg-accent"
          aria-hidden="true"
        />
      </header>

      {menuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            className="absolute inset-0 bg-black/30"
            onClick={() => setMenuOpen(false)}
            aria-label="Close navigation"
          />
          <div className="absolute inset-y-0 left-0 w-72 max-w-[85vw] shadow-2xl">
            <Navigation onNavigate={() => setMenuOpen(false)} />
          </div>
        </div>
      )}

      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 lg:block">
        <Navigation />
      </aside>

      <main className="min-w-0 lg:pl-64">
        {error && (
          <div className="border-b border-red-200 bg-red-50 px-5 py-3 font-mono text-[11px] text-red-700 lg:px-10">
            Could not load profiles: {error}
          </div>
        )}
        {authMode === "development" && (
          <div className="border-b border-accent/20 bg-accent/5 px-5 py-2 font-mono text-[10px] text-accent lg:px-10">
            LOCAL DEVELOPMENT IDENTITY — the backend must run with the
            FakeAuthProvider for requests to succeed. Configure Supabase public
            keys for real authentication.
          </div>
        )}
        {!profile ? (
          <NoProfile />
        ) : (
          <div className="mx-auto max-w-[1440px] px-5 py-8 md:px-8 lg:px-10 lg:py-10">
            {children}
          </div>
        )}
      </main>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <ActiveProfileProvider>
      <Shell>{children}</Shell>
    </ActiveProfileProvider>
  );
}
