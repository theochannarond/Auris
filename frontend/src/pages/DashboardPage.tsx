import { useState } from "react";
import { Link } from "react-router-dom";
import { useMeetings } from "../hooks/useMeetings";
import MeetingCard from "../components/ui/MeetingCard";

export default function DashboardPage() {
  const { meetings, loading, error, deleteMeeting } = useMeetings();
  const [notice, setNotice]           = useState("");
  const [deleteError, setDeleteError] = useState("");

  const handleDelete = async (meetingId: string) => {
    setNotice("");
    setDeleteError("");
    try {
      // Le texte de confirmation vient du backend : une seule formulation RGPD
      setNotice(await deleteMeeting(meetingId));
    } catch {
      setDeleteError("La suppression a échoué. La réunion est toujours présente.");
      throw new Error("suppression échouée");  // rend la main à la carte
    }
  };

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

      {/* Confirmation de suppression — RGPD Art.17 */}
      {notice && (
        <div style={{
          padding:      "14px 16px",
          marginBottom: "20px",
          borderRadius: "10px",
          background:   "#ECFDF5",
          border:       "1px solid #A7F3D0",
          color:        "#065F46",
          fontSize:     "0.9rem"
        }}>
          {notice}
        </div>
      )}

      {deleteError && (
        <div style={{
          padding:      "14px 16px",
          marginBottom: "20px",
          borderRadius: "10px",
          background:   "#FEF2F2",
          border:       "1px solid #FECACA",
          color:        "#7F1D1D",
          fontSize:     "0.9rem"
        }}>
          {deleteError}
        </div>
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
            <Link
              key={meeting.id}
              to={`/meetings/${meeting.id}`}
              style={{ textDecoration: "none", color: "inherit" }}
            >
              <MeetingCard meeting={meeting} onDelete={handleDelete} />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
