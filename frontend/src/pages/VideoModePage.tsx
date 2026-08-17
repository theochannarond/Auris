import { useState } from "react";
import { useMeetingStatus } from "../hooks/useMeetingStatus";
import BotStatusNotification from "../components/ui/BotStatusNotification";
import Button from "../components/ui/Button";
import Input from "../components/ui/Input";
import Spinner from "../components/Spinner";
import { apiFetch } from "../services/api";


export default function VideoModePage() {
  const [meetingLink, setMeetingLink] = useState("");
  const [title, setTitle]             = useState("");
  const [meeting, setMeeting]         = useState<{id: string; status: string} | null>(null);
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState("");
  const { status }                    = useMeetingStatus(meeting?.id ?? null);

  const handleCreateMeeting = async () => {
    if (!title || !meetingLink) {
      setError("Le titre et le lien de la réunion sont obligatoires.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const response = await apiFetch("/api/v1/meetings/video", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, meeting_link: meetingLink })
      });
      if (!response.ok) throw new Error();
      const data = await response.json();
      setMeeting(data);
    } catch {
      setError("Une erreur est survenue. Veuillez réessayer.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen font-sans px-6 max-w-[600px] mx-auto">
      <h1 className="text-3xl mb-2">Auris</h1>
      <h2 className="text-lg text-gray-500 mb-8 text-center">
        Mode réunion vidéo
      </h2>

      {!meeting ? (
        <div className="w-full flex flex-col gap-3">
          <Input
            placeholder="Titre de la réunion"
            value={title}
            onChange={e => setTitle(e.target.value)}
          />
          <Input
            placeholder="Lien Google Meet / Teams / Zoom"
            value={meetingLink}
            onChange={e => setMeetingLink(e.target.value)}
          />
          {error && (
            <p className="text-[#B91C1C] text-sm">{error}</p>
          )}
          <Button
            onClick={handleCreateMeeting}
            disabled={loading}
            loading={loading}
            fullWidth
          >
            {loading ? "Démarrage..." : "Lancer la réunion"}
          </Button>
        </div>
      ) : (
        <div className="text-center">
          {status === "pending" && (
            <div className="flex items-center gap-3 justify-center text-gray-500 mb-4">
              <Spinner size={18} />
              <span>En attente que le bot rejoigne...</span>
            </div>
          )}
          {status === "recording" && (
            <p className="text-lg text-[#059669] mb-2 font-medium">
              ✓ Le bot Auris a rejoint votre réunion
            </p>
          )}
          <p className="text-gray-500 text-sm">
            Statut : {meeting.status}
          </p>
          <p className="text-gray-500 text-xs mt-2">
            ID réunion : {meeting.id}
          </p>
        </div>
      )}

      {meeting && <BotStatusNotification status={status} />}
    </div>
  );
}