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
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!summaryId) return;

    setSummary(null);
    setError("");

    const stopPolling = () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };

    const fetchStatus = async () => {
      try {
        const res = await apiFetch(`/api/v1/summaries/${summaryId}`);
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

  return { summary, error };
}