import type { ButtonHTMLAttributes, ReactNode } from "react";


type ButtonVariant = "primary" | "secondary" | "danger";
type ButtonSize    = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?:  ButtonVariant;
  size?:     ButtonSize;
  loading?:  boolean;
  fullWidth?: boolean;
  children:  ReactNode;
}

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:   "bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white border-transparent",
  secondary: "bg-white hover:bg-gray-50 text-gray-700 border-gray-300",
  danger:    "bg-[var(--color-error)] hover:opacity-90 text-white border-transparent",
};

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: "px-4 py-2 text-sm",
  md: "px-6 py-3 text-base",
  lg: "px-8 py-4 text-lg",
};

export default function Button({
  variant   = "primary",
  size      = "md",
  loading   = false,
  fullWidth = false,
  disabled,
  children,
  className = "",
  ...props
}: ButtonProps) {
  const isDisabled = disabled || loading;

  return (
    <button
      disabled={isDisabled}
      className={[
        "inline-flex items-center justify-center gap-2",
        "rounded-lg border font-medium",
        "transition-colors duration-200",
        "min-h-[var(--touch-target)]",
        "disabled:opacity-60 disabled:cursor-not-allowed",
        VARIANT_CLASSES[variant],
        SIZE_CLASSES[size],
        fullWidth ? "w-full" : "w-auto",
        className,
      ].join(" ")}
      {...props}
    >
      {loading && (
        <span
          style={{
            width: "14px", height: "14px",
            border: "2px solid currentColor",
            borderTopColor: "transparent",
            borderRadius: "50%",
            animation: "spin 0.8s linear infinite",
            flexShrink: 0
          }}
        />
      )}
      {children}
    </button>
  );
}