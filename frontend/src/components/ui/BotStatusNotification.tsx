interface BotStatusNotificationProps {
  status: string | null;
  /**
   * Date d'entrée du bot dans la réunion, ou null s'il n'y est jamais entré.
   * Indispensable pour expliquer un échec : sans elle, une réunion enregistrée
   * mais silencieuse était annoncée comme un bot incapable de se connecter.
   */
  startedAt?: string | null;
}

export default function BotStatusNotification({ status, startedAt }: BotStatusNotificationProps) {
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
    // Le bot était bien entré : l'échec vient d'après, et le seul cas observé
    // est une réunion sans une parole — Voxtral rend alors un texte vide et
    // aucun compte rendu n'est produit. Renvoyer l'utilisateur vers son lien
    // serait l'envoyer chercher un problème qui n'existe pas.
    if (startedAt) {
      return (
        <div className="px-5 py-3 rounded-lg bg-[#FAD7D7] text-[#7A0A0A] text-sm mt-4">
          ✗ Le bot a bien rejoint la réunion, mais aucune parole n'a été détectée :
          aucun compte rendu n'a pu être produit.
        </div>
      );
    }

    return (
      <div className="px-5 py-3 rounded-lg bg-[#FAD7D7] text-[#7A0A0A] text-sm mt-4">
        ✗ Le bot n'a pas pu rejoindre la réunion. Vérifiez le lien et réessayez.
      </div>
    );
  }

  return null;
}