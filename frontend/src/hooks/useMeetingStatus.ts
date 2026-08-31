import { useState, useEffect, useRef } from "react";
import { apiFetch } from "../services/api";


interface MeetingStatus {
  id: string;
  status: string;
  started_at: string | null;
}

export function useMeetingStatus(meetingId: string | null, pollingInterval = 3000) {
  const [status, setStatus] = useState<string | null>(null);
  // Renseigné uniquement quand le bot est entré dans la réunion. C'est ce qui
  // permet de distinguer un échec de connexion d'une réunion sans parole.
  const [startedAt, setStartedAt] = useState<string | null>(null);
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
        setStartedAt(data.started_at ?? null);

        // Arrêter le polling seulement sur un statut VRAIMENT final.
        // "recording" et "processing" figuraient ici : le suivi s'arrêtait dès
        // que le bot entrait dans la réunion, si bien que la page restait
        // bloquée sur « le bot a rejoint » et n'affichait jamais la suite.
        if (["completed", "failed"].includes(data.status)) {
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

  return { status, startedAt, error };
}