import { useState } from "react";
import ClassificationBadges from "./ClassificationBadges";
import type { MeetingListItem } from "../../hooks/useMeetings";

interface MeetingCardProps {
  meeting: MeetingListItem;
  onDelete: (meetingId: string) => Promise<void>;
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

const actionButton = {
  border:       "1px solid #E5E7EB",
  borderRadius: "8px",
  background:   "white",
  padding:      "6px 12px",
  fontSize:     "0.8rem",
  cursor:       "pointer",
  fontFamily:   "inherit"
};

export default function MeetingCard({ meeting, onDelete }: MeetingCardProps) {
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting]     = useState(false);

  // La carte est enveloppée dans un <Link> : sans ça, chaque clic sur un
  // bouton déclencherait aussi la navigation vers le détail de la réunion
  const stopNavigation = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleConfirm = async (e: React.MouseEvent) => {
    stopNavigation(e);
    setDeleting(true);
    try {
      await onDelete(meeting.id);
      // Pas de setState au retour : la carte est démontée par le parent
    } catch {
      setDeleting(false);
      setConfirming(false);
    }
  };

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
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px" }}>
        <div style={{ fontSize: "1.05rem", fontWeight: 600, color: "#111827" }}>
          {meeting.title}
        </div>

        {!confirming && (
          <button
            type="button"
            onClick={(e) => { stopNavigation(e); setConfirming(true); }}
            style={{ ...actionButton, color: "#B91C1C", borderColor: "#FECACA", flexShrink: 0 }}
          >
            Supprimer
          </button>
        )}
      </div>

      <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", color: "#6B7280", fontSize: "0.85rem" }}>
        <span>{formatDate(meeting.created_at)}</span>
        <span>{formatDuration(meeting.duration_sec)}</span>
      </div>

      {/* Ne rend rien tant que le résumé n'a pas produit de thème ni de ton */}
      <ClassificationBadges theme={meeting.theme} tone={meeting.tone} />

      {/* Confirmation demandée dans la carte : pas de window.confirm, on reste
          dans le style du projet et l'utilisateur garde la réunion sous les yeux */}
      {confirming && (
        <div style={{
          display:      "flex",
          alignItems:   "center",
          flexWrap:     "wrap",
          gap:          "12px",
          padding:      "12px",
          borderRadius: "8px",
          background:   "#FEF2F2",
          border:       "1px solid #FECACA"
        }}>
          <span style={{ color: "#7F1D1D", fontSize: "0.85rem", flex: 1 }}>
            Supprimer définitivement cette réunion et toutes ses données ?
          </span>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={deleting}
            style={{
              ...actionButton,
              background:  deleting ? "#FCA5A5" : "#B91C1C",
              borderColor: deleting ? "#FCA5A5" : "#B91C1C",
              color:       "white",
              cursor:      deleting ? "default" : "pointer"
            }}
          >
            {deleting ? "Suppression..." : "Confirmer"}
          </button>
          <button
            type="button"
            onClick={(e) => { stopNavigation(e); setConfirming(false); }}
            disabled={deleting}
            style={{ ...actionButton, color: "#374151" }}
          >
            Annuler
          </button>
        </div>
      )}
    </div>
  );
}
