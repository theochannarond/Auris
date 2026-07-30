import { useState, useEffect, useRef } from "react";

interface TranscriptionStatus {
  id: string;
  meeting_id: string;
  status: string;
  processing_ms: number | null;
  error_message: string | null;
}

// Statuts terminaux — une fois atteints, plus rien ne bougera
const FINAL_STATUSES = ["completed", "failed"];

export function useTranscriptionStatus(transcriptionId: string | null, pollingInterval = 3000) {
  const [status, setStatus] = useState<string | null>(null);
  const [processingMs, setProcessingMs] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [error, setError] = useState<string>("");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!transcriptionId) return;

    // Nouvelle transcription suivie — on repart d'un état propre
    setStatus(null);
    setProcessingMs(null);
    setErrorMessage(null);
    setError("");

    const stopPolling = () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };

    const fetchStatus = async () => {
      try {
        const res = await fetch(`/api/v1/transcriptions/${transcriptionId}/status`);
        if (!res.ok) throw new Error("Erreur récupération statut");
        const data: TranscriptionStatus = await res.json();

        setStatus(data.status);
        setProcessingMs(data.processing_ms);
        setErrorMessage(data.error_message);

        // On n'arrête le polling que sur un statut terminal
        if (FINAL_STATUSES.includes(data.status)) {
          stopPolling();
        }
      } catch {
        setError("Impossible de récupérer l'état de la transcription.");
      }
    };

    // Premier appel immédiat, puis polling
    fetchStatus();
    intervalRef.current = setInterval(fetchStatus, pollingInterval);

    return stopPolling;
  }, [transcriptionId, pollingInterval]);

  return { status, processingMs, errorMessage, error };
}
