import { useMeetings } from "../hooks/useMeetings";
import MeetingCard from "../components/ui/MeetingCard";

export default function DashboardPage() {
  const { meetings, loading, error } = useMeetings();

  return (
    <div style={{
      fontFamily: "Arial, sans-serif",
      maxWidth: "760px",
      margin: "0 auto",
      padding: "48px 24px"
    }}>
      <h1 style={{ fontSize: "2rem", marginBottom: "8px" }}>Auris</h1>
      <h2 style={{ fontSize: "1.1rem", color: "#6B7280", marginBottom: "40px", fontWeight: "normal" }}>
        Historique de vos réunions
      </h2>

      {loading && (
        <p style={{ color: "#6B7280" }}>Chargement de vos réunions...</p>
      )}

      {error && (
        <p style={{ color: "#B91C1C", fontSize: "0.9rem" }}>{error}</p>
      )}

      {!loading && !error && meetings.length === 0 && (
        <div style={{
          background: "#F4F6FB",
          borderRadius: "12px",
          padding: "32px",
          textAlign: "center",
          color: "#6B7280"
        }}>
          <p style={{ marginBottom: "8px", color: "#374151", fontWeight: "500" }}>
            Aucune réunion pour le moment
          </p>
          <p style={{ fontSize: "0.9rem" }}>
            Vos réunions apparaîtront ici une fois enregistrées.
          </p>
        </div>
      )}

      {!loading && !error && meetings.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {meetings.map((meeting) => (
            <MeetingCard key={meeting.id} meeting={meeting} />
          ))}
        </div>
      )}
    </div>
  );
}
