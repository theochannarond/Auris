import { useEffect, useRef } from "react";
import { useNetworkStatus } from "./useNetworkStatus";
import {
  getPendingUploads,
  clearChunksFromIndexedDB,
} from "../services/audioStorage";

interface UseOfflineSyncProps {
  meetingId:  string | null;
  onSynced:   (blob: Blob) => void;
  onSyncFail: (error: string) => void;
}

export function useOfflineSync({
  meetingId,
  onSynced,
  onSyncFail,
}: UseOfflineSyncProps) {
  const { isOnline, wasOffline } = useNetworkStatus();
  const isSyncing = useRef(false);

  useEffect(() => {
    if (!isOnline || !wasOffline || !meetingId || isSyncing.current) return;

    const sync = async () => {
      isSyncing.current = true;
      try {
        const pending = await getPendingUploads();
        const record  = pending.find(r => r.id === meetingId);

        if (!record || record.chunks.length === 0) {
          isSyncing.current = false;
          return;
        }

        // Reconstitue le Blob complet depuis les chunks sauvegardés
        const blob = new Blob(record.chunks, { type: "audio/wav" });
        onSynced(blob);

        await clearChunksFromIndexedDB(meetingId);
      } catch (err) {
        onSyncFail("Impossible de synchroniser l'enregistrement local.");
      } finally {
        isSyncing.current = false;
      }
    };

    sync();
  }, [isOnline, wasOffline, meetingId]);
}