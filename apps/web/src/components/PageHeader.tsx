interface PageHeaderProps {
  title: string;
  subtitle?: string;
  label?: string;
}

export function PageHeader({ title, subtitle, label }: PageHeaderProps) {
  return (
    <div className="flex flex-col gap-2 mb-10">
      {label && (
        <span className="inline-flex items-center gap-1.5 rounded-sm border border-border-soft bg-panel px-2.5 py-0.5 text-mono-xs font-medium text-muted">
          {label}
        </span>
      )}
      <h1 className="text-3xl md:text-4xl font-semibold tracking-tight leading-tight">{title}</h1>
      {subtitle && (
        <p className="text-muted text-lg leading-relaxed max-w-[48rem]">{subtitle}</p>
      )}
    </div>
  );
}
