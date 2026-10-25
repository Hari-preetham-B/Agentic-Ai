"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { usePathname } from "next/navigation";

const navItems = [
  { label: "01 TWIN", href: "/app/twin" },
  { label: "02 CAREERS", href: "/app/careers" },
  { label: "03 SKILLS", href: "/app/skills" },
  { label: "04 ROADMAP", href: "/app/roadmap" },
  { label: "05 INTERVIEW", href: "/app/interview" },
  { label: "06 TRUST", href: "/app/trust" },
];

export function Navigation() {
  const pathname = usePathname();

  return (
    <nav
      className="fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-border bg-background"
      aria-label="Main navigation"
    >
      <div className="flex h-20 items-center justify-between border-b border-border px-6">
        <Link
          href="/"
          className="flex items-center gap-2"
          title="CareerTwin"
        >
          <span className="font-mono text-xs font-bold tracking-tighter text-muted">
            CAREERTWIN
          </span>
        </Link>
        <button className="p-2 text-muted hover:text-foreground transition-colors" aria-label="Menu">
          <span className="block w-4 h-[1px] bg-current"></span>
          <span className="block w-4 h-[1px] bg-current mt-1"></span>
          <span className="block w-4 h-[1px] bg-current mt-1"></span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto py-6 px-6">
        <div className="space-y-1">
          {navItems.map((item) => {
            const active = pathname === item.href;
            return (
              <motion.div
                key={item.label}
                whileHover={{ scale: 1.02 }}
                className="rounded-sm px-3 py-2 text-left transition-colors duration-200"
                style={{
                  backgroundColor: active ? "rgba(99, 102, 241, 0.08)" : "transparent",
                  border: active ? `1px solid ${"#242427"}` : "none",
                }}
              >
                <Link
                  href={item.href}
                  className="block font-mono text-xs font-medium tracking-tight"
                  aria-current={active ? "page" : undefined}
                >
                  {item.label}
                </Link>
              </motion.div>
            );
          })}
        </div>

        <div className="mt-8 pt-6 border-t border-border-soft">
          <Link
            href="/auth/login"
            className="inline-flex items-center gap-2 font-mono text-xs font-medium text-muted hover:text-foreground transition-colors"
          >
            PROFILE <span aria-hidden="true">↗</span>
          </Link>
          <p className="mt-2 text-mono-xs text-muted-soft max-w-[150px]">
            Authentication connects in a later phase.
          </p>
        </div>
      </div>
    </nav>
  );
}
