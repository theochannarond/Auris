import { useState } from "react";
import { Link } from "react-router-dom";
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
  const [stopping, setStopping]       = useState(false);
  const [error, setError]             = useState("");
  const { status, startedAt }         = useMeetingStatus(meeting?.id ?? null);

  // Le bot ne quitte pas la réunion quand l'utilisateur la quitte : il reste
  // seul dans la salle. Sans ce bouton, le seul moyen de l'arrêter était de le
  // retirer à la main dans Google Meet — et c'est son départ qui déclenche la
  // récupération de l'audio, donc la transcription.
  const handleStop = async () => {
    if (!meeting) return;
    setStopping(true);
    setError("");
    try {
      const response = await apiFetch(`/api/v1/meetings/${meeting.id}/stop`, {
        method: "POST",
      });
      if (!response.ok) throw new Error();
    } catch {
      setError("Impossible d'arrêter le bot. Réessayez.");
    } finally {
      setStopping(false);
    }
  };

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
      {/* Même repère que les pages dictaphone et détail de réunion : sans lui,
          le mode vidéo était un cul-de-sac, on ne pouvait en sortir qu'en
          modifiant l'URL à la main. */}
      <Link
        to="/dashboard"
        className="text-[#2C5F8A] text-sm no-underline self-start mb-8"
      >
        ← Retour au dashboard
      </Link>

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
        <div className="text-center w-full flex flex-col items-center">
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
          {status === "processing" && (
            <div className="flex items-center gap-3 justify-center text-gray-500 mb-4">
              <Spinner size={18} />
              <span>Réunion terminée — transcription en cours...</span>
            </div>
          )}
          {status === "completed" && (
            <p className="text-lg text-[#059669] mb-2 font-medium">
              ✓ Compte rendu disponible dans vos réunions
            </p>
          )}
          {status === "failed" && (
            <p className="text-lg text-[#B91C1C] mb-2 font-medium">
              {startedAt
                ? "✗ Aucun compte rendu n'a pu être produit"
                : "✗ La réunion n'a pas pu être traitée"}
            </p>
          )}

          {/* Affiche le statut vivant, et non celui figé à la création */}
          <p className="text-gray-500 text-sm">
            Statut : {status ?? meeting.status}
          </p>

          {(status === "pending" || status === "recording") && (
            <div className="mt-6 w-full max-w-[320px]">
              <Button
                onClick={handleStop}
                disabled={stopping}
                loading={stopping}
                fullWidth
              >
                {stopping ? "Arrêt en cours..." : "Quitter la réunion"}
              </Button>
              <p className="text-gray-500 text-xs mt-2">
                Le bot quitte la visioconférence et le compte rendu est lancé.
              </p>
            </div>
          )}

          {error && (
            <p className="text-[#B91C1C] text-sm mt-4">{error}</p>
          )}
        </div>
      )}

      {meeting && <BotStatusNotification status={status} startedAt={startedAt} />}
    </div>
  );
}