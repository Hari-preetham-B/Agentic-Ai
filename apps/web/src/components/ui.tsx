import type { ReactNode } from "react";
import Link from "next/link";

export function PageIntro({
  label,
  title,
  description,
  actions,
}: {
  label: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="mb-10 border-b border-border-soft pb-8">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="mb-3 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-accent">
            <span className="h-px w-6 bg-accent/60" aria-hidden="true" />
            {label}
          </p>
          <h1 className="max-w-3xl text-3xl font-semibold tracking-tight md:text-[2.75rem] md:leading-[1.1]">
            {title}
          </h1>
          {description && (
            <p className="mt-4 max-w-2xl text-sm leading-relaxed text-muted md:text-base">
              {description}
            </p>
          )}
        </div>
        {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
      </div>
    </header>
  );
}

export function Panel({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`border border-border-soft bg-panel/70 ${className}`}
    >
      {children}
    </div>
  );
}

export function SectionTitle({
  index,
  title,
  meta,
}: {
  index?: string;
  title: string;
  meta?: ReactNode;
}) {
  return (
    <div className="mb-4 flex items-end justify-between gap-4 border-b border-border-soft pb-3">
      <div className="flex items-baseline gap-3">
        {index && (
          <span className="font-mono text-[10px] tracking-wider text-muted-soft">
            {index}
          </span>
        )}
        <h2 className="text-lg font-medium tracking-tight">{title}</h2>
      </div>
      {meta && (
        <div className="font-mono text-[10px] text-muted">{meta}</div>
      )}
    </div>
  );
}

export function Stat({
  label,
  value,
  detail,
  accent = false,
}: {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  accent?: boolean;
}) {
  return (
    <div className="border border-border-soft bg-panel/60 p-5">
      <p className="font-mono text-[9px] uppercase tracking-[0.18em] text-muted">
        {label}
      </p>
      <p
        className={`mt-3 font-mono text-3xl font-medium tracking-tight ${
          accent ? "text-accent" : "text-foreground"
        }`}
      >
        {value}
      </p>
      {detail && (
        <p className="mt-2 text-[11px] leading-relaxed text-muted-soft">
          {detail}
        </p>
      )}
    </div>
  );
}

const PRIORITY_STYLES: Record<string, string> = {
  P0: "border-red-600 bg-red-600 text-white",
  P1: "border-red-300 bg-red-50 text-red-700",
  P2: "border-border-soft bg-background text-muted",
};

export function PriorityBadge({ priority }: { priority: string }) {
  return (
    <span
      className={`inline-flex border px-2 py-0.5 font-mono text-[9px] uppercase tracking-wider ${
        PRIORITY_STYLES[priority] ?? PRIORITY_STYLES.P2
      }`}
    >
      {priority}
    </span>
  );
}

const CONFIDENCE_STYLES: Record<string, string> = {
  SUPPORTED: "border-zinc-300 bg-zinc-100 text-zinc-700",
  INFERRED: "border-red-200 bg-red-50 text-red-700",
  UNCERTAIN: "border-border-muted bg-background text-muted",
  CONTRADICTED: "border-red-600 bg-red-600 text-white",
};

export function ConfidenceBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex border px-2.5 py-1 font-mono text-[9px] uppercase tracking-[0.14em] ${
        CONFIDENCE_STYLES[status] ?? CONFIDENCE_STYLES.UNCERTAIN
      }`}
    >
      {status.replaceAll("_", " ")}
    </span>
  );
}

const SKILL_STYLES: Record<string, string> = {
  MATCHED: "border-zinc-300 bg-zinc-100 text-zinc-700",
  PARTIAL: "border-red-200 bg-red-50 text-red-700",
  MISSING: "border-red-600 bg-red-600 text-white",
};

export function SkillStatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex border px-2 py-0.5 font-mono text-[9px] uppercase tracking-wider ${
        SKILL_STYLES[status] ?? "border-border-soft bg-background text-muted"
      }`}
    >
      {status}
    </span>
  );
}

export function Meter({
  value,
  label,
  tone = "accent",
}: {
  value: number;
  label?: string;
  tone?: "accent" | "emerald" | "amber";
}) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  const fill =
    tone === "emerald"
      ? "bg-zinc-800"
      : tone === "amber"
        ? "bg-red-400"
        : "bg-accent";
  return (
    <div>
      {label && (
        <div className="mb-2 flex justify-between font-mono text-[10px] text-muted">
          <span>{label}</span>
          <span>{pct.toFixed(0)}%</span>
        </div>
      )}
      <div className="h-1.5 w-full overflow-hidden bg-background">
        <div
          className={`h-full ${fill} transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export function EmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: ReactNode;
}) {
  return (
    <Panel className="p-8">
      <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-soft">
        Nothing here yet
      </p>
      <h3 className="mt-3 text-lg font-medium">{title}</h3>
      <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted">
        {body}
      </p>
      {action && <div className="mt-5">{action}</div>}
    </Panel>
  );
}

export function ButtonLink({
  href,
  children,
  variant = "secondary",
}: {
  href: string;
  children: ReactNode;
  variant?: "primary" | "secondary";
}) {
  const styles =
    variant === "primary"
      ? "border-accent bg-accent text-white hover:bg-accent-hover"
      : "border-border-soft bg-panel text-foreground hover:bg-panel-hover";
  return (
    <Link
      href={href}
      className={`inline-flex items-center justify-center border px-4 py-2.5 text-xs font-medium transition-colors ${styles}`}
    >
      {children}
    </Link>
  );
}

export function ErrorNote({ children }: { children: ReactNode }) {
  return (
    <div className="border border-red-200 bg-red-50 px-4 py-3 text-[12px] leading-relaxed text-red-700">
      {children}
    </div>
  );
}

export function Notice({ children }: { children: ReactNode }) {
  return (
    <div className="border border-border-soft bg-background px-4 py-3 font-mono text-[10px] leading-relaxed text-muted">
      {children}
    </div>
  );
}
