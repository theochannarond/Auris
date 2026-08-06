interface BotStatusNotificationProps {
  status: string | null;
}

export default function BotStatusNotification({ status }: BotStatusNotificationProps) {
  if (!status || status === "pending") {
    return (
      <div style={{
        padding: "12px 20px",
        borderRadius: "8px",
        background: "#FFF3CD",
        color: "#7A4A00",
        fontSize: "0.9rem",
        marginTop: "16px"
      }}>
        ⏳ En attente que le bot rejoigne la réunion...
      </div>
    );
  }

  if (status === "recording") {
    return (
      <div style={{
        padding: "12px 20px",
        borderRadius: "8px",
        background: "#D6F5E3",
        color: "#0A4A25",
        fontSize: "0.9rem",
        marginTop: "16px",
        fontWeight: "500"
      }}>
        ✓ Le bot Auris a rejoint la réunion — enregistrement en cours
      </div>
    );
  }

  if (status === "failed") {
    return (
      <div style={{
        padding: "12px 20px",
        borderRadius: "8px",
        background: "#FAD7D7",
        color: "#7A0A0A",
        fontSize: "0.9rem",
        marginTop: "16px"
      }}>
        ✗ Le bot n'a pas pu rejoindre la réunion. Vérifiez le lien et réessayez.
      </div>
    );
  }

  return null;
}