import ClassificationBadges from "./ClassificationBadges";
import type { MeetingListItem } from "../../hooks/useMeetings";

interface MeetingCardProps {
  meeting:  MeetingListItem;
  onDelete?: (meetingId: string) => Promise<void>;
}

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

export default function MeetingCard({ meeting, onDelete }: MeetingCardProps) {
  return (
    <div className="flex flex-col gap-3 p-5 border border-[#E5E7EB] rounded-xl bg-white hover:shadow-md transition-shadow duration-200">
      <div className="flex justify-between items-start gap-4">
        <span className="text-base font-semibold text-gray-900">
          {meeting.title}
        </span>
        {onDelete && (
          <button
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onDelete(meeting.id);
            }}
            className="text-xs text-gray-400 hover:text-[#B91C1C] transition-colors cursor-pointer border-none bg-transparent"
          >
            Supprimer
          </button>
        )}
      </div>

      <div className="flex gap-4 flex-wrap text-gray-500 text-sm">
        <span>{formatDate(meeting.created_at)}</span>
        <span>{formatDuration(meeting.duration_sec)}</span>
      </div>

      <ClassificationBadges theme={meeting.theme} tone={meeting.tone} />
    </div>
  );
}