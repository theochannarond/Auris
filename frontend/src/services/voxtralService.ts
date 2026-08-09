export async function triggerTranscription(meetingId: string): Promise<{ id: string }> {
  try {
    const response = await fetch("/api/v1/transcriptions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ meeting_id: meetingId })
    });
    if (!response.ok) {
      throw new Error();
    }
    return await response.json();
  } catch {
    throw new Error(
      "La transcription a échoué. Vérifiez votre connexion et réessayez."
    );
  }
}