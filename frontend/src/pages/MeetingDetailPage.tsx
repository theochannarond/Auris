import { useState, useEffect } from "react";
// @ts-ignore
import { Link, useParams } from "react-router-dom";
import { useMeetingDetail } from "../hooks/useMeetingDetail";
import { useSummaryStatus } from "../hooks/useSummaryStatus";
import SummaryDisplay from "../components/ui/SummaryDisplay";
import DiarizationDisplay from "../components/ui/DiarizationDisplay";
import Spinner from "../components/Spinner";
import ProgressBar from "../components/ProgressBar";

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

  const [summaryId, setSummaryId] = useState<string | null>(null);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [summaryError, setSummaryError] = useState("");
  const { summary: polledSummary } = useSummaryStatus(summaryId);

  useEffect(() => {
    if (polledSummary && polledSummary.content.trim() !== "") {
      setIsSummarizing(false);
    }
  }, [polledSummary]);

  const handleGenerateSummary = async () => {
    if (!meeting) return;
    setIsSummarizing(true);
    setSummaryError("");

    try {
      const response = await fetch("/api/v1/summaries", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ meeting_id: meeting.id })
      });
      if (!response.ok) throw new Error();
      const data = await response.json();
      setSummaryId(data.id);
    } catch {
      setSummaryError("Impossible de générer le compte-rendu pour le moment.");
      setIsSummarizing(false);
    }
  };

  const readySummary = polledSummary && polledSummary.content.trim() !== "" ? polledSummary : null;

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
          ) : readySummary ? (
            <SummaryDisplay
              content={readySummary.content}
              decisions={readySummary.decisions}
              action_items={readySummary.action_items}
              tone={readySummary.tone}
              theme={readySummary.theme}
              processingMs={readySummary.processing_ms}
            />
          ) : (
            <div>
              <p style={{ color: "#6B7280", fontSize: "0.9rem", marginBottom: "12px" }}>
                Aucun compte rendu n'a encore été généré pour cette réunion.
              </p>

              {meeting.transcription?.raw_text && (
                <button
                  onClick={handleGenerateSummary}
                  disabled={isSummarizing}
                  style={{
                    padding: "10px 24px", borderRadius: "8px",
                    border: "none",
                    backgroundColor: isSummarizing ? "#9CA3AF" : "#2C5F8A",
                    color: "white",
                    cursor: isSummarizing ? "not-allowed" : "pointer",
                    fontSize: "0.9rem",
                    display: "flex", alignItems: "center", gap: "8px"
                  }}
                >
                  {isSummarizing ? <Spinner size={16} /> : "Générer le compte-rendu"}
                </button>
              )}

              {isSummarizing && (
                <div style={{ marginTop: "16px", width: "100%", maxWidth: "480px" }}>
                  <ProgressBar label="Génération du compte-rendu en cours..." />
                </div>
              )}

              {summaryError && (
                <p style={{ color: "#B91C1C", fontSize: "0.85rem", marginTop: "8px" }}>
                  {summaryError}
                </p>
              )}
            </div>
          )}

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