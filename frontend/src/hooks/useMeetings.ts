import { useState, useEffect } from "react";

export interface MeetingListItem {
  id: string;
  title: string;
  mode: string;
  status: string;
  duration_sec: number | null;
  created_at: string;
  theme: string | null;
  tone: string | null;
}

export function useMeetings() {
  const [meetings, setMeetings] = useState<MeetingListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    // Évite un setState après démontage si la réponse arrive trop tard
    let cancelled = false;

    const fetchMeetings = async () => {
      try {
        const res = await fetch("/api/v1/meetings");
        if (!res.ok) throw new Error("Erreur récupération des réunions");
        const data: MeetingListItem[] = await res.json();
        if (!cancelled) setMeetings(data);
      } catch {
        if (!cancelled) setError("Impossible de charger vos réunions.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchMeetings();

    return () => {
      cancelled = true;
    };
  }, []);

  return { meetings, loading, error };
}
