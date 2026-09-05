import { useState, useEffect, useRef } from "react";
import { apiFetch } from "../services/api";


interface SummaryStatus {
  id: string;
  meeting_id: string;
  content: string;
  decisions: string[] | null;
  action_items: string[] | null;
  tone: string | null;
  theme: string | null;
  processing_ms: number | null;
}

export function useSummaryStatus(summaryId: string | null, pollingInterval = 3000) {
  const [summary, setSummary] = useState<SummaryStatus | null>(null);
  const [error, setError] = useState<string>("");
  // Une génération qui échoue laisse le résumé écarté côté serveur : la route
  // répond alors 404. Sans cet état, le suivi tournait indéfiniment et la barre
  // de progression ne s'arrêtait jamais.
  const [failed, setFailed] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!summaryId) return;

    setSummary(null);
    setError("");
    setFailed(false);

    const stopPolling = () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };

    const fetchStatus = async () => {
      try {
        const res = await apiFetch(`/api/v1/summaries/${summaryId}`);

        // 404 : le serveur a abandonné cette génération. C'est définitif,
        // inutile de continuer à interroger.
        if (res.status === 404) {
          setFailed(true);
          stopPolling();
          return;
        }
        // Autre erreur : probablement passagère, la prochaine tentative
        // rattrapera dans 3 secondes.
        if (!res.ok) throw new Error("Erreur récupération résumé");

        const data: SummaryStatus = await res.json();
        setSummary(data);

        if (data.content && data.content.trim() !== "") {
          stopPolling();
        }
      } catch {
        setError("Impossible de récupérer le compte-rendu.");
      }
    };

    fetchStatus();
    intervalRef.current = setInterval(fetchStatus, pollingInterval);

    return stopPolling;
  }, [summaryId, pollingInterval]);

  return { summary, error, failed };
}