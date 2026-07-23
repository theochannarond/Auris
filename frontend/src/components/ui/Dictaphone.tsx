import { useAudioRecorder } from "../../hooks/useAudioRecorder";

function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes.toString().padStart(2, "0")}:${remainingSeconds.toString().padStart(2, "0")}`;
}

export default function Dictaphone() {
  const {
    isRecording,
    isPaused,
    duration,
    audioBlob,
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    resetRecording,
  } = useAudioRecorder();

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "24px",
        fontFamily: "Arial, sans-serif",
        padding: "32px",
      }}
    >
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
        {!isRecording && (
          <button
            onClick={startRecording}
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
              onClick={isPaused ? resumeRecording : pauseRecording}
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
              onClick={stopRecording}
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

        {!isRecording && audioBlob && (
          <button
            onClick={resetRecording}
            style={{
              backgroundColor: "transparent",
              color: "#6B7280",
              border: "1px solid #6B7280",
              padding: "12px 32px",
              borderRadius: "8px",
              fontSize: "1rem",
              cursor: "pointer",
            }}
          >
            Recommencer
          </button>
        )}
      </div>
    </div>
  );
}