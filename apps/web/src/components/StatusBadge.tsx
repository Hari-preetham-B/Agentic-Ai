interface StatusBadgeProps {
  children: React.ReactNode;
}

export function StatusBadge({ children }: StatusBadgeProps) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-sm border border-border-soft bg-panel px-2.5 py-0.5 text-mono-xs font-medium text-muted">
      {children}
    </span>
  );
}
