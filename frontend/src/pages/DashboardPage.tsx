import { useState } from "react";
import { Link } from "react-router-dom";
import { useMeetings } from "../hooks/useMeetings";
import MeetingCard from "../components/ui/MeetingCard";

export default function DashboardPage() {
  const { meetings, loading, error, deleteMeeting } = useMeetings();
  const [notice, setNotice]           = useState("");
  const [deleteError, setDeleteError] = useState("");

  const handleDelete = async (meetingId: string) => {
    setNotice("");
    setDeleteError("");
    try {
      setNotice(await deleteMeeting(meetingId));
    } catch {
      setDeleteError("La suppression a échoué. La réunion est toujours présente.");
      throw new Error("suppression échouée");
    }
  };

  return (
    <div className="font-sans max-w-[760px] mx-auto px-6 py-12">
      <h1 className="text-3xl mb-2">Auris</h1>
      <h2 className="text-lg text-gray-500 mb-10 font-normal">
        Historique de vos réunions
      </h2>

      {loading && (
        <p className="text-gray-500">Chargement de vos réunions...</p>
      )}

      {error && (
        <p className="text-[#B91C1C] text-sm">{error}</p>
      )}

      {/* Confirmation suppression — RGPD Art.17 */}
      {notice && (
        <div className="px-4 py-3 mb-5 rounded-xl bg-[#ECFDF5] border border-[#A7F3D0] text-[#065F46] text-sm">
          {notice}
        </div>
      )}

      {deleteError && (
        <div className="px-4 py-3 mb-5 rounded-xl bg-[#FEF2F2] border border-[#FECACA] text-[#7F1D1D] text-sm">
          {deleteError}
        </div>
      )}

      {!loading && !error && meetings.length === 0 && (
        <div className="bg-[#F4F6FB] rounded-xl p-8 text-center text-gray-500">
          <p className="mb-2 text-gray-700 font-medium">
            Aucune réunion pour le moment
          </p>
          <p className="text-sm">
            Vos réunions apparaîtront ici une fois enregistrées.
          </p>
        </div>
      )}

      {!loading && !error && meetings.length > 0 && (
        <div className="flex flex-col gap-3">
          {meetings.map((meeting) => (
            <Link
              key={meeting.id}
              to={`/meetings/${meeting.id}`}
              className="no-underline text-inherit"
            >
              <MeetingCard meeting={meeting} onDelete={handleDelete} />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}