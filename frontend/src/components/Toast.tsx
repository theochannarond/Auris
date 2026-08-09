import { useEffect } from "react";

interface ToastProps {
  message: string;
  type?:   "error" | "success" | "warning";
  onClose: () => void;
}

const BG_COLOR: Record<string, string> = {
  error:   "#B91C1C",
  success: "#0A4A25",
  warning: "#7A4A00",
};

export default function Toast({ message, type = "error", onClose }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(onClose, 5000);
    return () => clearTimeout(timer);
  }, [onClose]);

  return (
    <div style={{
      position: "fixed", bottom: "24px", right: "24px",
      backgroundColor: BG_COLOR[type], color: "white",
      padding: "12px 20px", borderRadius: "8px",
      boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
      maxWidth: "320px", fontSize: "0.9rem"
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px" }}>
        <p style={{ margin: 0 }}>{message}</p>
        <button
          onClick={onClose}
          style={{
            background: "transparent", border: "none",
            color: "white", cursor: "pointer",
            fontSize: "1rem", padding: 0, lineHeight: 1
          }}
        >
          ✕
        </button>
      </div>
    </div>
  );
}