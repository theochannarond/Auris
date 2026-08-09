import { useState, useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { useMeetingDetail } from "../hooks/useMeetingDetail";
import { useSummaryStatus } from "../hooks/useSummaryStatus";
import SummaryDisplay from "../components/ui/SummaryDisplay";
import DiarizationDisplay from "../components/ui/DiarizationDisplay";
import Spinner from "../components/Spinner";
import ProgressBar from "../components/ProgressBar";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";

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

export default function MeetingDetailPage() {
  const { meetingId } = useParams<{ meetingId: string }>();
  const { meeting, loading, error } = useMeetingDetail(meetingId);

  const [summaryId, setSummaryId]       = useState<string | null>(null);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [summaryError, setSummaryError]  = useState("");
  const { summary: polledSummary }       = useSummaryStatus(summaryId);

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
    <div className="font-sans max-w-[760px] mx-auto px-6 py-12">
      <Link to="/dashboard" className="text-[#2C5F8A] text-sm no-underline">
        ← Retour à l'historique
      </Link>

      {loading && (
        <div className="flex items-center gap-3 mt-8 text-gray-500">
          <Spinner size={20} />
          <span>Chargement de la réunion...</span>
        </div>
      )}

      {error && (
        <p className="text-[#B91C1C] mt-8 text-sm">{error}</p>
      )}

      {!loading && !error && meeting && (
        <>
          <h1 className="text-3xl mt-6 mb-2">{meeting.title}</h1>
          <div className="flex gap-4 flex-wrap text-gray-500 text-sm mb-10">
            <span>{formatDate(meeting.created_at)}</span>
            <span>{formatDuration(meeting.duration_sec)}</span>
            <span>{meeting.mode === "video" ? "Réunion en ligne" : "Dictaphone"}</span>
          </div>

          {/* Compte rendu */}
          <h2 className="text-base text-[#2C5F8A] mt-10 mb-4">Compte rendu</h2>

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
              <p className="text-gray-500 text-sm mb-3">
                Aucun compte rendu n'a encore été généré pour cette réunion.
              </p>
              {meeting.transcription?.raw_text && (
                <Button
                  onClick={handleGenerateSummary}
                  disabled={isSummarizing}
                  loading={isSummarizing}
                >
                  {isSummarizing ? "Génération en cours..." : "Générer le compte-rendu"}
                </Button>
              )}
              {isSummarizing && (
                <div className="mt-4 w-full max-w-[480px]">
                  <ProgressBar label="Génération du compte-rendu en cours..." />
                </div>
              )}
              {summaryError && (
                <p className="text-[#B91C1C] text-sm mt-2">{summaryError}</p>
              )}
            </div>
          )}

          {/* Diarisation */}
          {meeting.transcription?.diarization && meeting.transcription.diarization.length > 0 && (
            <>
              <h2 className="text-base text-[#2C5F8A] mt-10 mb-4">Prise de parole</h2>
              <DiarizationDisplay segments={meeting.transcription.diarization} />
            </>
          )}

          {/* Transcription */}
          <h2 className="text-base text-[#2C5F8A] mt-10 mb-4">Transcription</h2>
          {meeting.transcription?.raw_text ? (
            <Card padding="lg">
              <p className="text-[#1C1C1C] text-sm leading-relaxed whitespace-pre-wrap m-0">
                {meeting.transcription.raw_text}
              </p>
            </Card>
          ) : (
            <p className="text-gray-500 text-sm">
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