import { useState } from "react";
import { useAudioRecorder } from "../hooks/useAudioRecorder";
import { useTranscriptionStatus } from "../hooks/useTranscriptionStatus";
import Dictaphone from "../components/ui/Dictaphone";
import TranscriptionProgress from "../components/ui/TranscriptionProgress";

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

  const { status: transcriptionStatus, processingMs, errorMessage } =
    useTranscriptionStatus(transcriptionId);

  const handleStart = async () => {
    setError("");
    setUploaded(false);

    // 1. Créer la réunion en base
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

    // 2. Démarrer l'enregistrement
    await startRecording();
  };

  const handleUpload = async () => {
    if (!audioBlob || !meetingId) return;
    setUploading(true);
    setError("");

    try {
      // 3. Upload audio vers OVH
      const formData = new FormData();
      formData.append("file", audioBlob, "recording.wav");

      const uploadRes = await fetch(`/api/v1/meetings/${meetingId}/audio`, {
        method: "POST",
        body: formData
      });
      if (!uploadRes.ok) throw new Error("Erreur lors de l'upload");

      // 4. Mettre à jour le statut → processing
      await fetch(`/api/v1/meetings/${meetingId}/status`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "processing" })
      });

      // 5. Déclencher la transcription — la réponse 202 porte l'id à suivre
      const transcriptionRes = await fetch("/api/v1/transcriptions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ meeting_id: meetingId })
      });
      if (!transcriptionRes.ok) throw new Error("Erreur au lancement de la transcription");
      const transcription = await transcriptionRes.json();
      setTranscriptionId(transcription.id);

      setUploaded(true);
    } catch {
      setError("Erreur lors de l'envoi de l'enregistrement.");
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

      {/* Composant dictaphone */}
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

      {/* Preview audio — affiché après arrêt */}
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
            <button
              onClick={resetRecording}
              className="px-6 py-2.5 rounded-lg border border-gray-300 bg-white text-gray-700 cursor-pointer text-sm min-h-[44px]"
            >
              Recommencer
            </button>
            <button
              onClick={handleUpload}
              disabled={uploading}
              className={`px-6 py-2.5 rounded-lg border-none text-white text-sm min-h-[44px] cursor-pointer disabled:cursor-not-allowed ${uploading ? "bg-gray-400" : "bg-[#2C5F8A]"}`}
            >
              {uploading ? "Envoi en cours..." : "Envoyer pour transcription"}
            </button>
          </div>
        </div>
      )}

      {/* Confirmation upload */}
      {uploaded && (
        <div className="mt-8 p-6 bg-[#D6F5E3] rounded-xl text-center max-w-[480px] w-full">
          <p className="text-[#0A4A25] font-medium text-lg">
            ✓ Enregistrement envoyé avec succès
          </p>
          <button
            onClick={() => {
              resetRecording();
              setUploaded(false);
              setMeetingId(null);
              setTranscriptionId(null);
            }}
            className="mt-4 px-6 py-2.5 rounded-lg border-none bg-[#0A4A25] text-white cursor-pointer text-sm min-h-[44px]"
          >
            Nouvelle réunion
          </button>
        </div>
      )}

      {/* Progression de la transcription — polling tant que le statut n'est pas terminal */}
      {uploaded && (
        <TranscriptionProgress
          status={transcriptionStatus}
          processingMs={processingMs}
          errorMessage={errorMessage}
        />
      )}

      {/* Erreur */}
      {error && (
        <p className="text-[#B91C1C] mt-4 text-sm">
          {error}
        </p>
      )}
    </div>
  );
}