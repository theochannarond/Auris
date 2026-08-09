interface BotStatusNotificationProps {
  status: string | null;
}

export default function BotStatusNotification({ status }: BotStatusNotificationProps) {
  if (!status || status === "pending") {
    return (
      <div className="px-5 py-3 rounded-lg bg-[#FFF3CD] text-[#7A4A00] text-sm mt-4">
        ⏳ En attente que le bot rejoigne la réunion...
      </div>
    );
  }

  if (status === "recording") {
    return (
      <div className="px-5 py-3 rounded-lg bg-[#D6F5E3] text-[#0A4A25] text-sm mt-4 font-medium">
        ✓ Le bot Auris a rejoint la réunion — enregistrement en cours
      </div>
    );
  }

  if (status === "failed") {
    return (
      <div className="px-5 py-3 rounded-lg bg-[#FAD7D7] text-[#7A0A0A] text-sm mt-4">
        ✗ Le bot n'a pas pu rejoindre la réunion. Vérifiez le lien et réessayez.
      </div>
    );
  }

  return null;
}