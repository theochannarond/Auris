import { useState, useEffect } from "react";

export interface NetworkStatus {
  isOnline:       boolean;
  wasOffline:     boolean;  // true si on vient de se reconnecter
  offlineSince:   number | null;  // timestamp de la déconnexion
}

export function useNetworkStatus(): NetworkStatus {
  const [isOnline, setIsOnline]         = useState(navigator.onLine);
  const [wasOffline, setWasOffline]     = useState(false);
  const [offlineSince, setOfflineSince] = useState<number | null>(null);

  useEffect(() => {
    const handleOffline = () => {
      setIsOnline(false);
      setWasOffline(false);
      setOfflineSince(Date.now());
    };

    const handleOnline = () => {
      setIsOnline(true);
      setWasOffline(true);
      // On reset wasOffline après 5s pour ne notifier qu'une fois
      setTimeout(() => setWasOffline(false), 5000);
    };

    window.addEventListener("offline", handleOffline);
    window.addEventListener("online",  handleOnline);

    return () => {
      window.removeEventListener("offline", handleOffline);
      window.removeEventListener("online",  handleOnline);
    };
  }, []);

  return { isOnline, wasOffline, offlineSince };
}