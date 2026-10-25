interface RuleProps {
  className?: string;
}

export function Rule({ className }: RuleProps) {
  return (
    <hr
      className={`border-t border-border-soft my-8 ${className}`}
      aria-hidden="true"
    />
  );
}
