import { useState, useEffect } from "react";
import { apiFetch } from "../services/api";

export interface ServiceStatus {
  name:       string;
  label:      string;
  status:     "up" | "down";
  latency_ms: number;
  error:      string | null;
}

export interface StatusReport {
  checked_at: string;
  overall:    "ok" | "degraded";
  services:   ServiceStatus[];
}

// Rafraîchissement automatique. Assez court pour qu'une panne se voie sans
// intervention, assez long pour ne pas sonder six services en boucle : la
// surveillance de fond, elle, tourne côté serveur toutes les 5 minutes.
const REFRESH_INTERVAL_MS = 30_000;

export function useServiceStatus() {
  const [report, setReport]   = useState<StatusReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState("");
  const [tick, setTick]       = useState(0);

  const refresh = () => setTick(t => t + 1);

  useEffect(() => {
    let cancelled = false;

    const fetchStatus = async () => {
      try {
        const res = await apiFetch("/api/v1/status/services");
        if (!res.ok) throw new Error("Erreur récupération de l'état des services");
        const data: StatusReport = await res.json();
        if (!cancelled) {
          setReport(data);
          setError("");
        }
      } catch {
        // On conserve volontairement le dernier rapport à l'écran : un état
        // daté, signalé comme tel, reste plus utile qu'une page vide — et
        // l'API injoignable est elle-même une information.
        if (!cancelled) {
          setError("Impossible de joindre l'API. L'état ci-dessous n'est plus à jour.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchStatus();
    const timer = setInterval(fetchStatus, REFRESH_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [tick]);

  return { report, loading, error, refresh };
}
