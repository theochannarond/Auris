import type { ReactNode } from "react";

interface CardProps {
  children:  ReactNode;
  className?: string;
  onClick?:  () => void;
  hoverable?: boolean;
  padding?:  "sm" | "md" | "lg";
}

const PADDING_CLASSES = {
  sm: "p-3",
  md: "p-4",
  lg: "p-6",
};

export default function Card({
  children,
  className = "",
  onClick,
  hoverable = false,
  padding   = "md",
}: CardProps) {
  return (
    <div
      onClick={onClick}
      className={[
        "rounded-xl border bg-white",
        "border-[var(--border)]",
        "shadow-sm",
        PADDING_CLASSES[padding],
        hoverable
          ? "cursor-pointer transition-shadow duration-200 hover:shadow-md"
          : "",
        className,
      ].join(" ")}
    >
      {children}
    </div>
  );
}