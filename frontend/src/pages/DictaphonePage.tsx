import { useState } from "react";
import { useAudioRecorder } from "../hooks/useAudioRecorder";
import { useTranscriptionStatus } from "../hooks/useTranscriptionStatus";
import Dictaphone from "../components/ui/Dictaphone";
import TranscriptionProgress from "../components/ui/TranscriptionProgress";
import Button from "../components/ui/Button";

const MAX_RETRIES = 3;

function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remaining).padStart(2, "0")}`;
}

export default function DictaphonePage() {
  const {
    isRecording,
    isPaused,
    duration,
    audioBlob,
    micError,
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    resetRecording,
  } = useAudioRecorder();

  const [meetingId, setMeetingId] = useState<string | null>(null);
  const [transcriptionId, setTranscriptionId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploaded, setUploaded] = useState(false);
  const [error, setError] = useState("");
  const [uploadError, setUploadError] = useState("");
  const [retryCount, setRetryCount] = useState(0);

  const { status: transcriptionStatus, processingMs, errorMessage } =
    useTranscriptionStatus(transcriptionId);

  const handleStart = async () => {
    setError("");
    setUploaded(false);

    try {
      const res = await fetch("/api/v1/meetings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: `Réunion du ${new Date().toLocaleDateString("fr-FR")}` })
      });
      if (!res.ok) throw new Error("Impossible de créer la réunion");
      const data = await res.json();
      setMeetingId(data.id);
    } catch {
      setError("Erreur lors de la création de la réunion.");
      return;
    }

    await startRecording();
  };

  const handleUpload = async () => {
    if (!audioBlob || !meetingId) return;
    setUploading(true);
    setUploadError("");

    try {
      const formData = new FormData();
      formData.append("file", audioBlob, "recording.wav");

      const uploadRes = await fetch(`/api/v1/meetings/${meetingId}/audio`, {
        method: "POST",
        body: formData
      });
      if (!uploadRes.ok) throw new Error();

      await fetch(`/api/v1/meetings/${meetingId}/status`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "processing" })
      });

      const transcriptionRes = await fetch("/api/v1/transcriptions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ meeting_id: meetingId })
      });
      if (!transcriptionRes.ok) throw new Error("Erreur au lancement de la transcription");
      const transcription = await transcriptionRes.json();
      setTranscriptionId(transcription.id);
      setUploaded(true);
      setRetryCount(0);
    } catch {
      setUploadError("Échec de l'envoi de l'audio. Vérifiez votre connexion et réessayez.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen font-sans px-6 py-8">
      <h1 className="text-3xl mb-2">Auris</h1>
      <h2 className="text-lg text-gray-500 mb-10">
        Mode dictaphone
      </h2>

      <Dictaphone
        isRecording={isRecording}
        isPaused={isPaused}
        duration={duration}
        audioBlob={audioBlob}
        onStart={handleStart}
        onStop={stopRecording}
        onPause={pauseRecording}
        onResume={resumeRecording}
      />

      {/* Erreur d'accès micro */}
      {micError && (
        <p className="text-[#B91C1C] text-sm mt-4 text-center">
          {micError}
        </p>
      )}

      {/* Preview audio */}
      {audioBlob && !uploaded && (
        <div className="mt-8 p-6 bg-[#F4F6FB] rounded-xl w-full max-w-[480px] text-center">
          <p className="text-gray-700 mb-4 font-medium">
            Aperçu de votre enregistrement
          </p>
          <audio
            controls
            src={URL.createObjectURL(audioBlob)}
            className="w-full mb-5"
          />
          <p className="text-gray-500 text-sm mb-5">
            Durée : {formatDuration(duration)}
          </p>
          <div className="flex gap-3 justify-center flex-wrap">
            <Button variant="secondary" onClick={resetRecording}>
              Recommencer
            </Button>
            <Button
              onClick={handleUpload}
              disabled={uploading}
              loading={uploading}
            >
              {uploading ? "Envoi en cours..." : "Envoyer pour transcription"}
            </Button>
          </div>

          {/* Erreur d'upload avec retry */}
          {uploadError && (
            <div className="mt-4 text-center">
              <p className="text-[#B91C1C] text-sm mb-2">{uploadError}</p>
              {retryCount < MAX_RETRIES ? (
                <button
                  onClick={() => { setRetryCount(c => c + 1); handleUpload(); }}
                  className="px-5 py-2 rounded-lg border border-[#B91C1C] bg-white text-[#B91C1C] cursor-pointer text-sm"
                >
                  Réessayer ({MAX_RETRIES - retryCount} tentative{MAX_RETRIES - retryCount > 1 ? "s" : ""} restante{MAX_RETRIES - retryCount > 1 ? "s" : ""})
                </button>
              ) : (
                <p className="text-[#B91C1C] text-sm">
                  Échec après {MAX_RETRIES} tentatives. Contactez le support.
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Confirmation upload */}
      {uploaded && (
        <div className="mt-8 p-6 bg-[#D6F5E3] rounded-xl text-center max-w-[480px] w-full">
          <p className="text-[#0A4A25] font-medium text-lg">
            ✓ Enregistrement envoyé avec succès
          </p>
          <Button
            variant="primary"
            onClick={() => {
              resetRecording();
              setUploaded(false);
              setMeetingId(null);
              setTranscriptionId(null);
            }}
          >
            Nouvelle réunion
          </Button>
        </div>
      )}

      {/* Progression transcription */}
      {uploaded && (
        <TranscriptionProgress
          status={transcriptionStatus}
          processingMs={processingMs}
          errorMessage={errorMessage}
        />
      )}

      {/* Erreur création réunion */}
      {error && (
        <p className="text-[#B91C1C] mt-4 text-sm">
          {error}
        </p>
      )}
    </div>
  );
}