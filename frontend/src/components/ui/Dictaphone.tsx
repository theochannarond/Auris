import Button from "./Button";

interface DictaphoneProps {
  isRecording: boolean;
  isPaused:    boolean;
  duration:    number;
  audioBlob:   Blob | null;
  onStart:     () => void;
  onStop:      () => void;
  onPause:     () => void;
  onResume:    () => void;
}

function formatDuration(seconds: number): string {
  const minutes         = Math.floor(seconds / 60);
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
}: DictaphoneProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-6 font-sans p-8 w-full max-w-[480px]">
      <div className="text-4xl tabular-nums">
        {formatDuration(duration)}
      </div>

      <div className="text-gray-500 text-sm">
        {isRecording
          ? isPaused
            ? "En pause"
            : "Enregistrement en cours..."
          : audioBlob
            ? "Enregistrement terminé"
            : "Prêt à enregistrer"}
      </div>

      <div className="flex gap-4 flex-wrap justify-center w-full">
        {!isRecording && !audioBlob && (
          <Button onClick={onStart} fullWidth>
            Enregistrer
          </Button>
        )}

        {isRecording && (
          <>
            <Button
              variant="secondary"
              onClick={isPaused ? onResume : onPause}
            >
              {isPaused ? "Reprendre" : "Pause"}
            </Button>
            <Button
              variant="danger"
              onClick={onStop}
            >
              Arrêter
            </Button>
          </>
        )}
      </div>
    </div>
  );
}