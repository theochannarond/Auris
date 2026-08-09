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

interface MeetingDeleteResponse {
  id: string;
  deleted_at: string;
  message: string;
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

  /**
   * Supprime une réunion et la retire de la liste affichée.
   * Renvoie le message de confirmation rédigé par le backend (RGPD Art.17).
   */
  const deleteMeeting = async (meetingId: string): Promise<string> => {
    const res = await fetch(`/api/v1/meetings/${meetingId}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Erreur suppression de la réunion");

    const data: MeetingDeleteResponse = await res.json();
    // Retrait local plutôt que rechargement : le backend filtre déjà les
    // réunions supprimées, un refetch renverrait exactement la même liste
    setMeetings((current) => current.filter((m) => m.id !== meetingId));
    return data.message;
  };

  return { meetings, loading, error, deleteMeeting };
}
