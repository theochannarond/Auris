import { useState } from "react";
import { useAudioRecorder } from "../hooks/useAudioRecorder";
import { useTranscriptionStatus } from "../hooks/useTranscriptionStatus";
import Dictaphone from "../components/ui/Dictaphone";
import Spinner from "../components/Spinner";
import ProgressBar from "../components/ProgressBar";
import TranscriptionProgress from "../components/ui/TranscriptionProgress";
import { saveChunkToIndexedDB, clearChunksFromIndexedDB } from "../services/audioStorage";
import { useOfflineSync } from "../hooks/useOfflineSync";
import { useNetworkStatus } from "../hooks/useNetworkStatus";
import { apiFetch } from "../services/api";
import { Link } from "react-router-dom";

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

  const {
    status: transcriptionStatus,
    processingMs,
    errorMessage,
  } = useTranscriptionStatus(transcriptionId);

  const handleStart = async () => {
    setError("");
    setUploaded(false);

    try {
      const res = await apiFetch("/api/v1/meetings", {
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

  const handleUploadBlob = async (blob: Blob) => {
    if (!meetingId) return;
    setUploading(true);
    setUploadError("");

    try {
      const formData = new FormData();
      formData.append("file", blob, "recording.wav");

      const uploadRes = await apiFetch(`/api/v1/meetings/${meetingId}/audio`, {
        method: "POST",
        body: formData
      });
      if (!uploadRes.ok) throw new Error();

      await apiFetch(`/api/v1/meetings/${meetingId}/status`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "processing" })
      });

      const transcriptionRes = await apiFetch("/api/v1/transcriptions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ meeting_id: meetingId })
      });
      if (!transcriptionRes.ok) throw new Error("Erreur au lancement de la transcription");
      const transcription = await transcriptionRes.json();
      setTranscriptionId(transcription.id);
      setUploaded(true);
      setRetryCount(0);

      // Nettoyage IndexedDB après upload réussi
      await clearChunksFromIndexedDB(meetingId);
    } catch {
      setUploadError("Échec de l'envoi de l'audio. Vérifiez votre connexion et réessayez.");
    } finally {
      setUploading(false);
    }
  };

  const handleUpload = async () => {
    if (!audioBlob || !meetingId) return;
    await handleUploadBlob(audioBlob);
  };

  const isBusy = uploading || transcriptionStatus === "processing";

  const { isOnline } = useNetworkStatus();

  useOfflineSync({
    meetingId,
    onSynced: (blob) => handleUploadBlob(blob),
    onSyncFail: (error) => setError(error),
  });

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
      <Link to="/dashboard" style={{ color: "#2C5F8A", fontSize: "0.85rem", textDecoration: "none", marginBottom: "32px", alignSelf: "flex-start" }}>
        ← Retour au dashboard
      </Link>
      <h1 style={{ fontSize: "2rem", marginBottom: "8px" }}>Auris</h1>
      <h2 style={{ fontSize: "0.9rem", color: "#6B7280", marginBottom: "40px" }}>
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

      {micError && (
        <p style={{ color: "#B91C1C", fontSize: "0.9rem", marginTop: "16px", textAlign: "center" }}>
          {micError}
        </p>
      )}

      {!isOnline && isRecording && (
        <p className="text-[#7A4A00] text-sm mt-4 text-center">
          ⚠ Connexion perdue — l'enregistrement continue localement.
        </p>
      )}

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
              disabled={isBusy}
              style={{
                padding: "10px 24px", borderRadius: "8px",
                border: "1px solid #D1D5DB", background: "white",
                color: "#374151",
                cursor: isBusy ? "not-allowed" : "pointer",
                fontSize: "0.9rem"
              }}
            >
              Recommencer
            </button>
            <button
              onClick={handleUpload}
              disabled={isBusy}
              style={{
                padding: "10px 24px", borderRadius: "8px",
                border: "none",
                backgroundColor: isBusy ? "#9CA3AF" : "#2C5F8A",
                color: "white",
                cursor: isBusy ? "not-allowed" : "pointer",
                fontSize: "0.9rem",
                display: "flex", alignItems: "center", gap: "8px",
                justifyContent: "center"
              }}
            >
              {uploading ? <Spinner size={16} /> : "Envoyer pour transcription"}
            </button>
          </div>

          {uploading && (
            <div style={{ marginTop: "16px", width: "100%", maxWidth: "480px" }}>
              <ProgressBar label="Envoi de l'enregistrement en cours..." />
            </div>
          )}

          {uploadError && (
            <div style={{ marginTop: "16px", textAlign: "center" }}>
              <p style={{ color: "#B91C1C", fontSize: "0.9rem", marginBottom: "8px" }}>
                {uploadError}
              </p>
              {retryCount < MAX_RETRIES ? (
                <button
                  onClick={() => { setRetryCount(c => c + 1); handleUpload(); }}
                  style={{
                    padding: "8px 20px", borderRadius: "8px",
                    border: "1px solid #B91C1C", background: "white",
                    color: "#B91C1C", cursor: "pointer", fontSize: "0.9rem"
                  }}
                >
                  Réessayer ({MAX_RETRIES - retryCount} tentative{MAX_RETRIES - retryCount > 1 ? "s" : ""} restante{MAX_RETRIES - retryCount > 1 ? "s" : ""})
                </button>
              ) : (
                <p style={{ color: "#B91C1C", fontSize: "0.85rem" }}>
                  Échec après {MAX_RETRIES} tentatives. Contactez le support.
                </p>
              )}
            </div>
          )}
        </div>
      )}
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
          <p style={{ color: "#0A4A25", fontSize: "0.9rem", marginTop: "8px" }}>
            La transcription va démarrer automatiquement.
          </p>
          <button
            onClick={() => { resetRecording(); setUploaded(false); setMeetingId(null); setTranscriptionId(null); }}
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

      {/* Suivi du statut de la transcription */}
      {transcriptionId && (
        <TranscriptionProgress
          status={transcriptionStatus}
          processingMs={processingMs}
          errorMessage={errorMessage}
        />
      )}


      {error && (
        <p style={{ color: "#B91C1C", marginTop: "16px", fontSize: "0.9rem" }}>
          {error}
        </p>
      )}
    </div>
  );
}