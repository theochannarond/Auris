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
    <div style={{
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      minHeight: "100vh",
      fontFamily: "Arial, sans-serif",
      padding: "32px 24px"
    }}>
      <h1 style={{ fontSize: "2rem", marginBottom: "8px" }}>Auris</h1>
      <h2 style={{ fontSize: "1.1rem", color: "#6B7280", marginBottom: "40px" }}>
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
        <div style={{
          marginTop: "32px",
          padding: "24px",
          background: "#F4F6FB",
          borderRadius: "12px",
          width: "100%",
          maxWidth: "480px",
          textAlign: "center"
        }}>
          <p style={{ color: "#374151", marginBottom: "16px", fontWeight: "500" }}>
            Aperçu de votre enregistrement
          </p>
          <audio
            controls
            src={URL.createObjectURL(audioBlob)}
            style={{ width: "100%", marginBottom: "20px" }}
          />
          <p style={{ color: "#6B7280", fontSize: "0.85rem", marginBottom: "20px" }}>
            Durée : {formatDuration(duration)}
          </p>
          <div style={{ display: "flex", gap: "12px", justifyContent: "center" }}>
            <button
              onClick={resetRecording}
              style={{
                padding: "10px 24px", borderRadius: "8px",
                border: "1px solid #D1D5DB", background: "white",
                color: "#374151", cursor: "pointer", fontSize: "0.9rem"
              }}
            >
              Recommencer
            </button>
            <button
              onClick={handleUpload}
              disabled={uploading}
              style={{
                padding: "10px 24px", borderRadius: "8px",
                border: "none",
                background: uploading ? "#9CA3AF" : "#2C5F8A",
                color: "white",
                cursor: uploading ? "not-allowed" : "pointer",
                fontSize: "0.9rem"
              }}
            >
              {uploading ? "Envoi en cours..." : "Envoyer pour transcription"}
            </button>
          </div>
        </div>
      )}

      {/* Confirmation upload */}
      {uploaded && (
        <div style={{
          marginTop: "32px",
          padding: "24px",
          background: "#D6F5E3",
          borderRadius: "12px",
          textAlign: "center",
          maxWidth: "480px",
          width: "100%"
        }}>
          <p style={{ color: "#0A4A25", fontWeight: "500", fontSize: "1.1rem" }}>
            ✓ Enregistrement envoyé avec succès
          </p>
          <button
            onClick={() => {
              resetRecording();
              setUploaded(false);
              setMeetingId(null);
              setTranscriptionId(null);
            }}
            style={{
              marginTop: "16px", padding: "10px 24px",
              borderRadius: "8px", border: "none",
              background: "#0A4A25", color: "white",
              cursor: "pointer", fontSize: "0.9rem"
            }}
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
        <p style={{ color: "#B91C1C", marginTop: "16px", fontSize: "0.9rem" }}>
          {error}
        </p>
      )}
    </div>
  );
}