import { useState, useEffect } from "react";
import { apiFetch } from "../services/api";


export interface MeetingListItem {
  id:           string;
  title:        string;
  mode:         string;
  status:       string;
  duration_sec: number | null;
  created_at:   string;
  theme:        string | null;
  tone:         string | null;
}

export function useMeetings() {
  const [meetings, setMeetings] = useState<MeetingListItem[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState("");

  useEffect(() => {
    let cancelled = false;

    const fetchMeetings = async () => {
      try {
        const res = await apiFetch("/api/v1/meetings");
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
    return () => { cancelled = true; };
  }, []);

  const deleteMeeting = async (meetingId: string): Promise<string> => {
    const res = await apiFetch(`/api/v1/meetings/${meetingId}`, {
      method: "DELETE"
    });
    if (!res.ok) throw new Error("Suppression échouée");
    setMeetings(prev => prev.filter(m => m.id !== meetingId));
    return "Réunion supprimée conformément au RGPD Art. 17.";
  };

  return { meetings, loading, error, deleteMeeting };
}