"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useActiveProfile } from "@/lib/profile/context";
import { useAuth } from "@/lib/auth/context";

const navItems = [
  { number: "01", label: "TWIN", href: "/app/twin" },
  { number: "02", label: "CAREERS", href: "/app/careers" },
  { number: "03", label: "SKILLS", href: "/app/skills" },
  { number: "04", label: "ROADMAP", href: "/app/roadmap" },
  { number: "05", label: "INTERVIEW", href: "/app/interview" },
  { number: "06", label: "TRUST", href: "/app/trust" },
];

export function Navigation({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { user, signOut, authMode } = useAuth();
  const { profile, profiles, selectProfile } = useActiveProfile();

  return (
    <nav
      className="flex h-full flex-col border-r border-border bg-background"
      aria-label="Main navigation"
    >
      <div className="flex h-20 shrink-0 items-center justify-between border-b border-border px-6">
        <Link href="/" className="group flex items-baseline gap-2">
          <span className="font-mono text-[11px] font-bold tracking-[0.18em] text-foreground">
            CAREERTWIN
          </span>
          <span className="h-1 w-1 rounded-full bg-accent" aria-hidden="true" />
        </Link>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-6">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const active =
              pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  onClick={onNavigate}
                  aria-current={active ? "page" : undefined}
                  className={`group flex items-center gap-4 rounded-sm border px-3 py-2.5 transition-colors ${
                    active
                      ? "border-border-soft bg-panel text-foreground"
                      : "border-transparent text-muted hover:border-border-soft hover:bg-panel/60 hover:text-foreground"
                  }`}
                >
                  <span
                    className={`font-mono text-[10px] tracking-wider ${
                      active ? "text-accent" : "text-muted-soft"
                    }`}
                  >
                    {item.number}
                  </span>
                  <span className="font-mono text-xs font-medium tracking-[0.12em]">
                    {item.label}
                  </span>
                  {active && (
                    <span
                      className="ml-auto h-1 w-1 rounded-full bg-accent"
                      aria-hidden="true"
                    />
                  )}
                </Link>
              </li>
            );
          })}
        </ul>

        <div className="mt-8 border-t border-border-soft pt-6">
          <p className="mb-3 font-mono text-[10px] tracking-[0.18em] text-muted-soft">
            PROFILE
          </p>
          {profile ? (
            <div className="space-y-3">
              <div className="rounded-sm border border-border-soft bg-panel p-3">
                <p className="truncate text-sm font-medium text-foreground">
                  {profile.full_name || "Unnamed profile"}
                </p>
                <p className="truncate font-mono text-[10px] text-muted">
                  {profile.headline || profile.email || "No headline"}
                </p>
                <p className="mt-2 font-mono text-[10px] uppercase tracking-wider text-muted-soft">
                  {profile.profile_status}
                </p>
              </div>
              {profiles.length > 1 && (
                <label className="block">
                  <span className="sr-only">Switch profile</span>
                  <select
                    value={profile.id}
                    onChange={(e) => {
                      selectProfile(e.target.value);
                      onNavigate?.();
                    }}
                    className="w-full rounded-sm border border-border-soft bg-background px-2 py-2 font-mono text-[11px] text-muted outline-none focus:border-accent"
                  >
                    {profiles.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.full_name || p.id.slice(0, 8)} · {p.profile_status}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <Link
                href="/onboarding/profile"
                onClick={onNavigate}
                className="inline-flex font-mono text-[10px] text-muted transition-colors hover:text-foreground"
              >
                EDIT PROFILE →
              </Link>
            </div>
          ) : (
            <Link
              href="/onboarding/start"
              onClick={onNavigate}
              className="inline-flex font-mono text-[10px] text-muted transition-colors hover:text-foreground"
            >
              CREATE PROFILE →
            </Link>
          )}
        </div>
      </div>

      <div className="shrink-0 border-t border-border px-6 py-5">
        {user ? (
          <>
            <p className="mb-2 truncate font-mono text-[10px] text-muted">
              {user.email}
            </p>
            {authMode === "development" && (
              <p className="mb-2 font-mono text-[9px] uppercase tracking-wider text-accent/80">
                Local identity · fake auth
              </p>
            )}
            <button
              onClick={() => void signOut()}
              className="font-mono text-[10px] font-medium tracking-wider text-muted transition-colors hover:text-foreground"
            >
              SIGN OUT ↗
            </button>
          </>
        ) : (
          <Link
            href="/auth/login"
            onClick={onNavigate}
            className="font-mono text-[10px] font-medium tracking-wider text-muted transition-colors hover:text-foreground"
          >
            SIGN IN ↗
          </Link>
        )}
      </div>
    </nav>
  );
}
