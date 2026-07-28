import { useState } from "react";

export default function VideoModePage() {
  const [meetingLink, setMeetingLink] = useState("");
  const [title, setTitle] = useState("");
  const [meeting, setMeeting] = useState<{id: string; status: string} | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleCreateMeeting = async () => {
    if (!title || !meetingLink) {
      setError("Le titre et le lien de la réunion sont obligatoires.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/v1/meetings/video", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, meeting_link: meetingLink })
      });
      if (!response.ok) throw new Error("Erreur lors de la création de la réunion.");
      const data = await response.json();
      setMeeting(data);
    } catch (err) {
      setError("Une erreur est survenue. Veuillez réessayer.");
    } finally {
      setLoa      setLoa      setLoa
  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      height: "100vh",
      fontFamily: "Arial, sans-serif",
      padding: "0 24px",
      maxWidth: "600px",
      margin: "0 auto"
    }}>
      <h1 style={{ fontSize: "2rem", marginBottom: "8px" }}>Auris</h1>
      <h2 style={{ fontSize: "1.1rem", color: "#6B7280", marginBottom: "32px" }}>
         ode réunion              </h2>

      {!meeting ? (
        <>
          <input
            type="text"
            placeholder="Titre de la réunion            placeholder="Titre de la réunion        > setTitle(e.target.value)}
            style={{
              width: "100%", padding: "12px", borderRadius: "8px",
              border: "1px solid #D1D5DB", marginBottom: "12px",
              fontSize: "1rem"              fontSiz                  <input
            type="text"
            placeholder="Lien Google Me             Zoom"
            value={meetingLink}
            onChange={e => setMeetingLink(e.target.value)}
            style={{
                   : "100%", padd                 erRadius: "8px",
              border: "1px solid #D1D5DB", marginBottom: "24px",
              fontSize: "1rem"
            }}
          />
          {error && (
            <p style={{ color: "#B91C1C", marginBottom: "16px", fo            <p style={{ color: "#B91C1C", marginBottom: "16px", fo            <    <button
            onClick={handleCreate            on        isabled={loading}
                                   backgroundColor: loading ? "#9CA3AF" : "#2C5F8A",
              color: "white", border: "none",
              padding: "12p              pRadius: "8px",
              fontSize: "1rem", cursor: loading ? "not-allowed" : "pointer"
            }}
          >
            {loading ? "Démarrage..." : "Lancer la réunion"}
          </button>
        </>
                     div style={{ textAlign: "center" }}>
          <p style={{ fontSize: "1.1rem", color: "#059669", marginBottom: "8px" }}>
            ✓ Le bot Auris a rejoint votre réunion
          </p>
          <p style={{ color: "#6B7280", fontSize: "          <p style={{ color: "#6B7280", fontSize: "         </p>
          <p style={{ color: "#       , fontSize: "0.85rem", marginTop: "8px" }}>
            ID réunion : {meeting.id}
          </p>
        </div>
      )}
    </div>
  );
}
