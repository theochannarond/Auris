interface DictaphoneProps {
  isRecording: boolean;
  isPaused: boolean;
  duration: number;
  audioBlob: Blob | null;
  onStart: () => void;
  onStop: () => void;
  onPause: () => void;
  onResume: () => void;
  onReset: () => void;
}

function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes.toString().padStart(2, "0")}:${remainingSeconds.toString().padStart(2, "0")}`;
}

export default function Dictaphone({
  isRecording,
  isPaused,
  duration,
  audioBlob,
  onStart,
  onStop,
  onPause,
  onResume,
  onReset,
}: DictaphoneProps) {
  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      gap: "24px",
      fontFamily: "Arial, sans-serif",
      padding: "32px",
    }}>
      <div style={{ fontSize: "2.5rem", fontVariantNumeric: "tabular-nums" }}>
        {formatDuration(duration)}
      </div>

      <div style={{ color: "#6B7280", fontSize: "0.9rem" }}>
        {isRecording
          ? isPaused
            ? "En pause"
            : "Enregistrement en cours..."
          : audioBlob
            ? "Enregistrement terminé"
            : "Prêt à enregistrer"}
      </div>

      <div style={{ display: "flex", gap: "16px" }}>
        {!isRecording && !audioBlob && (
          <button
            onClick={onStart}
            style={{
              backgroundColor: "#2C5F8A",
              color: "white",
              border: "none",
              padding: "12px 32px",
              borderRadius: "8px",
              fontSize: "1rem",
              cursor: "pointer",
            }}
          >
            Enregistrer
          </button>
        )}

        {isRecording && (
          <>
            <button
              onClick={isPaused ? onResume : onPause}
              style={{
                backgroundColor: "#9CA3AF",
                color: "white",
                border: "none",
                padding: "12px 32px",
                borderRadius: "8px",
                fontSize: "1rem",
                cursor: "pointer",
              }}
            >
              {isPaused ? "Reprendre" : "Pause"}
            </button>

            <button
              onClick={onStop}
              style={{
                backgroundColor: "#B91C1C",
                color: "white",
                border: "none",
                padding: "12px 32px",
                borderRadius: "8px",
                fontSize: "1rem",
                cursor: "pointer",
              }}
            >
              Arrêter
            </button>
          </>
        )}
      </div>
    </div>
  );
}