interface ProgressBarProps {
  progress?: number;      // 0 à 100 — si absent, mode indéterminé
  label?:    string;
}

export default function ProgressBar({ progress, label }: ProgressBarProps) {
  const isIndeterminate = progress === undefined;

  return (
    <div style={{ width: "100%" }}>
      {label && (
        <p style={{ fontSize: "0.85rem", color: "#6B7280", marginBottom: "6px" }}>
          {label}
        </p>
      )}
      <div style={{
        width: "100%", height: "6px",
        backgroundColor: "#E5E7EB", borderRadius: "3px",
        overflow: "hidden"
      }}>
        {isIndeterminate ? (
          <>
            <style>{`
              @keyframes indeterminate {
                0%   { transform: translateX(-100%); }
                100% { transform: translateX(300%); }
              }
            `}</style>
            <div style={{
              width: "33%", height: "100%",
              backgroundColor: "#2C5F8A", borderRadius: "3px",
              animation: "indeterminate 1.4s ease-in-out infinite"
            }} />
          </>
        ) : (
          <div style={{
            width: `${progress}%`, height: "100%",
            backgroundColor: "#2C5F8A", borderRadius: "3px",
            transition: "width 0.3s ease"
          }} />
        )}
      </div>
    </div>
  );
}