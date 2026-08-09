type BadgeVariant = "primary" | "success" | "warning" | "error" | "info" | "neutral";

interface BadgeProps {
  label:     string;
  variant?:  BadgeVariant;
  icon?:     string;
}

const VARIANT_CLASSES: Record<BadgeVariant, string> = {
  primary: "bg-[var(--color-primary-light)] text-[var(--color-primary)] border-[var(--color-primary)]",
  success: "bg-[var(--color-success-bg)] text-[var(--color-success)] border-[var(--color-success-border)]",
  warning: "bg-[var(--color-warning-bg)] text-[var(--color-warning)] border-[var(--color-warning-border)]",
  error:   "bg-[var(--color-error-bg)] text-[var(--color-error)] border-[var(--color-error-border)]",
  info:    "bg-[var(--color-info-bg)] text-[var(--color-info)] border-[var(--color-info-border)]",
  neutral: "bg-[var(--color-surface)] text-[var(--color-muted)] border-[var(--border)]",
};

export default function Badge({ label, variant = "neutral", icon }: BadgeProps) {
  return (
    <span className={[
      "inline-flex items-center gap-1.5",
      "px-3 py-1 rounded-full",
      "text-xs font-semibold border",
      VARIANT_CLASSES[variant],
    ].join(" ")}>
      {icon && <span>{icon}</span>}
      {label}
    </span>
  );
}