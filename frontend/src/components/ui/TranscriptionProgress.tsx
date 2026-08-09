interface TranscriptionProgressProps {
  status: string | null;
  processingMs?: number | null;
  errorMessage?: string | null;
}

const boxClass = "px-5 py-3 rounded-lg text-sm mt-4 w-full max-w-[480px] text-center";

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
      <div className={`${boxClass} bg-[#FFF3CD] text-[#7A4A00]`}>
        ⏳ Transcription en file d'attente...
      </div>
    );
  }

  if (status === "processing") {
    return (
      <div className={`${boxClass} bg-[#E0EAF5] text-[#1E3A5F]`}>
        {/* Barre indéterminée : Voxtral ne renvoie pas de pourcentage d'avancement */}
        <style>{`
          @keyframes auris-progress-slide {
            0%   { transform: translateX(-100%); }
            100% { transform: translateX(300%); }
          }
        `}</style>
        <p className="font-medium mb-3">
          Transcription de votre enregistrement en cours...
        </p>
        <div className="h-1.5 rounded-full bg-[#C3D4E8] overflow-hidden">
          <div
            className="h-full w-1/3 rounded-full bg-[#2C5F8A]"
            style={{ animation: "auris-progress-slide 1.4s ease-in-out infinite" }}
          />
        </div>
        <p className="text-xs mt-2.5 text-[#4A6B8A]">
          Cela peut prendre quelques minutes selon la durée de la réunion.
        </p>
      </div>
    );
  }

  if (status === "completed") {
    return (
      <div className={`${boxClass} bg-[#D6F5E3] text-[#0A4A25] font-medium`}>
        ✓ Transcription terminée
        {processingMs != null && (
          <span className="font-normal block text-xs mt-1">
            Traitée en {formatSeconds(processingMs)}
          </span>
        )}
      </div>
    );
  }

  if (status === "failed") {
    return (
      <div className={`${boxClass} bg-[#FAD7D7] text-[#7A0A0A]`}>
        ✗ La transcription a échoué.
        {errorMessage && (
          <span className="block text-xs mt-1">
            {errorMessage}
          </span>
        )}
      </div>
    );
  }

  return null;
}
