import { useState, useEffect } from "react";
import { apiFetch } from "../services/api";


export interface DiarizationSegment {
  speaker: string;
  start: number;
  end: number;
  text: string;
}

export interface MeetingTranscription {
  id: string;
  status: string;
  raw_text: string | null;
  diarization: DiarizationSegment[] | null;
  language: string | null;
  processing_ms: number | null;
}

export interface MeetingSummary {
  id: string;
  content: string;
  decisions: string[] | null;
  action_items: string[] | null;
  tone: string | null;
  theme: string | null;
  processing_ms: number | null;
  created_at: string;
}

export interface MeetingDetail {
  id: string;
  title: string;
  mode: string;
  status: string;
  meeting_link: string | null;
  started_at: string | null;
  ended_at: string | null;
  duration_sec: number | null;
  created_at: string;
  transcription: MeetingTranscription | null;
  summary: MeetingSummary | null;
}

export function useMeetingDetail(meetingId: string | undefined) {
  const [meeting, setMeeting] = useState<MeetingDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!meetingId) {
      setError("Réunion introuvable.");
      setLoading(false);
      return;
    }

    // Évite un setState après démontage si la réponse arrive trop tard
    let cancelled = false;

    const fetchDetail = async () => {
      try {
        const res = await apiFetch(`/api/v1/meetings/${meetingId}`);
        if (!res.ok) throw new Error("Erreur récupération de la réunion");
        const data: MeetingDetail = await res.json();
        if (!cancelled) setMeeting(data);
      } catch {
        if (!cancelled) setError("Impossible de charger cette réunion.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchDetail();

    return () => {
      cancelled = true;
    };
  }, [meetingId]);

  return { meeting, loading, error };
}
