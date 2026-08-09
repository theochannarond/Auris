import type { InputHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?:       string;
  error?:       string;
  hint?:        string;
  fullWidth?:   boolean;
}

export default function Input({
  label,
  error,
  hint,
  fullWidth = true,
  className = "",
  id,
  ...props
}: InputProps) {
  const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");

  return (
    <div className={`flex flex-col gap-1.5 ${fullWidth ? "w-full" : ""}`}>
      {label && (
        <label
          htmlFor={inputId}
          className="text-sm font-medium text-[var(--text-h)]"
        >
          {label}
        </label>
      )}
      <input
        id={inputId}
        className={[
          "px-3 py-2.5 rounded-lg border text-base",
          "bg-white text-[var(--text-h)]",
          "placeholder:text-[var(--color-muted-light)]",
          "min-h-[var(--touch-target)]",
          "transition-colors duration-200",
          "outline-none",
          error
            ? "border-[var(--color-error)] focus:ring-2 focus:ring-[var(--color-error)] focus:ring-opacity-30"
            : "border-[var(--border)] focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)] focus:ring-opacity-20",
          "disabled:opacity-60 disabled:cursor-not-allowed disabled:bg-gray-50",
          className,
        ].join(" ")}
        {...props}
      />
      {error && (
        <p className="text-xs text-[var(--color-error)]">{error}</p>
      )}
      {hint && !error && (
        <p className="text-xs text-[var(--color-muted)]">{hint}</p>
      )}
    </div>
  );
}