import { Link, useParams } from "react-router-dom";
import { useMeetingDetail } from "../hooks/useMeetingDetail";
import SummaryDisplay from "../components/ui/SummaryDisplay";
import DiarizationDisplay from "../components/ui/DiarizationDisplay";

function formatDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString("fr-FR", {
    day:   "numeric",
    month: "long",
    year:  "numeric",
  });
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) return "Durée inconnue";
  const minutes = Math.floor(seconds / 60);
  const rest    = seconds % 60;
  if (minutes === 0) return `${rest} s`;
  return `${minutes} min ${String(rest).padStart(2, "0")} s`;
}

const sectionTitle = {
  fontSize:     "1rem",
  color:        "#2C5F8A",
  marginBottom: "16px",
  marginTop:    "40px"
};

export default function MeetingDetailPage() {
  const { meetingId } = useParams<{ meetingId: string }>();
  const { meeting, loading, error } = useMeetingDetail(meetingId);

  return (
    <div style={{
      fontFamily: "Arial, sans-serif",
      maxWidth:   "760px",
      margin:     "0 auto",
      padding:    "48px 24px"
    }}>
      <Link
        to="/dashboard"
        style={{ color: "#2C5F8A", fontSize: "0.9rem", textDecoration: "none" }}
      >
        ← Retour à l'historique
      </Link>

      {loading && (
        <p style={{ color: "#6B7280", marginTop: "32px" }}>Chargement de la réunion...</p>
      )}

      {error && (
        <p style={{ color: "#B91C1C", marginTop: "32px", fontSize: "0.9rem" }}>{error}</p>
      )}

      {!loading && !error && meeting && (
        <>
          <h1 style={{ fontSize: "1.8rem", margin: "24px 0 8px 0" }}>{meeting.title}</h1>
          <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", color: "#6B7280", fontSize: "0.85rem" }}>
            <span>{formatDate(meeting.created_at)}</span>
            <span>{formatDuration(meeting.duration_sec)}</span>
            <span>{meeting.mode === "video" ? "Réunion en ligne" : "Dictaphone"}</span>
          </div>

          {/* Résumé structuré — SummaryDisplay exige un contenu, on ne le monte que s'il existe */}
          <h2 style={sectionTitle}>Compte rendu</h2>
          {meeting.summary ? (
            <SummaryDisplay
              content={meeting.summary.content}
              decisions={meeting.summary.decisions}
              action_items={meeting.summary.action_items}
              tone={meeting.summary.tone}
              theme={meeting.summary.theme}
              processingMs={meeting.summary.processing_ms}
            />
          ) : (
            <p style={{ color: "#6B7280", fontSize: "0.9rem" }}>
              Aucun compte rendu n'a encore été généré pour cette réunion.
            </p>
          )}

          {/* Diarisation — le composant ne rend rien si la liste est vide */}
          {meeting.transcription?.diarization && meeting.transcription.diarization.length > 0 && (
            <>
              <h2 style={sectionTitle}>Prise de parole</h2>
              <DiarizationDisplay segments={meeting.transcription.diarization} />
            </>
          )}

          <h2 style={sectionTitle}>Transcription</h2>
          {meeting.transcription?.raw_text ? (
            <p style={{
              padding:      "20px",
              borderRadius: "10px",
              background:   "#F4F6FB",
              color:        "#1C1C1C",
              fontSize:     "0.9rem",
              lineHeight:   "1.65",
              whiteSpace:   "pre-wrap",
              margin:       0
            }}>
              {meeting.transcription.raw_text}
            </p>
          ) : (
            <p style={{ color: "#6B7280", fontSize: "0.9rem" }}>
              {meeting.transcription
                ? "La transcription est en cours de traitement."
                : "Aucune transcription n'a encore été lancée pour cette réunion."}
            </p>
          )}
        </>
      )}
    </div>
  );
}
