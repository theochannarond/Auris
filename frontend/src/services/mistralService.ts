export async function triggerSummary(meetingId: string): Promise<{ id: string }> {
  try {
    const response = await fetch("/api/v1/summaries", {
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
      "Impossible de générer le compte-rendu pour le moment. Réessayez dans quelques instants."
    );
  }
}