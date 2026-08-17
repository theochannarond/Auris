import { useState, useEffect, useRef } from "react";
import { apiFetch } from "../services/api";


interface MeetingStatus {
  id: string;
  status: string;
}

export function useMeetingStatus(meetingId: string | null, pollingInterval = 3000) {
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string>("");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!meetingId) return;

    const fetchStatus = async () => {
      try {
        const res = await apiFetch(`/api/v1/meetings/${meetingId}/status`);
        if (!res.ok) throw new Error("Erreur récupération statut");
        const data: MeetingStatus = await res.json();
        setStatus(data.status);

        // Arrêter le polling si statut final
        if (["recording", "processing", "completed", "failed"].includes(data.status)) {
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
        }
      } catch {
        setError("Impossible de récupérer le statut de la réunion.");
      }
    };

    // Premier appel immédiat
    fetchStatus();

    // Polling toutes les 3 secondes
    intervalRef.current = setInterval(fetchStatus, pollingInterval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [meetingId, pollingInterval]);

  return { status, error };
}