import ClassificationBadges from "./ClassificationBadges";
import type { MeetingListItem } from "../../hooks/useMeetings";

interface MeetingCardProps {
  meeting: MeetingListItem;
}

function formatDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString("fr-FR", {
    day:   "numeric",
    month: "long",
    year:  "numeric",
  });
}

function formatDuration(seconds: number | null): string {
  // duration_sec n'est pas encore alimenté côté backend — on l'assume plutôt que de masquer
  if (seconds === null) return "Durée inconnue";
  const minutes = Math.floor(seconds / 60);
  const rest    = seconds % 60;
  if (minutes === 0) return `${rest} s`;
  return `${minutes} min ${String(rest).padStart(2, "0")} s`;
}

export default function MeetingCard({ meeting }: MeetingCardProps) {
  return (
    <div style={{
      display:       "flex",
      flexDirection: "column",
      gap:           "12px",
      padding:       "20px",
      border:        "1px solid #E5E7EB",
      borderRadius:  "12px",
      background:    "white"
    }}>
      <div style={{ fontSize: "1.05rem", fontWeight: 600, color: "#111827" }}>
        {meeting.title}
      </div>

      <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", color: "#6B7280", fontSize: "0.85rem" }}>
        <span>{formatDate(meeting.created_at)}</span>
        <span>{formatDuration(meeting.duration_sec)}</span>
      </div>

      {/* Ne rend rien tant que le résumé n'a pas produit de thème ni de ton */}
      <ClassificationBadges theme={meeting.theme} tone={meeting.tone} />
    </div>
  );
}
