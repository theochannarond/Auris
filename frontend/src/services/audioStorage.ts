const DB_NAME    = "auris_offline";
const DB_VERSION = 1;
const STORE_NAME = "audio_chunks";

export interface AudioChunk {
  id:          string;   // meetingId
  chunks:      Blob[];
  createdAt:   number;
  uploaded:    boolean;
}

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "id" });
      }
    };

    request.onsuccess  = () => resolve(request.result);
    request.onerror    = () => reject(request.error);
  });
}

export async function saveChunkToIndexedDB(
  meetingId: string,
  chunk:      Blob
): Promise<void> {
  const db      = await openDB();
  const tx      = db.transaction(STORE_NAME, "readwrite");
  const store   = tx.objectStore(STORE_NAME);
  const request = store.get(meetingId);

  return new Promise((resolve, reject) => {
    request.onsuccess = () => {
      const existing: AudioChunk = request.result || {
        id:        meetingId,
        chunks:    [],
        createdAt: Date.now(),
        uploaded:  false,
      };
      existing.chunks.push(chunk);
      store.put(existing);
      tx.oncomplete = () => resolve();
      tx.onerror    = () => reject(tx.error);
    };
    request.onerror = () => reject(request.error);
  });
}

export async function getChunksFromIndexedDB(
  meetingId: string
): Promise<Blob[]> {
  const db      = await openDB();
  const tx      = db.transaction(STORE_NAME, "readonly");
  const store   = tx.objectStore(STORE_NAME);
  const request = store.get(meetingId);

  return new Promise((resolve, reject) => {
    request.onsuccess = () => {
      const record: AudioChunk | undefined = request.result;
      resolve(record ? record.chunks : []);
    };
    request.onerror = () => reject(request.error);
  });
}

export async function markAsUploaded(meetingId: string): Promise<void> {
  const db      = await openDB();
  const tx      = db.transaction(STORE_NAME, "readwrite");
  const store   = tx.objectStore(STORE_NAME);
  const request = store.get(meetingId);

  return new Promise((resolve, reject) => {
    request.onsuccess = () => {
      const record: AudioChunk = request.result;
      if (record) {
        record.uploaded = true;
        store.put(record);
      }
      tx.oncomplete = () => resolve();
      tx.onerror    = () => reject(tx.error);
    };
    request.onerror = () => reject(request.error);
  });
}

export async function clearChunksFromIndexedDB(meetingId: string): Promise<void> {
  const db    = await openDB();
  const tx    = db.transaction(STORE_NAME, "readwrite");
  const store = tx.objectStore(STORE_NAME);
  store.delete(meetingId);

  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror    = () => reject(tx.error);
  });
}

export async function getPendingUploads(): Promise<AudioChunk[]> {
  const db      = await openDB();
  const tx      = db.transaction(STORE_NAME, "readonly");
  const store   = tx.objectStore(STORE_NAME);
  const request = store.getAll();

  return new Promise((resolve, reject) => {
    request.onsuccess = () => {
      const all: AudioChunk[] = request.result || [];
      resolve(all.filter(r => !r.uploaded));
    };
    request.onerror = () => reject(request.error);
  });
}