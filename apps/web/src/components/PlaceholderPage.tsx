interface PlaceholderPageProps {
  title: string;
  subtitle?: string;
  sectionLabel?: string;
}

export function PlaceholderPage({
  title,
  subtitle,
  sectionLabel = "FOUNDATION BUILD",
}: PlaceholderPageProps) {
  return (
    <div className="flex flex-col gap-6 py-10 px-6 md:px-10 lg:px-12">
      <div className="flex items-center gap-2">
        <span className="font-mono text-xs font-bold tracking-tighter text-muted uppercase">
          {sectionLabel}
        </span>
      </div>
      <h1 className="text-3xl md:text-4xl font-semibold tracking-tight">{title}</h1>
      {subtitle && <p className="text-muted text-lg leading-relaxed">{subtitle}</p>}
      <div className="rounded-sm border border-border-soft bg-panel p-8">
        <p className="text-muted-soft text-mono-sm">
          This page is a structural placeholder. Functionality will be connected in a later phase.
        </p>
      </div>
    </div>
  );
}
