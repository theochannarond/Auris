import type { CSSProperties } from "react";

interface TranscriptionProgressProps {
  status: string | null;
  processingMs?: number | null;
  errorMessage?: string | null;
}

const boxStyle: CSSProperties = {
  padding: "12px 20px",
  borderRadius: "8px",
  fontSize: "0.9rem",
  marginTop: "16px",
  width: "100%",
  maxWidth: "480px",
  textAlign: "center"
};

function formatSeconds(ms: number): string {
  return `${(ms / 1000).toFixed(1)} s`;
}

export default function TranscriptionProgress({
  status,
  processingMs,
  errorMessage
}: TranscriptionProgressProps) {
  if (!status) return null;

  if (status === "pending") {
    return (
      <div style={{ ...boxStyle, background: "#FFF3CD", color: "#7A4A00" }}>
        ⏳ Transcription en file d'attente...
      </div>
    );
  }

  if (status === "processing") {
    return (
      <div style={{ ...boxStyle, background: "#E0EAF5", color: "#1E3A5F" }}>
        {/* Barre indéterminée : Voxtral ne renvoie pas de pourcentage d'avancement */}
        <style>{`
          @keyframes auris-progress-slide {
            0%   { transform: translateX(-100%); }
            100% { transform: translateX(300%); }
          }
        `}</style>
        <p style={{ fontWeight: 500, marginBottom: "12px" }}>
          Transcription de votre enregistrement en cours...
        </p>
        <div style={{
          height: "6px",
          borderRadius: "3px",
          background: "#C3D4E8",
          overflow: "hidden"
        }}>
          <div style={{
            height: "100%",
            width: "33%",
            borderRadius: "3px",
            background: "#2C5F8A",
            animation: "auris-progress-slide 1.4s ease-in-out infinite"
          }} />
        </div>
        <p style={{ fontSize: "0.8rem", marginTop: "10px", color: "#4A6B8A" }}>
          Cela peut prendre quelques minutes selon la durée de la réunion.
        </p>
      </div>
    );
  }

  if (status === "completed") {
    return (
      <div style={{ ...boxStyle, background: "#D6F5E3", color: "#0A4A25", fontWeight: 500 }}>
        ✓ Transcription terminée
        {processingMs != null && (
          <span style={{ fontWeight: 400, display: "block", fontSize: "0.8rem", marginTop: "4px" }}>
            Traitée en {formatSeconds(processingMs)}
          </span>
        )}
      </div>
    );
  }

  if (status === "failed") {
    return (
      <div style={{ ...boxStyle, background: "#FAD7D7", color: "#7A0A0A" }}>
        ✗ La transcription a échoué.
        {errorMessage && (
          <span style={{ display: "block", fontSize: "0.8rem", marginTop: "4px" }}>
            {errorMessage}
          </span>
        )}
      </div>
    );
  }

  return null;
}
