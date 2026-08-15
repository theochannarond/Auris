import { useNetworkStatus } from "../../hooks/useNetworkStatus";

export default function OfflineBanner() {
  const { isOnline, wasOffline } = useNetworkStatus();

  if (isOnline && !wasOffline) return null;

  if (!isOnline) {
    return (
      <div className="fixed top-0 left-0 right-0 z-50 px-4 py-3 bg-[#7A4A00] text-white text-sm text-center font-medium">
        ⚠ Connexion perdue — l'enregistrement continue localement et sera envoyé automatiquement dès la reconnexion.
      </div>
    );
  }

  if (wasOffline) {
    return (
      <div className="fixed top-0 left-0 right-0 z-50 px-4 py-3 bg-[#0A4A25] text-white text-sm text-center font-medium">
        ✓ Connexion rétablie — synchronisation de l'enregistrement en cours...
      </div>
    );
  }

  return null;
}